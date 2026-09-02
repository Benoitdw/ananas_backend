"""Liaison Telegram par lien profond.

Le protocole existe pour une raison de securite: le token du bot est un secret
serveur partage par tous les comptes, il ne doit jamais etre communique a un
utilisateur. Ces tests verrouillent le comportement du cote qui remplace la
lecture manuelle de getUpdates par l'utilisateur.

Le piege principal est la concurrence: getUpdates est une ressource exclusive,
et chaque appel avec un offset **detruit** definitivement les mises a jour
precedentes cote Telegram. Si la requete de A consommait le message de B sans
le traiter, B attendrait indefiniment.
"""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from ananas.db import Base
from ananas.models import NotificationChannel, TelegramLinkCode, User
from ananas import telegram_link as tl


@pytest.fixture
def db():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


def make_user(db, email="a@example.com") -> User:
    user = User(email=email, password_hash="x")
    db.add(user)
    db.commit()
    return user


def update(update_id: int, text: str, chat_id: int) -> dict:
    return {"update_id": update_id, "message": {"text": text, "chat": {"id": chat_id}}}


@pytest.fixture
def telegram(monkeypatch):
    """Remplace l'API Telegram par une file de mises a jour controlee."""
    state = {"queue": [], "offsets": []}

    def fake_get_updates(offset=None, limit=100):
        state["offsets"].append(offset)
        # Telegram ne rejoue que ce qui n'a pas ete confirme
        pending = [u for u in state["queue"] if offset is None or u["update_id"] >= offset]
        return pending

    monkeypatch.setattr(tl, "get_updates", fake_get_updates)
    monkeypatch.setattr(tl, "bot_username", lambda: "ananas_bot")
    return state


# ------------------------------------------------------------- extraction


@pytest.mark.parametrize(
    "text, expected",
    [
        ("/start ABC23456", "ABC23456"),
        ("/start@ananas_bot ABC23456", "ABC23456"),
        ("  /START abc23456  ", "ABC23456"),
        ("ABC23456", "ABC23456"),  # code colle a la main
        ("abc23456", "ABC23456"),
        ("/start", None),
        ("salut", None),
        ("", None),
    ],
)
def test_extraction_du_code(text, expected):
    assert tl._extract_code(text) == expected


def test_alphabet_sans_caracteres_ambigus():
    """Le code peut etre recopie a la main depuis un autre appareil."""
    for ambigu in "O0I1L":
        assert ambigu not in tl.ALPHABET


# ---------------------------------------------------------------- liaison


def test_lien_profond(db, telegram):
    code = tl.new_code(db, make_user(db))
    assert tl.deep_link(code.code) == f"https://t.me/ananas_bot?start={code.code}"


def test_liaison_complete(db, telegram):
    user = make_user(db)
    code = tl.new_code(db, user)

    assert tl.resolve(db, user) is None  # rien recu encore

    telegram["queue"].append(update(1, f"/start {code.code}", 42))
    channel = tl.resolve(db, user)

    assert channel is not None
    assert channel.target == "42"
    assert channel.type == "telegram"


def test_code_consomme_apres_liaison(db, telegram):
    """Un code rejouable permettrait de detourner la conversation d'un tiers."""
    user = make_user(db)
    code = tl.new_code(db, user)
    telegram["queue"].append(update(1, f"/start {code.code}", 42))
    tl.resolve(db, user)

    assert db.scalars(select(TelegramLinkCode)).all() == []


def test_un_seul_code_vivant_par_compte(db, telegram):
    """Un code oublie dans un onglet ne doit pas pouvoir lier plus tard."""
    user = make_user(db)
    first = tl.new_code(db, user)
    second = tl.new_code(db, user)

    codes = db.scalars(select(TelegramLinkCode)).all()
    assert [c.code for c in codes] == [second.code]
    assert first.code != second.code


def test_code_expire_ignore(db, telegram):
    user = make_user(db)
    code = tl.new_code(db, user)
    code.expires_at = datetime.now(UTC) - timedelta(minutes=1)
    db.commit()

    telegram["queue"].append(update(1, f"/start {code.code}", 42))
    tl.drain_updates(db)

    db.refresh(code)
    assert code.chat_id is None


def test_relier_met_a_jour_le_canal_existant(db, telegram):
    """Changer de telephone ne doit pas creer un second canal Telegram."""
    user = make_user(db)
    db.add(NotificationChannel(user_id=user.id, type="telegram", target="11", enabled=False))
    db.commit()

    code = tl.new_code(db, user)
    telegram["queue"].append(update(1, f"/start {code.code}", 99))
    channel = tl.resolve(db, user)

    assert channel.target == "99"
    assert channel.enabled is True
    assert len(db.scalars(select(NotificationChannel)).all()) == 1


# ------------------------------------------------------------ concurrence


def test_une_vidange_resout_tous_les_codes_en_attente(db, telegram):
    """Le coeur du probleme: getUpdates est exclusif et destructif.

    Si la requete d'Alice consommait le message de Bob sans le traiter, Bob
    attendrait indefiniment — Telegram ne rejoue pas une mise a jour confirmee.
    """
    alice, bob = make_user(db, "alice@x.be"), make_user(db, "bob@x.be")
    code_a, code_b = tl.new_code(db, alice), tl.new_code(db, bob)

    telegram["queue"] += [
        update(1, f"/start {code_a.code}", 111),
        update(2, f"/start {code_b.code}", 222),
    ]

    # Alice interroge la premiere: sa requete voit et traite les deux messages
    channel_a = tl.resolve(db, alice)
    assert channel_a.target == "111"

    # Bob n'a plus rien a lire cote Telegram, mais son code est deja resolu
    telegram["queue"].clear()
    channel_b = tl.resolve(db, bob)
    assert channel_b is not None and channel_b.target == "222"


def test_offset_avance_et_persiste(db, telegram):
    """Sans offset persiste, on retraite ou on perd des messages au redemarrage."""
    user = make_user(db)
    code = tl.new_code(db, user)
    telegram["queue"].append(update(4242, f"/start {code.code}", 42))

    tl.drain_updates(db)
    assert tl._get_offset(db) == 4243

    # L'appel suivant confirme bien le lot precedent
    tl.drain_updates(db)
    assert telegram["offsets"][-1] == 4243


def test_message_sans_code_ne_bloque_pas(db, telegram):
    """Quelqu'un ecrit 'salut' au bot: la mise a jour doit etre consommee, pas
    rester en travers de la file."""
    telegram["queue"].append(update(7, "salut", 5))
    assert tl.drain_updates(db) == 0
    assert tl._get_offset(db) == 8


def test_echec_reseau_silencieux(db, monkeypatch):
    """Une panne Telegram doit laisser reessayer, pas casser la page."""
    from ananas.notifiers.telegram import TelegramApiError

    def boom(offset=None, limit=100):
        raise TelegramApiError("injoignable")

    monkeypatch.setattr(tl, "get_updates", boom)
    assert tl.drain_updates(db) == 0

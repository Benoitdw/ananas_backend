"""Perimetre de recherche applique a la notification quotidienne.

Un filtre d'envoi est plus dangereux qu'un filtre d'interface: ce qu'il ecarte
n'est pas simplement cache, il ne sera jamais montre. Trois garde-fous en
decoulent, et ce sont eux que ce fichier verifie:

  - il est eteint tant que l'utilisateur ne l'a pas allume;
  - une entreprise sans coordonnees passe quand meme (position inconnue n'est
    pas synonyme de trop loin);
  - ce qui a ete ecarte est compte, pour que la notification puisse le dire.
"""

from __future__ import annotations

from ananas.models import Company, Job, UserHome
from ananas.notifiers.base import Digest, JobLine
from ananas.notifiers.telegram import TelegramNotifier
from ananas.worker.notify import build_digest, within_radius

# Domicile: Bruxelles. Gand est a ~50 km, Liege a ~90 km.
BRUXELLES = (50.8503, 4.3517)
GAND = (51.0543, 3.7174)
LIEGE = (50.6326, 5.5797)


def home(radius_km: int = 60, *, active: bool = True, located: bool = True) -> UserHome:
    return UserHome(
        user_id=1,
        lat=BRUXELLES[0] if located else None,
        lon=BRUXELLES[1] if located else None,
        radius_km=radius_km,
        notify_within_radius=active,
    )


def row(name: str, point: tuple[float, float] | None):
    company = Company(
        slug=name.lower(),
        name=name,
        lat=point[0] if point else None,
        lon=point[1] if point else None,
    )
    return (Job(title=f"Offre {name}", url=f"https://{name.lower()}.example/1"), company, None)


def names(rows) -> list[str]:
    return [company.name for _job, company, _score in rows]


# --------------------------------------------------------------- within_radius


def test_reglage_eteint_ne_filtre_rien():
    rows = [row("Gand", GAND), row("Liege", LIEGE)]
    kept, beyond = within_radius(rows, home(active=False))
    assert names(kept) == ["Gand", "Liege"]
    assert beyond == 0


def test_sans_domicile_du_tout_ne_filtre_rien():
    rows = [row("Liege", LIEGE)]
    assert within_radius(rows, None) == (rows, 0)


def test_domicile_non_localise_ne_filtre_rien():
    """Filtrer sur un point inconnu reviendrait a tout supprimer."""
    rows = [row("Gand", GAND), row("Liege", LIEGE)]
    kept, beyond = within_radius(rows, home(located=False))
    assert names(kept) == ["Gand", "Liege"]
    assert beyond == 0


def test_au_dela_du_rayon_est_ecarte_et_compte():
    kept, beyond = within_radius([row("Gand", GAND), row("Liege", LIEGE)], home(60))
    assert names(kept) == ["Gand"]
    assert beyond == 1


def test_entreprise_sans_coordonnees_est_gardee():
    # Meme regle que l'offre non caracterisee face au seuil de pertinence:
    # on ne perd pas ce qu'on ne sait pas mesurer.
    kept, beyond = within_radius([row("Inconnue", None), row("Liege", LIEGE)], home(60))
    assert names(kept) == ["Inconnue"]
    assert beyond == 1


def test_rayon_large_garde_tout():
    kept, beyond = within_radius([row("Gand", GAND), row("Liege", LIEGE)], home(150))
    assert names(kept) == ["Gand", "Liege"]
    assert beyond == 0


# ----------------------------------------------------------------- build_digest


def test_build_digest_transporte_le_compte_ecarte():
    digest = build_digest([], beyond_radius=3, radius_km=40)
    assert digest.beyond_radius == 3
    assert digest.radius_km == 40


def test_build_digest_par_defaut_aucun_ecarte():
    assert build_digest([]).beyond_radius == 0


# ------------------------------------------------------------- rendu Telegram


def sample(beyond: int, radius: int | None) -> Digest:
    return Digest(
        companies={"Acme": [JobLine(title="Data Engineer", url="https://acme.example/1")]},
        beyond_radius=beyond,
        radius_km=radius,
    )


def test_rendu_annonce_les_offres_hors_perimetre():
    html = TelegramNotifier().render(sample(3, 40))
    assert "3 autres offres au-dela de 40 km" in html


def test_rendu_accorde_le_singulier():
    html = TelegramNotifier().render(sample(1, 40))
    assert "1 autre offre au-dela de 40 km" in html
    assert "offres au-dela" not in html


def test_rendu_silencieux_quand_rien_n_a_ete_ecarte():
    assert "au-dela de" not in TelegramNotifier().render(sample(0, 40))

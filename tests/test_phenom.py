"""Scrapers Phenom People (GSK).

Le piege de ces sites: la recherche par lieu est une recherche de *proximite*,
pas un filtre. Interroger "Rixensart" renvoie des postes a Londres et
Collegeville. Sans filtrage, l'entreprise "GSK Rixensart" se retrouverait avec
des offres qui n'ont rien a voir avec le site local — et les notifications
aussi.
"""

import json

import pytest

from ananas.scrapers.phenom import PhenomScraper, _places
from ananas.scrapers.registry import get_scraper, load_scrapers


class FakeGsk(PhenomScraper):
    key = "fake-gsk"
    base_url = "https://jobs.example.com"
    locale_path = "be/fr"
    town = "Rixensart"
    search_location = "Rixensart, Brabant wallon, Belgique"
    rate_limit = 0


def job(**over) -> dict:
    return {
        "jobId": "1",
        "jobSeqNo": "SEQ1",
        "title": "Ingenieur procedes",
        "city": "Rixensart",
        "multi_location": ["Rixensart, Brabant wallon, Belgique"],
        "category": "Engineering",
        "postedDate": "2026-07-10T00:00:00.000+0000",
        "descriptionTeaser": "Un poste interessant",
        **over,
    }


# --------------------------------------------------- recherche de proximite


def test_poste_local_retenu():
    assert FakeGsk()._is_local(job())


def test_poste_multi_site_incluant_la_ville_retenu():
    """Un poste ouvert a Londres ET a Rixensart concerne bien le site local:
    filtrer sur `city` seul le ferait manquer, car city vaut alors London."""
    multi = job(
        city="London",
        multi_location=[
            "London, Royaume-Uni",
            "Rixensart, Brabant wallon, Belgique",
            "Barnard Castle, Durham, Royaume-Uni",
        ],
    )
    assert FakeGsk()._is_local(multi)


def test_poste_lointain_ecarte():
    """C'est tout l'objet du filtre: sans lui, un poste a Collegeville
    apparaitrait chez GSK Rixensart."""
    lointain = job(city="Collegeville", multi_location=["Collegeville, Pennsylvanie, USA"])
    assert not FakeGsk()._is_local(lointain)


def test_filtrage_insensible_a_la_casse():
    assert FakeGsk()._is_local(job(multi_location=["RIXENSART, Brabant wallon, Belgique"]))


def test_poste_sans_lieu_ecarte():
    assert not FakeGsk()._is_local({"multi_location": [], "location": ""})


# ------------------------------------------------------------------ lieux


def test_lieux_reduits_aux_villes():
    """Cinq sites en forme complete depassent la colonne location (255) et
    sont illisibles: on ne garde que les villes."""
    lieux = _places(
        job(
            multi_location=[
                "Wavre, Brabant wallon, Belgique",
                "Siena, Sienne, Italie",
                "Ware, Hertfordshire, Royaume-Uni",
            ]
        )
    )
    assert lieux == "Wavre, Siena, Ware"


def test_lieux_dedoublonnes():
    doublons = job(multi_location=["Wavre, Belgique", "Wavre, Brabant wallon, Belgique"])
    assert _places(doublons) == "Wavre"


def test_lieux_bornes():
    long = job(multi_location=[f"Ville{i}, Region, Pays" for i in range(80)])
    assert len(_places(long)) <= 255


# ------------------------------------------------------------- conversion


def test_identifiant_stable():
    """jobId survit a un changement de titre ou de slug d'URL."""
    posting = FakeGsk()._to_posting(job(jobId="444378"))
    assert posting.external_id == "444378"
    renomme = FakeGsk()._to_posting(job(jobId="444378", title="Autre intitule"))
    assert posting.fingerprint == renomme.fingerprint


def test_url_construite_depuis_le_numero_de_sequence():
    posting = FakeGsk()._to_posting(job(jobSeqNo="GHV123", title="Ingenieur procedes"))
    assert posting.url.startswith("https://jobs.example.com/be/fr/job/GHV123/")


def test_date_de_publication_lue():
    assert FakeGsk()._to_posting(job()).posted_at.isoformat() == "2026-07-10"


def test_date_invalide_ignoree():
    assert FakeGsk()._to_posting(job(postedDate="pas une date")).posted_at is None


# ---------------------------------------------------------------- registre


@pytest.mark.parametrize("key", ["gsk-wavre", "gsk-rixensart"])
def test_scrapers_gsk_enregistres(key):
    load_scrapers()
    cls = get_scraper(key)
    assert cls is not None
    # La cle doit egaler le slug de l'entreprise pour l'auto-liage du seed
    assert cls.key == key
    assert cls.town and cls.search_location


def test_les_deux_sites_sont_distincts():
    """Wavre et Rixensart sont deux entreprises: leurs scrapers ne doivent pas
    viser le meme lieu."""
    load_scrapers()
    assert get_scraper("gsk-wavre").town != get_scraper("gsk-rixensart").town


# ------------------------------------------------------------- description


def test_repli_sur_extrait_si_fiche_illisible(monkeypatch):
    """Une fiche indisponible ne doit pas faire perdre l'offre."""
    scraper = FakeGsk()

    def boom(url):
        raise ValueError("503")

    monkeypatch.setattr(scraper, "_ddo", boom)
    texte = scraper._description(
        "https://x", job(ml_skills=["maintenance", "diagnostic"], timeType="Plein temps")
    )
    assert "Un poste interessant" in texte
    assert "maintenance" in texte


def test_pagination_s_arrete_sans_nouveaute(monkeypatch):
    """Si le site renvoie sans cesse la meme page, la boucle doit sortir
    plutot que de tourner jusqu'a max_pages."""
    scraper = FakeGsk()
    appels = []

    def toujours_pareil(url):
        appels.append(url)
        return {"eagerLoadRefineSearch": {"totalHits": 999, "data": {"jobs": [job()]}}}

    monkeypatch.setattr(scraper, "_ddo", toujours_pareil)
    assert len(scraper._search()) == 1
    assert len(appels) == 2  # une page utile, puis une sans nouveaute


def test_ddo_decode_meme_suivi_d_autre_code(monkeypatch):
    """Le JSON est suivi de code arbitraire: raw_decode doit s'arreter au bon
    endroit."""
    scraper = FakeGsk()
    payload = json.dumps({"eagerLoadRefineSearch": {"totalHits": 0, "data": {"jobs": []}}})

    class Reponse:
        text = f"var x=1; phApp.ddo = {payload}; phApp.autre = {{}}; </script>"
        def raise_for_status(self): ...

    monkeypatch.setattr(scraper.session, "get", lambda *a, **k: Reponse())
    assert scraper._ddo("https://x")["eagerLoadRefineSearch"]["totalHits"] == 0

"""Scrapers Radancy (Sanofi).

Contrairement a Phenom, ces sites rendent du HTML classique. Le point qui les
rend fiables est le bloc schema.org JobPosting publie sur chaque fiche: c'est
un standard, il survit aux refontes graphiques la ou un selecteur CSS casse.
"""

from datetime import date

import pytest

from ananas.scrapers.http import jsonld_job_posting
from ananas.scrapers.radancy import (
    RadancyScraper,
    _after_label,
    _as_date,
    _jsonld_country,
    _jsonld_places,
)
from ananas.scrapers.registry import get_scraper, load_scrapers


class FakeRadancy(RadancyScraper):
    key = "fake-radancy"
    base_url = "https://jobs.example.com"
    search_path = "/en/search-jobs/Belgium/"
    rate_limit = 0


def card(**over) -> dict:
    return {
        "job_id": "42384344512",
        "url": "https://jobs.example.com/en/job/geel/warehouse-operator/2649/42384344512",
        "title": "Warehouse Operator",
        "location": "Geel",
        "category": "Supply Chain",
        **over,
    }


# ----------------------------------------------------------------- JSON-LD


def test_jsonld_extrait():
    html = """
    <script type="application/ld+json">{"@type":"Organization","name":"X"}</script>
    <script type="application/ld+json">{"@type":"JobPosting","title":"Warehouse Operator"}</script>
    """
    assert jsonld_job_posting(html)["title"] == "Warehouse Operator"


def test_jsonld_dans_un_graphe():
    html = """<script type="application/ld+json">
      {"@graph":[{"@type":"WebPage"},{"@type":"JobPosting","title":"Technicien"}]}</script>"""
    assert jsonld_job_posting(html)["title"] == "Technicien"


def test_jsonld_absent():
    assert jsonld_job_posting("<html><body>rien</body></html>") is None


def test_jsonld_invalide_ignore():
    """Un bloc casse ne doit pas empecher de lire les suivants."""
    html = """
    <script type="application/ld+json">{ pas du json }</script>
    <script type="application/ld+json">{"@type":"JobPosting","title":"Ok"}</script>
    """
    assert jsonld_job_posting(html)["title"] == "Ok"


# ------------------------------------------------------------------- dates


@pytest.mark.parametrize(
    "brut, attendu",
    [
        ("2026-8-4", date(2026, 8, 4)),  # forme non ISO propre a Radancy
        ("2026-08-04", date(2026, 8, 4)),
        ("2026-08-04T10:00:00Z", date(2026, 8, 4)),
    ],
)
def test_dates_acceptees(brut, attendu):
    assert _as_date(brut) == attendu


@pytest.mark.parametrize("brut", ["", None, "hier", "2026-13-45"])
def test_dates_invalides(brut):
    assert _as_date(brut) is None


# ------------------------------------------------------------------ libelles


def test_etiquette_retiree():
    """Les cartes rendent 'Location: Geel'."""
    assert _after_label("Location: Geel") == "Geel"
    assert _after_label("Geel") == "Geel"


def test_lieux_jsonld():
    node = [
        {"address": {"addressLocality": "Geel"}},
        {"address": {"addressLocality": "Diegem"}},
        {"address": {"addressLocality": "Geel"}},
    ]
    assert _jsonld_places(node) == "Geel, Diegem"


def test_lieux_jsonld_vides():
    assert _jsonld_places(None) == ""
    assert _jsonld_places([{"address": {}}]) == ""


# -------------------------------------------------------------- conversion


def test_fiche_indisponible_conserve_l_offre(monkeypatch):
    """Perdre la fiche ne doit pas faire perdre l'offre: la liste porte deja
    l'essentiel."""
    scraper = FakeRadancy()
    monkeypatch.setattr(scraper, "_detail", lambda url: {})
    posting = scraper._to_posting(card())
    assert posting.title == "Warehouse Operator"
    assert posting.location == "Geel"
    assert posting.external_id == "42384344512"


def test_fiche_enrichit_l_offre(monkeypatch):
    scraper = FakeRadancy()
    monkeypatch.setattr(
        scraper,
        "_detail",
        lambda url: {
            "title": "Warehouse Operator",
            "description": "Un texte complet",
            "posted_at": date(2026, 8, 4),
            "location": "Geel",
        },
    )
    posting = scraper._to_posting(card())
    assert posting.description == "Un texte complet"
    assert posting.posted_at == date(2026, 8, 4)


def test_identifiant_stable_malgre_renommage(monkeypatch):
    scraper = FakeRadancy()
    monkeypatch.setattr(scraper, "_detail", lambda url: {})
    a = scraper._to_posting(card())
    b = scraper._to_posting(card(title="Magasinier"))
    assert a.fingerprint == b.fingerprint


# ------------------------------------------------------------- filtre pays


def test_pays_lu_depuis_jsonld():
    node = [{"address": {"addressCountry": "Belgium", "addressLocality": "Geel"}}]
    assert _jsonld_country(node) == "BELGIUM"


def test_pays_en_objet_imbrique():
    """schema.org autorise addressCountry sous forme d'objet Country."""
    node = [{"address": {"addressCountry": {"name": "Belgium"}}}]
    assert _jsonld_country(node) == "BELGIUM"


def test_pays_absent():
    assert _jsonld_country([{"address": {"addressLocality": "Geel"}}]) == ""
    assert _jsonld_country(None) == ""


def test_filtre_accepte_code_et_nom():
    """Les sites melangent code ISO et nom: n'accepter que "BE" rejetterait
    toutes les offres de Sanofi, qui ecrit "Belgium"."""
    load_scrapers()
    acceptes = get_scraper("sanofi-belgium").countries
    assert "BELGIUM" in acceptes and "BE" in acceptes


def test_offre_etrangere_ecartee(monkeypatch):
    """La recherche par chemin est un mot-cle: une annonce parisienne qui
    mentionne la Belgique remonterait sans ce filtre."""

    class Filtrant(FakeRadancy):
        countries = frozenset({"BELGIUM"})

    scraper = Filtrant()
    monkeypatch.setattr(scraper, "_collect", lambda: [card(job_id="1"), card(job_id="2")])
    pays = {"1": "BELGIUM", "2": "FRANCE"}
    monkeypatch.setattr(
        scraper,
        "_detail",
        lambda url: {"country": pays[url[-1]] if url[-1] in pays else "FRANCE"},
    )
    monkeypatch.setattr(scraper, "_to_posting", RadancyScraper._to_posting.__get__(scraper))

    cards = [card(job_id="1", url="u/1"), card(job_id="2", url="u/2")]
    monkeypatch.setattr(scraper, "_collect", lambda: cards)
    retenues = scraper.fetch()
    assert [p.external_id for p in retenues] == ["1"]


def test_pays_ne_change_pas_l_identite_de_l_offre(monkeypatch):
    """`raw` sert au filtrage, il ne doit pas entrer dans le fingerprint:
    sinon un changement de libelle de pays ferait renotifier l'offre."""
    scraper = FakeRadancy()
    monkeypatch.setattr(scraper, "_detail", lambda url: {"country": "BELGIUM"})
    a = scraper._to_posting(card())
    monkeypatch.setattr(scraper, "_detail", lambda url: {"country": "BE"})
    b = scraper._to_posting(card())
    assert a.fingerprint == b.fingerprint


# ---------------------------------------------------------------- registre


def test_sanofi_enregistre():
    load_scrapers()
    cls = get_scraper("sanofi-belgium")
    assert cls is not None and cls.search_path.endswith("/Belgium/")

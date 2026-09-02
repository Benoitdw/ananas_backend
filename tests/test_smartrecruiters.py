"""Parsing de l'API SmartRecruiters (Sobi…).

Aucune requete reseau : on verrouille les helpers de conversion. Le reseau est
couvert manuellement a l'ecriture du scraper (voir api/README.md). L'API
repond parfois 200 + ``content`` vide sous throttling — ``_list`` doit alors
lever plutot que rendre une liste vide (sinon ``run()`` fermerait toutes les
offres du jour) ; c'est le comportement teste ici via un faux ``_page``.
"""

import pytest

from ananas.scrapers.smartrecruiters import SmartRecruitersScraper, _as_date, _city


class _Fake(SmartRecruitersScraper):
    key = "fake"
    company = "Fake"
    country = "be"

    def __init__(self, pages):
        super().__init__()
        self._pages = list(pages)
        self.calls = 0

    def _page(self, url, params):  # noqa: ARG002
        page = self._pages[self.calls] if self.calls < len(self._pages) else {"totalFound": 0, "content": []}
        self.calls += 1
        return page


def test_city_prefere_full_location():
    assert _city({"location": {"city": "Zaventem", "fullLocation": "Zaventem, Belgium"}}) == "Zaventem, Belgium"
    assert _city({"location": {"city": "Gent"}}) == "Gent"
    assert _city({}) == ""


def test_date_iso_avec_zulu():
    assert _as_date("2026-09-01T13:47:30.824Z").isoformat() == "2026-09-01"
    assert _as_date(None) is None
    assert _as_date("bidon") is None


def test_liste_vide_reelle_est_toleree():
    assert _Fake([{"totalFound": 0, "content": []}])._list() == []


def test_content_vide_avec_total_positif_leve():
    # throttling silencieux : 3 offres annoncees, 0 renvoyee
    with pytest.raises(RuntimeError):
        _Fake([{"totalFound": 3, "content": []}])._list()


def test_pagination_concatene():
    pages = [
        {"totalFound": 3, "content": [{"id": "1"}, {"id": "2"}]},
        {"totalFound": 3, "content": [{"id": "3"}]},
    ]
    assert [s["id"] for s in _Fake(pages)._list()] == ["1", "2", "3"]

"""Parsing du JSON-LD schema.org expose par les sites Attrax (AbbVie...).

Aucune requete reseau: on verrouille uniquement l'extraction, sur un extrait
JSON-LD reel (voir AttraxScraper._job_from_detail). Le reseau lui-meme est
couvert manuellement lors de l'ecriture du scraper (voir api/README.md).
"""

from ananas.scrapers.attrax import _as_date, _locations

LD_JSON = {
    "@context": "http://schema.org",
    "@type": "JobPosting",
    "url": "https://careers.abbvie.com/en/job/msl-hematology-jid-32454",
    "title": "Medical Science Liaison (MSL) Hematology",
    "description": "<p>About <strong>AbbVie</strong></p>",
    "datePosted": "2026-09-01T15:50:09+00:00",
    "employmentType": ["Full-time"],
    "industry": ["Research & Development"],
    "identifier": {"@type": "PropertyValue", "name": "AbbVie", "value": "0fef3248-cc0a-4721"},
    "jobLocation": [{"@type": "Place", "address": {"addressLocality": "Wavre, Wallonia"}}],
}


def test_locations_reunit_les_lieux_dedoublonnes():
    data = {**LD_JSON, "jobLocation": LD_JSON["jobLocation"] * 2}
    assert _locations(data) == "Wavre, Wallonia"


def test_locations_absent_rend_none():
    assert _locations({}) is None


def test_date_iso_avec_fuseau():
    assert _as_date("2026-09-01T15:50:09+00:00").isoformat() == "2026-09-01"


def test_date_absente_ou_invalide():
    assert _as_date(None) is None
    assert _as_date("pas une date") is None

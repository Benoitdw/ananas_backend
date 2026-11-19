"""Parsing des scrapers ajoutes pour la Liste An, sans reseau.

On verrouille les decisions non evidentes: la veille d'etat vide, l'item
factice des flux jobs2web, le filtre de lieu JazzHR, le titre reconstruit des
PDF LIMS. Le reseau lui-meme a ete verifie a l'ecriture (voir LISTE_AN.md).
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from bs4 import BeautifulSoup

from ananas.scrapers.jazzhr import JazzHRScraper
from ananas.scrapers.jobs2web import Jobs2WebScraper
from ananas.scrapers.lims import _title_from_file
from ananas.scrapers.page_watch import PageWatchScraper
from ananas.scrapers.watched_pages import TwoBridgeScraper


def soup_of(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "html.parser")


class Watch(PageWatchScraper):
    key = "test-watch"
    label = "Acme"
    careers_url = "https://acme.test/careers"
    region = "main"
    empty_markers = ("There are currently no open vacancies",)


def watch(html: str) -> list:
    scraper = Watch()
    scraper.get_soup = lambda url: soup_of(html)
    return scraper.fetch()


def test_veille_rien_tant_que_l_etat_vide_est_affiche():
    # Casse et apostrophes typographiques ne comptent pas
    assert watch("<main><p>THERE ARE CURRENTLY  NO OPEN VACANCIES.</p></main>") == []


def test_veille_une_offre_stable_quand_l_etat_vide_disparait():
    html = "<main><h2>Open Vacancies</h2><a href='/x'>Senior Scientist</a></main>"
    first, second = watch(html), watch(html)
    assert len(first) == 1
    assert first[0].url == "https://acme.test/careers"
    assert "Senior Scientist" in first[0].description
    # Meme page -> meme offre, donc pas de nouvelle notification
    assert first[0].fingerprint == second[0].fingerprint
    # Page modifiee -> nouvelle offre
    assert watch(html.replace("Senior", "Junior"))[0].fingerprint != first[0].fingerprint


def test_veille_leve_si_la_zone_a_disparu():
    with pytest.raises(RuntimeError, match="introuvable"):
        watch("<body><p>refonte</p></body>")


def test_2bridge_onglet_avec_seulement_le_formulaire_est_vide():
    tab = soup_of(
        "<div id='tab-job-opportunity'><h3>Job opportunities</h3>"
        "<form>Your name* Your email*</form></div>"
    ).div
    assert TwoBridgeScraper().is_empty(tab)
    tab = soup_of(
        "<div id='tab-job-opportunity'><h3>Job opportunities</h3><p>QA Officer</p></div>"
    ).div
    assert not TwoBridgeScraper().is_empty(tab)


class UCL(Jobs2WebScraper):
    key = "test-j2w"
    base_url = "https://jobs.example.test"
    category_id = "1"


def test_jobs2web_ignore_l_item_aucune_offre(monkeypatch):
    rss = b"""<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel>
      <item><title>Aucune offre d'emploi actuellement disponible</title>
        <link>https://jobs.example.test</link></item>
      <item><title>PhD Position</title>
        <link>https://jobs.example.test/x/job/PhD-Position/1449333433/?utm_source=J2WRSS</link>
      </item></channel></rss>"""
    scraper = UCL()
    monkeypatch.setattr(
        scraper.session,
        "get",
        lambda *a, **k: SimpleNamespace(content=rss, raise_for_status=lambda: None),
    )
    monkeypatch.setattr(scraper, "sleep", lambda: None)
    postings = scraper.fetch()
    assert [p.title for p in postings] == ["PhD Position"]
    assert postings[0].external_id == "1449333433"


class Jazz(JazzHRScraper):
    key = "test-jazz"
    jazz_slug = "acme"
    location_tokens = frozenset({"belgium"})


def test_jazzhr_filtre_sur_le_lieu_de_la_ligne(monkeypatch):
    html = """<table>
      <tr><td><a href="/apply/jobs/details/AAA111?&">Lab Tech</a></td>
          <td>Wilrijk, Antwerp, Belgium</td></tr>
      <tr><td><a href="/apply/jobs/details/BBB222?&">Histotech</a></td>
          <td>Naperville, IL</td></tr>
    </table>"""
    scraper = Jazz()
    scraper.get_soup = lambda url: soup_of(html)
    monkeypatch.setattr(
        scraper, "_detail", lambda url, code, title, loc: SimpleNamespace(code=code, loc=loc)
    )
    found = scraper.fetch()
    assert [(p.code, p.loc) for p in found] == [("AAA111", "Wilrijk, Antwerp, Belgium")]


def test_lims_titre_depuis_le_nom_du_pdf():
    base = "https://lims-mbnext.eu/wp-content/uploads/2024/06/"
    assert _title_from_file(base + "Annonce-IT-application-Specialist-.pdf") == (
        "IT application Specialist"
    )
    assert _title_from_file(base + "Technologue-de-laboratoire.pdf") == "Technologue de laboratoire"

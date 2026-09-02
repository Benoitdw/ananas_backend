"""Parsing des pages SuccessFactors (Boehringer, Terumo).

Aucune requete reseau : on verrouille l'extraction sur des extraits de HTML
reels. Le reseau lui-meme est couvert manuellement a l'ecriture du scraper
(voir api/README.md).
"""

from bs4 import BeautifulSoup

from ananas.scrapers.successfactors import _as_date, _tiles, _total

TABLE_ROW = """
<table><tr class="data-row">
  <td class="colTitle"><span class="jobTitle">
    <a href="/job/Young-Graduate-Design-Engineering-Belg/1401333533/" class="jobTitle-link">Young Graduate Design Engineering</a>
  </span></td>
  <td class="colLocation"><span class="jobLocation">Belgium</span></td>
  <td class="colDate"><span class="jobDate">31 Aug 2026</span></td>
</tr></table>
"""

TILE = """
<ul id="job-tile-list"><li class="job-tile" data-url="/job/Brussels-Sales-Manager-Belg/1431507533/">
  <a class="jobTitle-link" href="/job/Brussels-Sales-Manager-Belg/1431507533/">Sales Manager</a>
  <div id="job-1431507533-desktop-section-location-value">Brussels-Capital Region, Belgium</div>
</li></ul>
"""


def test_tiles_reconnait_les_deux_themes():
    assert len(_tiles(BeautifulSoup(TABLE_ROW, "html.parser"))) == 1
    assert len(_tiles(BeautifulSoup(TILE, "html.parser"))) == 1


def test_total_lit_les_deux_libelles():
    a = '<span class="paginationLabel">Results 1 - 14 of 14</span>'
    b = '<span id="tile-search-results-label">Showing 1 to 2 of 2 Jobs</span>'
    assert _total(BeautifulSoup(a, "html.parser")) == 14
    assert _total(BeautifulSoup(b, "html.parser")) == 2
    assert _total(BeautifulSoup("<span>rien</span>", "html.parser")) == 0


def test_date_formats_rencontres():
    assert _as_date("31 Aug 2026").isoformat() == "2026-08-31"
    assert _as_date("2 Sept 2026").isoformat() == "2026-09-02"  # "Sept" non standard
    assert _as_date("Mon Aug 31 02:00:00 UTC 2026").isoformat() == "2026-08-31"
    assert _as_date(None) is None
    assert _as_date("pas une date") is None

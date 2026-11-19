"""ALK-Abello — Louvain-la-Neuve (allergologie). Teamtailor ``careers.alk.net``.

Le flux RSS Teamtailor couvre tout le groupe (Danemark, Etats-Unis...). On ne
garde que les offres dont un des lieux declares est en Belgique; le flux porte
le nom du site (``tt:location/tt:name``) et sa ville/pays.

Verifie le 2026-11-19: voir SCRAPERS.md.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET

from ananas.scrapers.base import JobPosting
from ananas.scrapers.qbd_group import TT_NS, TeamtailorScraper
from ananas.scrapers.registry import register

BELGIUM = ("belgium", "belgique", "belgië", "belgie", "louvain-la-neuve", "brussels")


@register
class ALKScraper(TeamtailorScraper):
    key = "alk"
    label = "ALK"
    base_url = "https://careers.alk.net"
    careers_url = "https://careers.alk.net/jobs?query=belgium"

    def fetch(self) -> list[JobPosting]:
        response = self.session.get(self.feed_url, timeout=30)
        response.raise_for_status()
        self.sleep()
        root = ET.fromstring(response.content)
        return [
            self._parse_item(item)
            for item in root.findall("./channel/item")
            if _in_belgium(item)
        ]


def _in_belgium(item: ET.Element) -> bool:
    places = " ".join(
        (node.text or "")
        for node in item.iter()
        if node.tag.startswith("{" + TT_NS["tt"] + "}")
    ).casefold()
    return any(token in places for token in BELGIUM)

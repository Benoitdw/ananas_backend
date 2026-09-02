"""Utilitaires HTTP partages par les scrapers.

Repris du POC ../job_an/scrape_partners.py: une session unique avec un
User-Agent explicite, et de quoi normaliser le texte extrait du HTML.
"""

from __future__ import annotations

import html
import json
import re

import requests
from bs4 import BeautifulSoup

USER_AGENT = "Mozilla/5.0 (compatible; ananas-bot/1.0; +https://github.com/ananas)"

session = requests.Session()
session.headers.update({"User-Agent": USER_AGENT})


def txt(node) -> str:
    """Texte d'un noeud BeautifulSoup, espaces normalises. '' si le noeud est None."""
    return re.sub(r"\s+", " ", node.get_text(" ", strip=True)) if node else ""


def get_soup(url: str, *, sess: requests.Session | None = None, timeout: int = 30) -> BeautifulSoup:
    r = (sess or session).get(url, timeout=timeout)
    r.raise_for_status()
    return BeautifulSoup(r.text, "html.parser")


def get_json(url: str, *, sess: requests.Session | None = None, timeout: int = 30, **kwargs):
    """Pour les sites dont les offres viennent d'une API JSON (cas frequent:
    Greenhouse, Lever, Workable, Recruitee...)."""
    r = (sess or session).get(url, timeout=timeout, **kwargs)
    r.raise_for_status()
    return r.json()


def decode_cfemail(hex_str: str) -> str:
    """Decode l'obfuscation email de Cloudflare (attribut data-cfemail)."""
    try:
        data = bytes.fromhex(hex_str)
        return "".join(chr(b ^ data[0]) for b in data[1:])
    except ValueError:
        return ""


def html_to_text(raw: str, limit: int = 8000) -> str:
    """Texte lisible a partir d'un fragment HTML.

    Les descriptions d'offres arrivent souvent en HTML echappe dans un flux
    (RSS, JSON d'ATS). On garde le texte: c'est ce que lit l'extraction de
    caracteristiques, la mise en forme ne l'interesse pas.
    """
    if not raw:
        return ""
    soup = BeautifulSoup(html.unescape(raw), "html.parser")
    return re.sub(r"\s+", " ", soup.get_text(" ", strip=True)).strip()[:limit]


def jsonld_job_posting(html: str) -> dict | None:
    """Bloc schema.org JobPosting d'une page, s'il y en a un.

    C'est un standard: quand un site le publie, c'est une source plus sure que
    n'importe quel selecteur CSS — il ne bouge pas a la prochaine refonte.
    """
    for match in re.finditer(
        r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', html, re.S
    ):
        try:
            data = json.loads(match.group(1))
        except json.JSONDecodeError:
            continue
        # Certains sites emballent plusieurs entites dans un tableau ou un @graph
        for node in data if isinstance(data, list) else data.get("@graph", [data]):
            if isinstance(node, dict) and node.get("@type") == "JobPosting":
                return node
    return None


def absolutize(base: str, href: str) -> str:
    """Transforme un href relatif en URL absolue."""
    from urllib.parse import urljoin

    return urljoin(base, href)

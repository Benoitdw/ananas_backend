"""Utilitaires HTTP partages par les scrapers.

Repris du POC ../job_an/scrape_partners.py: une session unique avec un
User-Agent explicite, et de quoi normaliser le texte extrait du HTML.
"""

from __future__ import annotations

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


def absolutize(base: str, href: str) -> str:
    """Transforme un href relatif en URL absolue."""
    from urllib.parse import urljoin

    return urljoin(base, href)

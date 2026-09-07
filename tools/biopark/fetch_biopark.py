"""Telecharge l'annuaire /community/ de biopark.be dans ``pages/``.

Trois listes sont d'abord recuperees — l'annuaire complet, puis les deux
categories Odoo "members" et "partners" qui donnent le rattachement de chaque
fiche — puis chaque fiche detail.

Ce script ne fait que descendre les pages: l'extraction est dans
``parse_biopark.py``, pour qu'ajuster un selecteur ne coute pas 157 requetes.
Le cache est le repertoire ``pages/``; le relancer ne retelecharge que ce qui
manque, le vider force une mise a jour complete.

    python3 fetch_biopark.py
"""

import html
import os
import re
import time
import urllib.request

BASE = "https://www.biopark.be"
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "pages")

# ppg=500 sort les 157 fiches d'un coup au lieu des 20 par defaut d'Odoo.
LISTINGS = (
    ("biopark_list.tsv", "/community?ppg=500"),
    ("cat_members-1.txt", "/community/category/members-1?ppg=500"),
    ("cat_partners-24.txt", "/community/category/partners-24?ppg=500"),
)
LINK = re.compile(r'itemprop="name" href="/community/([^"?]*)[^"]*" content="([^"]*)"')


def get(url, cache_name):
    path = os.path.join(CACHE, cache_name)
    if os.path.exists(path) and os.path.getsize(path) > 5000:
        return open(path, encoding="utf-8").read()
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "en"})
    with urllib.request.urlopen(req, timeout=30) as r:
        body = r.read().decode("utf-8", "replace")
    open(path, "w", encoding="utf-8").write(body)
    time.sleep(0.4)  # on ne martele pas le site pour 157 pages
    return body


def refresh_listings():
    """(Re)ecrit l'annuaire complet et les deux listes de categories."""
    for fname, path in LISTINGS:
        page = get(BASE + path, fname.rsplit(".", 1)[0] + ".html")
        links = LINK.findall(page)
        with open(os.path.join(HERE, fname), "w", encoding="utf-8") as f:
            for slug, name in links:
                f.write(f"{slug}\t{html.unescape(name)}\n" if fname.endswith(".tsv")
                        else f"{slug}\n")
        print(f"  {fname:22} {len(links):3} fiches")


def main():
    os.makedirs(CACHE, exist_ok=True)
    refresh_listings()
    entries = [line.rstrip("\n").split("\t")
               for line in open(os.path.join(HERE, "biopark_list.tsv"), encoding="utf-8")
               if line.strip()]
    for i, (slug, name) in enumerate(entries, 1):
        get(f"{BASE}/community/{slug}", slug + ".html")
        print(f"  {i:3}/{len(entries)} {name}")
    print(f"{len(entries)} fiches dans {CACHE} — enchainer sur parse_biopark.py")


if __name__ == "__main__":
    main()

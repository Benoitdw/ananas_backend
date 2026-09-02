"""Geocodage d'adresses via Nominatim (OpenStreetMap).

Porte depuis le POC ../job_an/scrape_partners.py, ou cette cascade avait ete
mise au point contre les 81 adresses reelles de BioWin: elles melangent boites
postales, batiments et campus ("Park 7 Campus, Xenon building Hermeslaan 11 -
2") que Nominatim ne digere pas tel quel.

La strategie est de degrader progressivement plutot que d'echouer:
    rue complete -> rue nettoyee -> ville -> code postal -> nom de la commune
et de retourner **comment** le point a ete place, pour que l'interface puisse
le signaler honnetement a l'utilisateur.
"""

from __future__ import annotations

import logging
import re
import threading
import time

import requests

log = logging.getLogger(__name__)

NOMINATIM = "https://nominatim.openstreetmap.org/search"
# Nominatim impose 1 requete/seconde et un User-Agent identifiable
MIN_INTERVAL = 1.1
USER_AGENT = "ananas-bot/1.0 (https://github.com/ananas)"

# Corrections vues dans les donnees BioWin
TYPOS = {"BRUXELELS": "Bruxelles", "Dion Valmont": "Dion-Valmont"}

# Precisions, de la meilleure a la pire
ADDRESS = "adresse"
CITY = "ville"
NAME = "approx. (nom)"
NONE = "non localise"

_session = requests.Session()
_session.headers.update({"User-Agent": USER_AGENT})

# Cache process-local: une soumission repetee ou deux utilisateurs proposant
# la meme entreprise ne paient pas deux fois la seconde d'attente.
_cache: dict[str, list[float] | None] = {}
_lock = threading.Lock()
_last_call = 0.0


def street_candidates(street: str) -> list[str]:
    """Variantes d'une rue a essayer, de la plus complete a la plus simple."""
    base = re.sub(r"\b(bte|boite|boîte|box|bus)\b\.?\s*[\w/-]*", "", street, flags=re.I)
    base = re.sub(r"\s{2,}", " ", base).strip(" ,-")
    out = [street, base]
    # "Avenue d'Ecolys, 2" -> "Avenue d'Ecolys 2"
    out.append(re.sub(r",\s*(?=\d)", " ", base))
    # garde le dernier segment qui ressemble a "nom de rue + numero"
    for seg in reversed([x.strip() for x in base.split(",")]):
        if m := re.match(
            r"^(?:.*\s)?([A-Za-zÀ-ÿ'’.\-]+(?:\s[A-Za-zÀ-ÿ'’.\-]+)*)\s+(\d+)\s*(?:[-/]\s*\d+)?$", seg
        ):
            out.append(f"{m.group(1)} {m.group(2)}")
            break
    seen: set[str] = set()
    return [x for x in out if x and not (x in seen or seen.add(x))]


def clean_city(city: str) -> str:
    for bad, good in TYPOS.items():
        city = re.sub(re.escape(bad), good, city, flags=re.I)
    return re.sub(r"\s+", " ", city).strip()


def _query(params: dict) -> list[float] | None:
    """Un appel Nominatim, cache et limite en debit."""
    global _last_call
    key = repr(sorted(params.items()))

    with _lock:
        if key in _cache:
            return _cache[key]

        elapsed = time.monotonic() - _last_call
        if elapsed < MIN_INTERVAL:
            time.sleep(MIN_INTERVAL - elapsed)

        try:
            r = _session.get(NOMINATIM, params={**params, "format": "jsonv2", "limit": 1}, timeout=15)
            r.raise_for_status()
            res = r.json()
            hit = [float(res[0]["lat"]), float(res[0]["lon"])] if res else None
        except (requests.RequestException, ValueError, KeyError, IndexError) as exc:
            log.warning("geocodage echoue pour %s: %s", params, exc)
            hit = None

        _last_call = time.monotonic()
        # Le cache retient aussi les echecs: inutile de reessayer une adresse
        # que Nominatim ne connait pas.
        _cache[key] = hit
        return hit


def geocode(
    *, street: str = "", city: str = "", country: str = "", name: str = ""
) -> tuple[float | None, float | None, str]:
    """Retourne (lat, lon, precision). Ne leve jamais.

    ``precision`` vaut 'adresse', 'ville', 'approx. (nom)' ou 'non localise' —
    les memes valeurs que celles importees du POC, pour que l'interface n'ait
    qu'un seul vocabulaire a comprendre.
    """
    city = clean_city(city)
    country = (country or "Belgium").strip()
    belgian = country.lower().startswith("belg")

    attempts: list[tuple[dict, str]] = []
    if street and city:
        attempts += [({"q": f"{c}, {city}, {country}"}, ADDRESS) for c in street_candidates(street)]
    if street and not city:
        attempts.append(({"q": f"{street}, {country}"}, ADDRESS))
    if city:
        attempts.append(({"q": f"{city}, {country}"}, CITY))
        # "1325 Dion-Valmont" -> code postal seul, puis nom de commune seul
        if m := re.match(r"^(\d{4,5})\s+(.+)$", city):
            attempts.append(({"postalcode": m.group(1), "country": country}, CITY))
            attempts.append(({"q": f"{m.group(2)}, {country}"}, CITY))
    # dernier recours quand aucune adresse n'est fournie
    if not city and not street and name:
        attempts.append(({"q": name, "countrycodes": "be"}, NAME))

    for params, precision in attempts:
        if belgian and "countrycodes" not in params and "country" not in params:
            params = {**params, "countrycodes": "be"}
        if hit := _query(params):
            return hit[0], hit[1], precision

    return None, None, NONE

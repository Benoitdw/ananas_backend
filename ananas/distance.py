"""Distance a vol d'oiseau entre deux points, et tri d'entreprises autour d'un
domicile.

Volontairement en Python plutot qu'en SQL: le repertoire tient en memoire (une
centaine de lignes), et surtout PostGIS n'est pas installe — une formule de
haversine en SQL brut serait illisible et non portable vers SQLite pour les
tests. Le cout est nul a cette echelle.

La Terre est traitee comme une sphere: a l'echelle de la Belgique, l'ecart avec
l'ellipsoide WGS84 est de l'ordre de 0,3 %, tres en dessous de la precision des
positions elles-memes (une entreprise geocodee "ville" est deja a plusieurs
kilometres de son adresse reelle).
"""

from __future__ import annotations

from math import asin, cos, radians, sin, sqrt

EARTH_RADIUS_KM = 6371.0088


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distance orthodromique en kilometres entre deux points en degres."""
    phi1, phi2 = radians(lat1), radians(lat2)
    dphi = phi2 - phi1
    dlambda = radians(lon2 - lon1)
    h = sin(dphi / 2) ** 2 + cos(phi1) * cos(phi2) * sin(dlambda / 2) ** 2
    return 2 * EARTH_RADIUS_KM * asin(sqrt(h))


def distance_from(
    home: tuple[float, float] | None, lat: float | None, lon: float | None
) -> float | None:
    """Distance au domicile, ou None si l'un des deux points manque.

    None n'est pas 0: une entreprise sans coordonnees n'est pas "sur place",
    elle est simplement hors du classement — c'est ce que l'interface affiche
    par un tiret plutot que par une valeur inventee.
    """
    if home is None or lat is None or lon is None:
        return None
    return round(haversine_km(home[0], home[1], lat, lon), 1)

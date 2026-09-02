"""Remplit lat / lon / geo_precision d'un CSV du repertoire, sur place.

    python -m ananas.geocode_csv data/biotech-belgique.csv [--force]

Le seed ne geocode pas: il lit des coordonnees deja presentes dans le CSV.
C'est deliberé — Nominatim est limite a une requete par seconde, et un seed
est lance a chaque demarrage. Le prix est donc paye **une fois**, ici, quand
le CSV est ecrit, et le resultat est versionne avec lui.

Seules les lignes sans coordonnees sont interrogees (``--force`` les reprend
toutes), pour qu'ajouter dix entreprises a un fichier de cent coute dix
secondes et non cent.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

from ananas.geocoding import geocode

# Ecrites en plus des colonnes deja presentes dans le fichier
GEO_FIELDS = ("lat", "lon", "geo_precision")


def geocode_csv(path: Path, force: bool = False) -> tuple[int, int]:
    """Retourne (lignes geocodees, lignes non localisees)."""
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)

    for field in GEO_FIELDS:
        if field not in fieldnames:
            fieldnames.append(field)

    done = failed = 0
    for row in rows:
        if not force and (row.get("lat") or "").strip():
            continue
        lat, lon, precision = geocode(
            street=(row.get("street") or "").strip(),
            city=(row.get("city") or "").strip(),
            country=(row.get("country") or "").strip(),
            name=(row.get("name") or "").strip(),
        )
        row["lat"] = "" if lat is None else f"{lat:.7f}"
        row["lon"] = "" if lon is None else f"{lon:.7f}"
        row["geo_precision"] = precision
        print(f"  {row.get('name', '?'):40} {precision:14} {row['lat']} {row['lon']}")
        if lat is None:
            failed += 1
        else:
            done += 1

    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    return done, failed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ananas-geocode-csv", description=__doc__)
    parser.add_argument("csv", type=Path)
    parser.add_argument(
        "--force", action="store_true", help="reprend aussi les lignes deja geocodees"
    )
    args = parser.parse_args(argv)

    if not args.csv.exists():
        raise SystemExit(f"CSV introuvable: {args.csv}")

    done, failed = geocode_csv(args.csv, force=args.force)
    print(f"{done} localisees, {failed} non localisees -> {args.csv}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

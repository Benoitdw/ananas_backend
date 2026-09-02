"""Complete ``website`` / ``careers_url`` des fiches, depuis ``data/company-web.csv``.

    python -m ananas.enrich [--csv chemin] [--force]

Le repertoire ``curated`` (biotech-belgique.csv) arrive sans site web ni page
carrieres : ces deux champs sont propres a Ananas, ils ne viennent d'aucune
source amont. Ce script les pose a partir d'un CSV ``slug,website,careers_url``
tenu a la main.

Par defaut il ne **remplit que les blancs** : une cellule vide n'efface jamais
une valeur deja en base (un ``careers_url`` auto-renseigne au liage d'un
scraper, typiquement). ``--force`` ecrase avec ce que dit le CSV, cellules
vides comprises.

Idempotent : relancer ne fait rien de plus.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

from sqlalchemy import select

from ananas.db import session_scope
from ananas.models import Company

DEFAULT_CSV = Path(__file__).resolve().parent.parent / "data" / "company-web.csv"
FIELDS = ("website", "careers_url")


def enrich(csv_path: Path = DEFAULT_CSV, force: bool = False) -> tuple[int, int]:
    """Retourne (fiches modifiees, lignes sans entreprise correspondante)."""
    if not csv_path.exists():
        raise SystemExit(f"CSV introuvable: {csv_path}")

    with csv_path.open(encoding="utf-8", newline="") as f:
        rows = [r for r in csv.DictReader(f) if (r.get("slug") or "").strip()]

    changed = missing = 0
    with session_scope() as db:
        by_slug = {c.slug: c for c in db.scalars(select(Company))}
        for row in rows:
            company = by_slug.get(row["slug"].strip())
            if company is None:
                print(f"  ? slug inconnu, ignore: {row['slug']}")
                missing += 1
                continue

            touched = False
            for field in FIELDS:
                value = (row.get(field) or "").strip()
                current = getattr(company, field) or ""
                if force:
                    if value != current:
                        setattr(company, field, value or None)
                        touched = True
                elif value and not current:
                    setattr(company, field, value)
                    touched = True

            if touched:
                print(f"  + {company.slug}")
                changed += 1

    return changed, missing


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ananas-enrich", description=__doc__)
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    parser.add_argument(
        "--force",
        action="store_true",
        help="ecrase les valeurs existantes (cellules vides comprises)",
    )
    args = parser.parse_args(argv)

    changed, missing = enrich(args.csv, force=args.force)
    print(f"{changed} fiche(s) completee(s), {missing} ligne(s) sans correspondance")
    return 0


if __name__ == "__main__":
    sys.exit(main())

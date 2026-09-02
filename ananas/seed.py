"""Import du repertoire d'entreprises depuis les CSV de ``data/``.

    python -m ananas.seed [--csv chemin]... [--update] [--link-only]

Deux fichiers sont charges par defaut, dans cet ordre:

  - ``partners.csv``          les 81 partenaires du POC BioWin (source 'biowin')
  - ``biotech-belgique.csv``  49 biotech/pharma belges (source 'curated')

Le geocodage est deja paye a l'ecriture du CSV (Nominatim, ~1 requete/seconde,
voir ``python -m ananas.geocode_csv``): les entreprises arrivent avec leur
lat/lon, la carte est peuplee des le premier demarrage.

Idempotent: l'upsert se fait sur ``source_url`` quand le CSV en fournit un
(BioWin), sinon sur le couple (source, slug) — la relance ne cree pas de
doublon dans les deux cas. Par defaut les entreprises deja presentes ne sont
pas modifiees, pour ne pas ecraser un ``careers_url`` renseigne a la main;
``--update`` force le rafraichissement des champs descriptifs (jamais
careers_url ni scraper_key).

Le seed se termine par un auto-liage: tout scraper dont la ``key`` egale le
slug d'une entreprise est branche automatiquement. C'est ce qui permet de dire
"ajouter un scraper = deposer un fichier": nomme ta classe avec la cle
``qbd-group`` et l'entreprise du meme slug est reliee sans SQL a la main.
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
import unicodedata
from collections.abc import Sequence
from pathlib import Path

from sqlalchemy import select

from ananas.db import session_scope
from ananas.models import SOURCE_BIOWIN, Company
from ananas.scrapers.registry import load_scrapers

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DEFAULT_CSVS = (DATA_DIR / "partners.csv", DATA_DIR / "biotech-belgique.csv")

# Champs recopies tels quels du CSV. careers_url et scraper_key n'y sont pas:
# ils sont propres a Ananas et se remplissent a la main.
CSV_FIELDS = (
    "name type core_business other_tags baseline description "
    "street city postal_code country address "
    "website email phone linkedin logo geo_precision"
).split()


def slugify(value: str) -> str:
    """'QbD Group' -> 'qbd-group'. Sert de cle lisible dans les URL et la CLI."""
    ascii_only = (
        unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    )
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_only.lower()).strip("-")
    return slug[:160] or "entreprise"


def unique_slug(base: str, taken: set[str]) -> str:
    slug, n = base, 2
    while slug in taken:
        slug = f"{base}-{n}"
        n += 1
    taken.add(slug)
    return slug


def _as_float(raw: str) -> float | None:
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def load_rows(csv_path: Path) -> list[dict]:
    with csv_path.open(encoding="utf-8", newline="") as f:
        return [row for row in csv.DictReader(f) if (row.get("name") or "").strip()]


def seed(
    csv_paths: Sequence[Path] = DEFAULT_CSVS, update: bool = False
) -> tuple[int, int, int]:
    """Retourne (crees, mis a jour, inchanges)."""
    for csv_path in csv_paths:
        if not csv_path.exists():
            raise SystemExit(f"CSV introuvable: {csv_path}")

    created = updated = untouched = 0

    with session_scope() as db:
        companies = list(db.scalars(select(Company)))
        by_url = {c.source_url: c for c in companies if c.source_url}
        # Cle de repli pour les CSV sans fiche d'origine. Le couple (source,
        # slug) et non le slug seul: une entreprise proposee par un
        # utilisateur porte le meme slug qu'une homonyme du repertoire, et le
        # seed n'a pas a l'ecraser.
        by_source_slug = {(c.source, c.slug): c for c in companies}
        taken = {c.slug for c in companies}

        for csv_path in csv_paths:
            for row in load_rows(csv_path):
                values = {field: (row.get(field) or "").strip() for field in CSV_FIELDS}
                values["source"] = (row.get("source") or "").strip() or SOURCE_BIOWIN
                values["source_url"] = (row.get("url") or "").strip()
                values["lat"] = _as_float(row.get("lat"))
                values["lon"] = _as_float(row.get("lon"))

                slug = slugify(values["name"])
                if values["source_url"]:
                    company = by_url.get(values["source_url"])
                else:
                    company = by_source_slug.get((values["source"], slug))

                if company is None:
                    company = Company(slug=unique_slug(slug, taken), **values)
                    db.add(company)
                    by_source_slug[(company.source, company.slug)] = company
                    if company.source_url:
                        by_url[company.source_url] = company
                    created += 1
                elif update:
                    for key, value in values.items():
                        setattr(company, key, value)
                    updated += 1
                else:
                    untouched += 1

    return created, updated, untouched


def link_scrapers() -> list[tuple[str, str]]:
    """Branche chaque scraper enregistre sur l'entreprise de meme slug.

    Ne touche jamais a un scraper_key deja renseigne: un liage manuel
    (scraper dont la cle differe du slug) reste prioritaire.
    """
    scrapers = load_scrapers()
    linked: list[tuple[str, str]] = []

    with session_scope() as db:
        for key, cls in sorted(scrapers.items()):
            company = db.scalar(select(Company).where(Company.slug == key))
            if company is None or company.scraper_key == key:
                continue
            if company.scraper_key:
                continue  # deja branche sur un autre scraper, on n'ecrase pas
            company.scraper_key = key
            if not company.careers_url and cls.careers_url:
                company.careers_url = cls.careers_url
            linked.append((company.name, key))

    return linked


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ananas-seed", description=__doc__)
    parser.add_argument(
        "--csv",
        type=Path,
        action="append",
        dest="csvs",
        help=f"a repeter pour cumuler; defaut: {', '.join(p.name for p in DEFAULT_CSVS)}",
    )
    parser.add_argument(
        "--update",
        action="store_true",
        help="rafraichit les entreprises deja presentes (careers_url et scraper_key preserves)",
    )
    parser.add_argument(
        "--link-only",
        action="store_true",
        help="ne fait que rebrancher les scrapers sur les entreprises de meme slug",
    )
    args = parser.parse_args(argv)

    if not args.link_only:
        created, updated, untouched = seed(args.csvs or DEFAULT_CSVS, update=args.update)
        total = created + updated + untouched
        print(
            f"{total} entreprises importees "
            f"({created} creees, {updated} mises a jour, {untouched} inchangees)"
        )

    linked = link_scrapers()
    if linked:
        for name, key in linked:
            print(f"  scraper branche: {name} -> {key}")
    else:
        print("  aucun nouveau scraper a brancher")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Genere api/BIOPARK.md, la liste de suivi des entreprises importees du BioPark."""
import csv, os, re, unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "..", "data")
OUT = os.path.join(HERE, "..", "..", "BIOPARK.md")


def slugify(value):
    ascii_only = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "-", ascii_only.lower()).strip("-")[:160] or "entreprise"


rows = list(csv.DictReader(open(os.path.join(DATA, "biopark.csv"), encoding="utf-8")))
scrapers = {f[:-3].replace("_", "-") for f in os.listdir(os.path.join(HERE, "..", "..", "ananas", "scrapers"))
            if f.endswith(".py") and not f.startswith("__")}

# Regroupe par core_business pour que la liste soit attaquable par lots.
groups = {}
for r in rows:
    groups.setdefault(r["core_business"] or "(non classe)", []).append(r)

lines = []
w = lines.append
w("# BioPark Charleroi — suivi de l'import\n")
w("Les 137 membres et partenaires de <https://www.biopark.be/community>, importes")
w("dans `data/biopark.csv` (source `biopark`) et charges par `python -m ananas.seed`.")
w("Les 20 fiches deja presentes dans `partners.csv` / `biotech-belgique.csv` ont")
w("ete ecartees a l'import (liste en fin de fichier).\n")
w("Etape suivante : brancher les scrapers. Convention inchangee — `key` du scraper")
w("= `slug` de l'entreprise, liage par `python -m ananas.seed --link-only`.\n")
w("Colonnes : **site** = site officiel connu, **carr.** = page carrieres reperee,")
w("**scraper** = module ecrit et branche.\n")
w("## Import\n")
w("- [x] Extraction des 157 fiches `/community/` (nom, type, core business,")
w("      taille, adresse, site, logo, description)")
w("- [x] Dedoublonnage contre `partners.csv` + `biotech-belgique.csv` (20 ecartees)")
w("- [x] Ecriture de `data/biopark.csv` (137 lignes) et ajout a `DEFAULT_CSVS`")
w("- [x] Geocodage Nominatim (`python -m ananas.geocode_csv data/biopark.csv`) :")
w(f"      {sum(1 for r in rows if r['lat'])}/{len(rows)} placees")
w("- [x] `python -m ananas.seed` : 137 creees, 267 entreprises en base")
w("- [ ] Reperer les pages carrieres (colonne **carr.**)")
w("- [ ] Ecrire les scrapers, par ordre de volume d'offres\n")

w("## Entreprises importees\n")
for cb in sorted(groups, key=lambda k: (k == "(non classe)", k.lower())):
    items = sorted(groups[cb], key=lambda r: r["name"].lower())
    w(f"### {cb} ({len(items)})\n")
    w("| slug | entreprise | type | site | carr. | scraper |")
    w("|---|---|---|---|---|---|")
    for r in items:
        slug = slugify(r["name"])
        site = f"[site]({r['website']})" if r["website"] else "—"
        done = "x" if slug in scrapers else " "
        w(f"| `{slug}` | {r['name']} | {r['type'] or '—'} | {site} | [ ] | [{done}] |")
    w("")

w("## Ecartees — doublons\n")
w("Deja dans le repertoire, l'import ne les recree pas.\n")
dups = [
    ("2 Bridge", ""), ("Agence du Numérique", ""), ("BioWin", ""), ("Calysta", ""),
    ("Cap4HR", ""), ("Catalent", ""), ("Forem", "Le Forem"),
    ("Icosa Europe", "ICOSA EUROPE"), ("Ignity", ""), ("InhaTarget Therapeutics", ""),
    ("Jansen Cleanrooms & Labs", ""), ("My engineering", "My Engineering SRL"),
    ("Ooho", "Ooho bv"), ("PwC Belgium", ""), ("QBD Group", "QbD Group"),
    ("Quantoom Biosciences", ""), ("Sales Attitude", ""), ("Strand", ""),
    ("Thermo Fisher Scientific", "Thermo Fisher Scientific – Henogen"),
    ("Wallonie Entreprendre Life Sciences", "Wallonie Entreprendre"),
]
w("| fiche BioPark | deja en base sous |")
w("|---|---|")
for a, b in dups:
    w(f"| {a} | {b or a} |")
w("")
w("La fiche BioPark de **Thermo Fisher Scientific** donne l'adresse precise du")
w("site de Charleroi (16 rue Clement Ader, 6041) — a reporter sur la ligne")
w("`thermo-fisher-scientific-henogen` si le point sur la carte est approximatif.\n")

sans_site = sorted(r["name"] for r in rows if not r["website"])
sans_geo = sorted(r["name"] for r in rows if not r["lat"])
w("## Trous connus\n")
w("Manques de la source, pas de l'import : la fiche BioPark elle-meme est vide.\n")
w(f"- **{len(sans_site)} sans site web**, donc sans point de depart pour un scraper :")
w("  " + ", ".join(sans_site) + ".")
w(f"- **{len(sans_geo)} sans coordonnees** (aucune adresse sur la fiche), absentes")
w("  de la carte tant qu'une adresse n'est pas saisie a la main :")
w("  " + ", ".join(sans_geo) + ".")
w("- Le telephone de `REDSYSTEM` est recopie tel quel de la source, ou il est")
w("  malforme (`+32 (0470 47 51 07`).")
w("")

open(OUT, "w", encoding="utf-8").write("\n".join(lines))
print(f"{OUT} — {len(lines)} lignes, {len(rows)} entreprises, {len(groups)} groupes")

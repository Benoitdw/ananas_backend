# Import de l'annuaire BioPark Charleroi

Produit `api/data/biopark.csv` (les 137 membres et partenaires de
<https://www.biopark.be/community> qui manquaient au repertoire) et la liste de
suivi `api/BIOPARK.md`. Aucune dependance: stdlib Python uniquement.

Ces scripts ne tournent **pas** au demarrage. Comme le geocodage, le prix est
paye une fois, ici, et le resultat est versionne dans `data/`. On ne les
relance que pour rafraichir l'annuaire.

```bash
cd api/tools/biopark
python3 fetch_biopark.py     # 157 pages -> pages/ (cache; vider pour rafraichir)
python3 parse_biopark.py     # pages/ -> biopark_raw.csv (extraction brute)
python3 build_csv.py         # -> ../../data/biopark.csv (dedoublonne, format seed)
python3 gen_todo.py          # -> ../../BIOPARK.md

cd ../../..
docker compose exec backend python -m ananas.geocode_csv data/biopark.csv
docker compose exec backend python -m ananas.seed
```

`build_csv.py` reprend les `lat`/`lon` deja presentes dans `biopark.csv` quand
l'adresse resolue n'a pas bouge: le regenerer ne rejette pas 137 requetes
Nominatim, et `geocode_csv` ne reprend que les nouvelles lignes.

## Ce que fait `build_csv.py`

- **Dedoublonne** contre `partners.csv` et `biotech-belgique.csv`. La comparaison
  se fait sur le nom normalise (accents, casse, formes juridiques `SA`/`SRL`/…
  retirees); les libelles qui divergent trop pour etre rapproches ainsi sont
  listes a la main dans `ALIASES`. 20 fiches sont ecartees, voir `BIOPARK.md`.
- **Decoupe l'adresse** telle que la fiche l'affiche (format Google Maps,
  `rue, code postal ville, pays`) en `street` / `postal_code` / `city` /
  `country`. Les quatre adresses au format inhabituel sont dans `ADDRESS_FIXES`.
- **Aligne le vocabulaire** sur les facettes existantes: `Public/non-profit
  organisation` de BioPark devient `Public/Non-profit organisation` comme chez
  BioWin. Categorie, taille, technologie et aire therapeutique partent dans
  `other_tags`, que l'API interroge au meme titre que `core_business`.
- Pose `source=biopark` et `url` = la fiche BioPark d'origine, sur laquelle le
  seed reconcilie: relancer l'import ne cree pas de doublon.

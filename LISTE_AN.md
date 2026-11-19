# Liste An — suivi

La liste d'employeurs scientifiques de « Listes Emplois Scientifiques.xlsx »
(2026-11-19), importee dans `data/liste-an.csv` et chargee par
`python -m ananas.seed`.

**Une ligne = une fiche du repertoire**, designee par son `slug`. La moitie de
la liste etait deja connue (BioWin, BioPark, repertoire Ananas, proposee par
un utilisateur): ces fiches ne sont ni dupliquees ni modifiees, elles recoivent
seulement le tag **« Liste An »**. Les autres sont creees avec la source
`liste-an` (25 sur une base vierge, 19 sur une base qui a deja les six fiches
proposees par un utilisateur le 2026-09-07: Saint-Luc, UCLouvain x2, EPHEC,
Institut de Duve, HE Vinci).

Sur la carte, la page d'administration et l'API, le filtre **provenance
« Liste An »** montre les 62 fiches: celles creees par la liste *et* celles
qui portent son tag (`LIST_TAGS` dans `models.py`, `matchesSource` dans
`web/src/lib/sources.ts`). Le filtre par tag « Liste An » donne le meme
resultat.

GSK compte deux lignes (Wavre et Rixensart, deux fiches existantes).

## Scrapers

Convention inchangee: `key` du scraper = `slug` de la fiche, liage par
`python -m ananas.seed --link-only`. Offres comptees le 2026-11-19, depuis un
poste de developpement (pas depuis le conteneur).

### Nouveaux (29)

| slug | ATS / methode | module | offres |
|---|---|---|---|
| `services-publiques-sciences-r-d` | travaillerpour.be (Drupal) | `travaillerpour.py` | 2 |
| `services-publiques-toutes-les-offres` | travaillerpour.be (Drupal) | `travaillerpour.py` | 15 |
| `fondation-contre-le-cancer` | CVWarehouse (cartes cancer.be) | `fondation_cancer.py` | 2 |
| `ucl-personnels-academiques` | SuccessFactors jobs2web (RSS) | `ucl.py` | 0 |
| `institut-de-duve` | API Sanity publique + PDF | `de_duve.py` | 1 |
| `haute-ecole-leonard-de-vinci` | TalentSquare | `vinci.py` | 5 |
| `hopitaux-iris-sud` | Beehire (API JSON) | `iris_sud.py` + `beehire.py` | 26 |
| `zoetis-belgium` | Workday `zoetis_intl`, facette site Zaventem | `zoetis.py` | 3 |
| `diasource-immunoassays` | site propre `/job-offers` | `diasource.py` | 0 |
| `alk` | Teamtailor (RSS), filtre Belgique | `alk.py` | 1 |
| `lims-mbnext` | annonces PDF (WordPress) | `lims.py` | 3 |
| `clinique-saint-pierre-ottignies` | TalentFinder, categorie medico-technique | `talentfinder_hospitals.py` + `talentfinder.py` | 1 |
| `chu-helora` | TalentFinder (paramedical) | `talentfinder_hospitals.py` | 0 |
| `sgs-lab-simon` | SmartRecruiters `SGS`, Belgique | `sgs.py` | 52 |
| `eurofins-belgium` | SmartRecruiters `Eurofins`, Belgique | `eurofins.py` | 36 |
| `croix-rouge-de-belgique` | site WordPress, secteurs filtres | `croix_rouge.py` | 11 |
| `astrivax` | API REST WordPress (`vacancies`) | `astrivax.py` | 0 |
| `muna-therapeutics` | BambooHR | `muna.py` + `bamboohr.py` | 0 |
| `institute-of-pathology-and-genetics-ipg` | TalentSquare `ipg` | `ipg.py` | 4 |
| `seqalis` | TalentSquare `ipg`, offres citant Seqalis | `ipg.py` | 0 |
| `bioxodes` | biopark.jobs | `bioxodes.py` + `bioparkjobs.py` | 0 |
| `chu-ucl-namur` | Skeeled (liens depuis la page WP) | `skeeled_clients.py` + `skeeled.py` | 24 |
| `bepharbel` | Skeeled | `skeeled_clients.py` | 0 |
| `cellcarta` | JazzHR, filtre Belgique | `cellcarta.py` + `jazzhr.py` | 7 |
| `chemosensoryx` | veille de l'etat vide | `watched_pages.py` | 0 |
| `one2treat` | veille de l'etat vide | `watched_pages.py` | 0 |
| `aboleris-pharma` | veille de l'etat vide | `watched_pages.py` | 0 |
| `2-bridge` | veille de l'onglet « Job opportunity » | `watched_pages.py` | 0 |
| `center-for-microscopy-and-molecular-imaging-cmmi` | veille du « Coming soon » | `watched_pages.py` | 0 |

**Veille de l'etat vide** (`page_watch.py`): pour une page qui n'a jamais
montre d'offre, un parseur serait devine. On surveille plutot la phrase
« aucune offre ». Si elle disparait, une offre « nouvelle(s) offre(s) sur la
page carrieres » remonte (avec le texte de la page): c'est la notification, et
le signal pour ecrire le vrai parseur.

### Deja couverts par un scraper existant (20)

`sciensano`, `cliniques-universitaires-saint-luc`,
`ucl-personnels-administratifs`, `ucl-personnels-scientifiques`,
`haute-ecole-ephec`, `equaly`, `sobi-swedish-orphan-biovitrum`,
`novadip-biosciences`, `cellistic`, `gsk-wavre`, `gsk-rixensart`,
`abbvie-belgium`, `ucb-pharma-braine-l-alleud`, `bristol-myers-squibb`,
`univercells-technologies`, `terumo-europe`, `sanofi-belgium`,
`novartis-pharma`, `prothya-biosolutions`, et **AstraZeneca** →
`alexion-pharma-belgium`, dont le scraper remonte deja tous les postes belges
du groupe AstraZeneca (meme Workday).

Les filtres de la liste plus fins que ceux des scrapers existants (UCB
« R&D », GSK « Science & Technology », Eurofins `deptid`) ne sont pas
reproduits: on garde tout le site, le score de correspondance fait le tri.

### A suivre a la main (13)

Fond bleu dans le fichier (pas de page carrieres):

- [ ] `ellion-srl` — Ellion (consultance)
- [ ] `biosenic` — BioSenic
- [ ] `alphadia` — Alphadia
- [ ] `cognivia` — Cognivia
- [ ] `santero-therapeutics` — Santero Therapeutics
- [ ] `epics-therapeuthics` — Epics Therapeutics
- [ ] `conveyxo` — convEyXO

Pas de fond bleu, mais rien d'automatisable au 2026-11-19:

- [ ] `fnrs` — **le site refuse les robots** (403 sur tout User-Agent qui se
      declare robot). Une offre en ligne (PDF). Fiche creee, pas de scraper.
- [ ] `synlab-belgium` — **coupe la connexion aux robots**, et le serveur
      n'envoie pas son certificat intermediaire. Offres en PDF sur
      `synlab.be/fr/carrieres`.
- [ ] `celyad-oncology` — **coupe la connexion aux robots**. Archive WordPress
      `celyad.com/careers/` vide.
- [ ] `montis-biosciences` — aucune page carrieres (le lien de la liste est la
      page d'accueil).
- [ ] `minoryx-therapeutics` — candidature par email uniquement
      (careers@minoryx.com), aucune liste ni phrase d'etat vide a surveiller.
- [ ] `neuvasq` — page carrieres sans liste ni phrase d'etat vide.

Pour les trois sites qui bloquent les robots, ne pas contourner le blocage en
se faisant passer pour un navigateur: c'est un refus explicite de l'editeur.

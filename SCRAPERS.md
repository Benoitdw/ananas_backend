# Scrapers — suivi

Liste de travail pour couvrir le repertoire `curated` (49 biotech/pharma
belges, `data/biotech-belgique.csv`). Voir `README.md` §*Ecrire un scraper*.

Convention : `key` du scraper = `slug` de l'entreprise → liage automatique par
`python -m ananas.seed --link-only`.

## Fait (10)

| slug | ATS | module | offres au 2026-09-02 |
|---|---|---|---|
| `qbd-group` | Teamtailor (RSS) | `qbd_group.py` | 36 |
| `gsk-wavre` | Phenom People | `gsk.py` + `phenom.py` | ✓ |
| `gsk-rixensart` | Phenom People | `gsk.py` | ✓ |
| `ucb-pharma-braine-l-alleud` | Phenom People | `ucb.py` | 80 |
| `ucb-anderlecht` | Phenom People | `ucb.py` | 46 |
| `ucb-leuven` | Phenom People | `ucb.py` | 0 (aucun poste ouvert) |
| `sanofi-belgium` | Radancy | `sanofi.py` + `radancy.py` | 5 |
| `abbvie-belgium` | Attrax (JSON-LD) | `abbvie.py` + `attrax.py` | 2 |
| `pfizer-belgium` | Workday | `pfizer.py` + `workday.py` | 8 |
| `novartis-pharma` | Workday | `novartis.py` + `workday.py` | 16 |

## Bases d'ATS reutilisables

| module | ATS | a declarer |
|---|---|---|
| `qbd_group.py::TeamtailorScraper` | Teamtailor RSS | `base_url` |
| `phenom.py::PhenomScraper` | Phenom People (`phApp.ddo`) | `base_url`, `search_params`, `town` |
| `radancy.py::RadancyScraper` | Radancy (JSON-LD) | `base_url`, `search_path`, `countries` |
| `attrax.py::AttraxScraper` | Attrax (JSON-LD) | `base_url`, `country` |
| `workday.py::WorkdayScraper` | Workday CXS JSON | `host`, `tenant`, `site`, (`country_facet_wid` ou `search_text`) |

## A faire — priorise par volume / facilite

### Grands groupes, ATS connu (rapide)

- [ ] **`bristol-myers-squibb`** — Workday `bristolmyerssquibb.wd5` / site `BMS`.
      Facette `Location_Country`. 0 offre belge au 2026-09-02 → scraper valide
      mais vide ; a poser quand même (Braine-l'Alleud).
- [ ] **`msd-belgium`** — Phenom People (`jobs.msd.com` / `msd.wd5`? à verifier).
      MSD/Merck a un gros site. Localiser Bruxelles.
- [ ] **`baxter`** — Workday `baxter.wd1` (à verifier tenant). Site de Lessines
      (production) — volume probable.
- [ ] **`catalent`** — Workday. Pas de site belge propre listé — verifier s'il
      y a des offres BE avant de poser.
- [ ] **`alexion-pharma-belgium`** — Workday `astrazeneca.wd3` / site `Careers`
      (Alexion = groupe AstraZeneca). 1 offre "Belgium" au 2026-09-02.
- [ ] **`novo-nordisk`** — ATS propre `career.novonordisk.com` (pas Workday).
      À explorer : souvent une API JSON derriere.
- [ ] **`boehringer-ingelheim`** — `jobs.boehringer-ingelheim.com` (ATS propre).
- [ ] **`roche-diagnostics`** — `careers.roche.com` (ATS propre, gros).
- [ ] **`biomerieux`** — `careers.biomerieux.com` (SmartRecruiters ? à verifier).
- [ ] **`terumo-europe`** — HQ Leuven. `terumo-europe.com/en/careers` — ATS ?
- [ ] **`thermo-fisher-scientific-henogen`** — `jobs.thermofisher.com` (ATS
      propre). Site de Gosselies (ex-Henogen). Filtrer sur Gosselies/Seneffe.

### Biotechs moyennes — souvent SmartRecruiters / Greenhouse / Lever / Recruitee

- [ ] `iteos-therapeutics` — Gosselies. Careers sur site propre
      (`iteostherapeutics.com/careers`) ; verifier s'il y a un ATS derriere
      (Greenhouse fréquent pour les biotechs NASDAQ).
- [ ] `celyad-oncology` — 0 poste annoncé, candidature par email. Basse prio.
- [ ] `univercells-technologies` / `exothera` / `quantoom-biosciences` —
      galaxie Univercells (Nivelles/Gosselies). Souvent Teamtailor ou
      SmartRecruiters — 1 base pourrait couvrir les 3.
- [ ] `novadip-biosciences` — Mont-Saint-Guibert.
- [ ] `cellistic` — Mont-Saint-Guibert (spin-off Ncardia).
- [ ] `ncardia` — Gosselies.
- [ ] `iba` — Louvain-la-Neuve. `iba-worldwide.com/careers` — SmartRecruiters ?
- [ ] `precirix` — Bruxelles.
- [ ] `icometrix` — Leuven. `icometrix.com/careers` — souvent Recruitee.
- [ ] `kantify` — Bruxelles, petite équipe.
- [ ] `prothya-biosolutions` — Bruxelles (ex-Sanquin). ATS propre probable.
- [ ] `realco` — Louvain-la-Neuve.
- [ ] `galactic` — Escanaffles/Bruxelles.

### Petites structures — verifier qu'il y a une page carrieres exploitable

- [ ] `diasource-immunoassays`, `onelife` (Louvain-la-Neuve)
- [ ] `inhatarget-therapeutics`, `biosenic` (Gosselies)
- [ ] `astrivax`, `montis-biosciences`, `midiagnostics`, `replasia`,
      `azalea-vision`, `qaelum`, `nelson-labs-europe` (Leuven)
- [ ] `sgs-lab-simon` (Bierges) — SGS groupe, ATS Workday possible
- [ ] `bausch-lomb-pharma` (Bruxelles) — Workday `bauschhealth`
- [ ] `bristol-myers-squibb` déjà listé plus haut

## Profils (`website` / `careers_url`) — `data/company-web.csv`

`python -m ananas.enrich` pose `website` / `careers_url` depuis ce CSV
(remplit les blancs ; `--force` pour ecraser). Au 2026-09-02 : 34/49 fiches
`curated` ont un `website`. Restent sans site : `diasource-immunoassays`,
`ncardia`, `inhatarget-therapeutics`, `biosenic`, `sgs-lab-simon`, `onelife`,
`astrivax`, `montis-biosciences`, `midiagnostics`, `replasia`, `azalea-vision`,
`qaelum`, `nelson-labs-europe`, `bausch-lomb-pharma`.

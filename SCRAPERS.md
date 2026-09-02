# Scrapers — suivi

Liste de travail pour couvrir le repertoire `curated` (49 biotech/pharma
belges, `data/biotech-belgique.csv`). Voir `README.md` §*Ecrire un scraper*.

Convention : `key` du scraper = `slug` de l'entreprise → liage automatique par
`python -m ananas.seed --link-only`.

## Fait (14)

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
| `pfizer-belgium` | Workday (facette pays) | `pfizer.py` + `workday.py` | 8 |
| `novartis-pharma` | Workday (recherche texte) | `novartis.py` | 16 |
| `bristol-myers-squibb` | Workday (recherche texte) | `bms.py` | 0 (aucun poste belge) |
| `alexion-pharma-belgium` | Workday groupe AstraZeneca | `alexion.py` | 1 |
| `roche-diagnostics` | Phenom People (`location_tokens`) | `roche.py` | 1 |
| `msd-belgium` | Phenom People (`location_tokens`) | `msd.py` | 4 |

## Bases d'ATS reutilisables

| module | ATS | a declarer |
|---|---|---|
| `qbd_group.py::TeamtailorScraper` | Teamtailor RSS | `base_url` |
| `phenom.py::PhenomScraper` | Phenom People (`phApp.ddo`) | `base_url`, `search_params`, `town` |
| `radancy.py::RadancyScraper` | Radancy, liste **SSR** (JSON-LD) | `base_url`, `search_path`, `countries` |
| `attrax.py::AttraxScraper` | Attrax (JSON-LD) | `base_url`, `country` |
| `workday.py::WorkdayScraper` | Workday CXS JSON | `host`, `tenant`, `site`, (`country_facet_wid` ou `search_text`) |

## A faire — priorise par volume / facilite

### Grands groupes, ATS connu (rapide)

- [ ] **`baxter`** — Radancy `jobs.baxter.com` mais liste **rendue en JS** (la
      page SSR n'expose que du contenu, pas les offres). Passer par l'endpoint
      `/en/search-jobs/results?...` (renvoie `{"results": "<html>"}`) — mais il
      faut la bonne `LocationFacet` : `Location=Belgium` seul ne filtre rien.
      Site de Lessines (production) → volume attendu. `RadancyScraper` ne
      couvre aujourd'hui que la liste SSR (Sanofi), pas cet AJAX.
- [ ] **`catalent`** — Workday (tenant `catalent.wd5`, site `External` → 422 en
      l'etat, chercher le bon `site`). Verifier volume BE avant de poser.
- [ ] **`novo-nordisk`** — ATS propre (`www.novonordisk.com/careers`, DNS
      `career.novonordisk.com` inaccessible depuis le conteneur). À explorer :
      souvent une API JSON derriere.
- [ ] **`boehringer-ingelheim`** — `jobs.boehringer-ingelheim.com` =
      **SuccessFactors** (ni `phApp.ddo` ni JSON-LD en SSR). Nouvelle base à
      écrire (`successfactors.py`) — reutilisable pour Terumo.
- [ ] **`biomerieux`** — `careers.biomerieux.com` renvoie 403 au bot (Akamai).
      Tester un autre User-Agent / l'API SmartRecruiters (`biomerieux`).
- [ ] **`terumo-europe`** — HQ Leuven. `careers.terumo-europe.com` =
      **SuccessFactors** (`/go/All-jobs_en/3867101/`). Voir base commune avec
      Boehringer.
- [ ] **`thermo-fisher-scientific-henogen`** — `jobs.thermofisher.com` (bloque
      le bot en HEAD). Site de Gosselies (ex-Henogen). ATS propre — à sonder.
- [ ] **`sgs-lab-simon`** — groupe SGS, `www.sgs.com/en/careers` (Workday
      `sgs` probable). Site de Bierges.
- [ ] **`bausch-lomb-pharma`** — Workday `bauschhealth.wd5` (site `External` →
      422, chercher le bon `site`).

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
(remplit les blancs ; `--force` pour ecraser).

Au 2026-09-02 : **49/49** fiches `curated` ont un `website` ; 14/49 ont un
`careers_url` (celles qui ont un scraper, renseigne automatiquement au liage).
Quelques URL non verifiees a la main (bot bloque) : `onelife`, `azalea-vision`,
`nelson-labs-europe`, `iteos-therapeutics`, `thermo-fisher-scientific-henogen`.

# Scrapers — suivi

Liste de travail pour couvrir le repertoire `curated` (49 biotech/pharma
belges, `data/biotech-belgique.csv`). Voir `README.md` §*Ecrire un scraper*.

Convention : `key` du scraper = `slug` de l'entreprise → liage automatique par
`python -m ananas.seed --link-only`.

## Fait (19)

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
| `catalent` | Phenom People (`location_tokens`) | `catalent.py` | 0 (aucun site belge) |
| `boehringer-ingelheim` | SuccessFactors (vignettes) | `boehringer.py` + `successfactors.py` | 2 |
| `terumo-europe` | SuccessFactors (tableau) | `terumo.py` + `successfactors.py` | 14 |
| `thermo-fisher-scientific-henogen` | Phenom People (`location_tokens` Gosselies/Seneffe) | `thermofisher.py` | 3 |
| `nelson-labs-europe` | Workday groupe Sotera Health | `nelson_labs.py` | 1 |

## Bases d'ATS reutilisables

| module | ATS | a declarer |
|---|---|---|
| `qbd_group.py::TeamtailorScraper` | Teamtailor RSS | `base_url` |
| `phenom.py::PhenomScraper` | Phenom People (`phApp.ddo`) | `base_url`, `search_params`, `town` |
| `radancy.py::RadancyScraper` | Radancy, liste **SSR** (JSON-LD) | `base_url`, `search_path`, `countries` |
| `attrax.py::AttraxScraper` | Attrax (JSON-LD) | `base_url`, `country` |
| `workday.py::WorkdayScraper` | Workday CXS JSON | `host`, `tenant`, `site`, (`country_facet_wid` ou `search_text`) |
| `successfactors.py::SuccessFactorsScraper` | SAP SuccessFactors (liste SSR, 2 themes) | `base_url` |

## A faire — priorise par volume / facilite

### Grands groupes, ATS connu (rapide)

- [ ] **`baxter`** — Radancy `jobs.baxter.com` mais liste **rendue en JS** (la
      page SSR n'expose que du contenu, pas les offres). Passer par l'endpoint
      `/en/search-jobs/results?...` (renvoie `{"results": "<html>"}`) — mais il
      faut la bonne `LocationFacet` : `Location=Belgium` seul ne filtre rien.
      Site de Lessines (production) → volume attendu. `RadancyScraper` ne
      couvre aujourd'hui que la liste SSR (Sanofi), pas cet AJAX.
- [x] ~~**`catalent`**~~ — Phenom People (`careers.catalent.com`, `us/en`).
      Aucun site belge : `qcountry=Belgium` = 0 poste. Scraper pose (comme BMS).
- [ ] **`novo-nordisk`** — ATS propre (`www.novonordisk.com/careers`, DNS
      `career.novonordisk.com` inaccessible depuis le conteneur). À explorer :
      souvent une API JSON derriere.
- [x] ~~**`boehringer-ingelheim`**~~ — SuccessFactors (`successfactors.py`).
- [x] ~~**`terumo-europe`**~~ — SuccessFactors, meme base.
- [ ] **`biomerieux`** — `careers.biomerieux.com` renvoie 403 au bot (Akamai).
      Tester un autre User-Agent / l'API SmartRecruiters (`biomerieux`).
- [x] ~~**`thermo-fisher-scientific-henogen`**~~ — Phenom (`jobs.thermofisher.com`),
      filtre `location_tokens` Gosselies/Seneffe (43 postes BE groupe → 3 locaux).
- [ ] **`sgs-lab-simon`** — groupe SGS. Workday `sgs.wd3` repond 401 (compte
      systeme). `careers.sgs.com` inaccessible depuis le conteneur. À reprendre
      hors conteneur. Site de Bierges.
- [ ] **`bausch-lomb-pharma`** — SuccessFactors mais **ancien servlet**
      (`career2.successfactors.eu/career?company=Bausch`, aussi
      `careers.bauschlomb.com/search` qui renvoie 0). Pas le theme SSR gere par
      `successfactors.py`. À reprendre.

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
      `azalea-vision`, `qaelum` (Leuven)
- [x] ~~`nelson-labs-europe`~~ (Leuven) — Workday groupe Sotera Health.
- [ ] `sgs-lab-simon` (Bierges) — SGS groupe, ATS Workday possible
- [ ] `bausch-lomb-pharma` (Bruxelles) — Workday `bauschhealth`
- [ ] `bristol-myers-squibb` déjà listé plus haut

## Profils (`website` / `careers_url`) — `data/company-web.csv`

`python -m ananas.enrich` pose `website` / `careers_url` depuis ce CSV
(remplit les blancs ; `--force` pour ecraser).

Au 2026-09-02 : **49/49** fiches `curated` ont un `website` ; 19/49 ont un
`careers_url` (celles qui ont un scraper, renseigne automatiquement au liage).
Quelques URL non verifiees a la main (bot bloque) : `onelife`, `azalea-vision`,
`iteos-therapeutics`.

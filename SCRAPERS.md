# Scrapers — suivi

Liste de travail pour couvrir le repertoire `curated` (49 biotech/pharma
belges, `data/biotech-belgique.csv`). Voir `README.md` §*Ecrire un scraper*.

Les 137 membres et partenaires du BioPark de Charleroi (`data/biopark.csv`)
ont leur propre liste de suivi: `BIOPARK.md`.

Convention : `key` du scraper = `slug` de l'entreprise → liage automatique par
`python -m ananas.seed --link-only`.

## Fait (29)

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
| `prothya-biosolutions` | Site propre WP (pages departement) | `prothya.py` | 15 |
| `galactic` | TalentFinder (JSON-LD) | `galactic.py` | 1 |
| `novadip-biosciences` | Site propre WP | `novadip.py` | 1 |
| `cellistic` | Site propre (`/careers/<slug>`) | `cellistic.py` + `ncardia.py` | 2 |
| `ncardia` | Site propre (`/careers/<slug>`, filtre pays) | `ncardia.py` | 0 (1 poste a Leiden NL) |
| `quantoom-biosciences` | Site propre WP | `quantoom.py` | 1 |
| `univercells-technologies` | Workday groupe Donaldson (`location_tokens` Nivelles) | `univercells.py` | 2 |
| `sobi-swedish-orphan-biovitrum` | SmartRecruiters (API, filtre pays) | `sobi.py` + `smartrecruiters.py` | 0 (0 poste belge) |
| `baxter` | Workday (`baxter.wd1`) | `baxter.py` | 0 (aucun poste belge publie) |
| `qaelum` | Section carrieres Joomla (flux RSS) | `qaelum.py` | 1 |

## Bases d'ATS reutilisables

| module | ATS | a declarer |
|---|---|---|
| `qbd_group.py::TeamtailorScraper` | Teamtailor RSS | `base_url` |
| `phenom.py::PhenomScraper` | Phenom People (`phApp.ddo`) | `base_url`, `search_params`, `town` |
| `radancy.py::RadancyScraper` | Radancy, liste **SSR** (JSON-LD) | `base_url`, `search_path`, `countries` |
| `attrax.py::AttraxScraper` | Attrax (JSON-LD) | `base_url`, `country` |
| `workday.py::WorkdayScraper` | Workday CXS JSON | `host`, `tenant`, `site`, (`country_facet_wid` ou `search_text`) |
| `successfactors.py::SuccessFactorsScraper` | SAP SuccessFactors (liste SSR, 2 themes) | `base_url` |
| `smartrecruiters.py::SmartRecruitersScraper` | SmartRecruiters (API publique) | `company`, `country` |
| `ncardia.py::SlugCareersScraper` | Site "constructeur" a liens `/careers/<slug>` | `base_url`, `location_tokens` |

## A faire — priorise par volume / facilite

### Grands groupes, ATS connu (rapide)

- [x] ~~**`baxter`**~~ — le portail `jobs.baxter.com` (Radancy en vitrine) est
      alimente par le Workday `baxter.wd1` / site `baxter`. Au 2026-09-02 : la
      facette pays ne liste **aucune** valeur "Belgium", `searchText=Belgium`
      = 0. Baxter ne publie pas Lessines/Braine-l'Alleud en ligne. Scraper
      Workday pose (comme BMS) — remontera les offres des qu'il y en aura.
- [x] ~~**`catalent`**~~ — Phenom People (`careers.catalent.com`, `us/en`).
      Aucun site belge : `qcountry=Belgium` = 0 poste. Scraper pose (comme BMS).
- [ ] **`novo-nordisk`** — `careers.novonordisk.com` = SuccessFactors RMK
      (jobs2web / `j2w`). L'endpoint `tile-search-results/?q=&startrow=0` rend
      des `li.job-tile` (100/page) **mais n'accepte aucun filtre de lieu**
      (tout parametre supplementaire → reponse vide) et les vignettes ne
      portent ni lieu ni total. Il faudrait crawler tout le catalogue mondial
      puis ouvrir chaque fiche pour filtrer — trop lourd/fragile. À reprendre
      si Novo expose un site belge ou une API JSON.
- [x] ~~**`boehringer-ingelheim`**~~ — SuccessFactors (`successfactors.py`).
- [x] ~~**`terumo-europe`**~~ — SuccessFactors, meme base.
- [ ] **`biomerieux`** — `careers.biomerieux.com` renvoie 403 au bot (Akamai).
      SmartRecruiters mais l'identifiant `biomerieux` ne renvoie rien via l'API
      publique (l'entreprise a un id SR different / prive). À retrouver.
- [x] ~~**`sobi-swedish-orphan-biovitrum`**~~ — SmartRecruiters (`Sobi`), API
      publique, filtre `country=be` (0 poste belge au 2026-09-02).
- [x] ~~**`thermo-fisher-scientific-henogen`**~~ — Phenom (`jobs.thermofisher.com`),
      filtre `location_tokens` Gosselies/Seneffe (43 postes BE groupe → 3 locaux).
- [ ] **`sgs-lab-simon`** — groupe SGS. Workday `sgs.wd3` repond 401 (compte
      systeme). `careers.sgs.com` inaccessible depuis le conteneur. À reprendre
      hors conteneur. Site de Bierges.
- [ ] **`bausch-lomb-pharma`** — SuccessFactors mais **ancien servlet**
      (`career2.successfactors.eu/career?company=Bausch`, aussi
      `careers.bauschlomb.com/search` qui renvoie 0). Pas le theme SSR gere par
      `successfactors.py`. À reprendre.

### Biotechs moyennes

Note : depuis le conteneur, plusieurs sites sont injoignables (DNS/pare-feu
egress) — `iteostherapeutics.com`, `univercells-technologies.com`,
`exothera.bio`, `cellistic.com`, `iba-worldwide.com`, `precirix.com`,
`careers.biomerieux.com` (403 Akamai). À reprendre hors conteneur.

- [x] ~~`prothya-biosolutions`~~ — Bruxelles. Site propre WP
      (`careers-be.prothya.com`), parcours des pages departement → 15 offres.
- [x] ~~`galactic`~~ — Bruxelles. ATS TalentFinder, fiches en JSON-LD → 1 offre.
- [x] ~~`novadip-biosciences`~~ — Mont-Saint-Guibert. Site propre WP → 1 offre.
- [x] ~~`ncardia`~~ / ~~`cellistic`~~ — meme gabarit de site (`SlugCareersScraper`).
      Ncardia 0 en BE (1 a Leiden), Cellistic 2.
- [x] ~~`quantoom-biosciences`~~ — site WP `/job-application/` → 1 offre.
- [ ] `celyad-oncology` — 0 poste annoncé, candidature par email. Basse prio.
- [ ] `montis-biosciences` — Leuven. Site propre, aucune offre affichee. Basse prio.
- [ ] `realco` — Louvain-la-Neuve. Site propre. Au 2026-09-02 : 1 poste
      (Allemagne, remote) — 0 local. Basse prio.
- [ ] `kantify` — Bruxelles. Aucune offre listee (page "rejoignez-nous" sans
      postes). Basse prio.
- [x] ~~`qaelum`~~ — Leuven. Section carrieres Joomla avec flux RSS → 1 offre.
- [ ] `icometrix` — Leuven. Site Wix, aucune page carrieres publique ;
      rachat par GE HealthCare annonce. Basse prio.
- [ ] `astrivax` — Leuven. `astrivax.com/vacancies/` : aucune offre ouverte
      (candidature spontanee seulement). Basse prio.
- [x] ~~`univercells-technologies`~~ — rachetee par Donaldson, offres sur le
      Workday `donaldson.wd115`, filtre `location_tokens` Nivelles → 2 offres.
- [ ] `iteos-therapeutics` / `exothera` / `iba` / `precirix` — injoignables
      depuis le conteneur (voir note ci-dessus ; `data/company-web.csv` a
      `exothera.com` corrige — a retester hors conteneur).
- [ ] `diasource-immunoassays` — LLN. Candidature par email, aucune offre
      listee. Basse prio.

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

Au 2026-09-02 : **49/49** fiches `curated` ont un `website` ; 30/49 ont un
`careers_url` (celles qui ont un scraper, renseigne automatiquement au liage).
Quelques URL non verifiees a la main (bot bloque) : `onelife`, `azalea-vision`,
`iteos-therapeutics`.

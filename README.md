# Ananas — API, worker et scrapers

Backend FastAPI, worker de scraping quotidien et registre de scrapers du SaaS
**Ananas** (veille emploi geolocalisee). Le front vit dans un depot separe
(`../web`) et ne communique avec ce service que par HTTP.

Un seul projet Python, deux entrypoints — les modeles, la config et la
connexion base ne sont ecrits qu'une fois :

| entrypoint | commande |
|---|---|
| API HTTP | `uvicorn ananas.api.main:app` |
| worker planifie | `python -m ananas.worker.main` |

## Demarrage

Le chemin normal est le `docker-compose.yml` du dossier parent, qui lance
`db + backend + worker + web` ensemble. Voir `../README.md`.

En autonome (base Postgres deja disponible) :

```bash
pip install -e .
export DATABASE_URL="postgresql+psycopg://ananas:ananas@localhost:5432/ananas"
alembic upgrade head
python -m ananas.seed            # importe les 130 entreprises des CSV de data/
uvicorn ananas.api.main:app --reload
```

## Ce qu'il y a dedans

```
ananas/
├── models.py        7 tables SQLAlchemy
├── security.py      argon2 + JWT en cookie httpOnly
├── seed.py          import des CSV + auto-liage des scrapers
├── geocode_csv.py   remplit lat/lon d'un CSV, une fois pour toutes
├── admin.py         cree le compte d'administration (hors HTTP)
├── api/             routes FastAPI
├── scrapers/        BaseScraper, registre, exemple QbD Group
├── notifiers/       BaseNotifier, registre, Telegram
└── worker/          planification, scrape, notification
```

### Trois provenances, un seul vocabulaire de tags

`companies.source` vaut `biowin` (les 81 partenaires du POC, `data/partners.csv`),
`curated` (les 49 biotech/pharma belges de `data/biotech-belgique.csv`) ou
`from_user` (proposees via `POST /api/companies`). Une entreprise proposee est
une entreprise a part entiere: visible, filtrable et enregistrable par tous.

Ajouter un lot d'entreprises = deposer un CSV dans `data/`, le geocoder une
fois, l'ajouter a `DEFAULT_CSVS` (seed.py):

```bash
python -m ananas.geocode_csv data/mon-lot.csv   # ~1 s par ligne, Nominatim
python -m ananas.seed
```

Le CSV n'a besoin que de `name`; `source` vaut `biowin` s'il est absent. Les
lignes sans `url` (fiche BioWin d'origine) sont reconciliees sur le couple
`(source, slug)`, donc relancer le seed ne cree pas de doublon.

Les secteurs BioWin vivent dans `core_business`, les tags utilisateur dans
`tags`. Le filtre et la liste de facettes interrogent **les deux colonnes**:
cote interface il n'y a qu'un seul vocabulaire, donc un seul filtre.

Deux garde-fous rendent ce vocabulaire exploitable, sans lesquels les tags ne
servent a rien:

- `normalize_tag` (schemas.py) uniformise casse et espaces, en preservant les
  sigles courts (IVD, CRO).
- `_canonical_tags` (api/companies.py) rattache un tag a l'orthographe **deja
  presente** dans le repertoire quand elle existe a la casse pres. Sans lui,
  "Administrative & Office support" et "... Support" cohabiteraient dans le
  filtre.

### Qui peut modifier une fiche

Une seule fonction, `may_edit` (api/companies.py), et une seule route
(`PATCH /api/companies/{id}`) pour l'administration comme pour l'utilisateur
qui corrige sa propre proposition. Deux routes auraient fini par diverger, et
c'est la plus permissive qui aurait fait foi ; `tests/test_permissions.py`
verrouille la regle.

```
administration    -> toutes les fiches
auteur d'une fiche -> la sienne (companies.submitted_by_user_id)
tout le monde      -> rien
```

`CompanyDetail.can_edit` transporte le verdict jusqu'a l'interface : le front
n'a aucune regle a reimplementer, il affiche ou non un bouton.

Deux details qui comptent :

- **Le slug ne suit pas le nom.** C'est une identite : URL partagee, et cle
  d'auto-liage d'un scraper dans `seed.py`. Renommer ne doit rien casser.
- **L'adresse n'est re-geocodee que si elle change.** Sans cette condition,
  corriger un telephone sur une fiche BioWin lui ferait perdre sa precision
  `adresse` heritee du POC pour la repasser au geocodeur.

### Le compte d'administration

`is_admin` ne s'accorde par aucune route — `ananas/admin.py` est une commande :

```bash
python -m ananas.admin              # lit ADMIN_EMAIL / ADMIN_PASSWORD du .env
python -m ananas.admin --email a@b.c --password '...'
python -m ananas.admin --revoke a@b.c
```

Elle est idempotente : le compte est cree s'il n'existe pas, promu s'il existe,
et son mot de passe reecrit a chaque passage — changer le mot de passe admin,
c'est editer le `.env` et relancer. Une elevation de privilege demande donc un
acces au serveur, pas une faille dans le formulaire d'inscription.

`api/admin.py` (`GET /api/admin/users`, `/stats`) est en **lecture seule et
sans contenu** : compteurs d'usage, jamais le CV, les aspirations ou le
`chat_id` Telegram d'un compte. Ces donnees ne servent pas a moderer un
repertoire, et les exposer ferait de la page admin une cible.

### Les deux garanties du schema

- `jobs` porte une contrainte unique `(company_id, fingerprint)`. C'est elle
  qui definit "la meme offre", et donc par difference ce qu'est une offre
  *nouvelle*.
- `sent_job_notifications` a pour cle primaire `(user_id, job_id)`. Une offre
  ne peut structurellement pas etre notifiee deux fois au meme utilisateur,
  meme si le worker est relance a la main ou plante en plein envoi.

## Ecrire un scraper

Une seule methode a implementer. Depose un fichier dans `ananas/scrapers/` :

```python
from ananas.scrapers.base import BaseScraper, JobPosting
from ananas.scrapers.registry import register
from ananas.scrapers.http import txt


@register
class AcmeScraper(BaseScraper):
    key = "acme-biotech"                       # = le slug de l'entreprise
    label = "Acme Biotech"
    careers_url = "https://acme.com/careers"

    def fetch(self) -> list[JobPosting]:
        soup = self.get_soup(self.careers_url)
        return [
            JobPosting(title=txt(a), url=self.absolutize(a["href"]))
            for a in soup.select("a.job-link")
        ]
```

Puis branche-le sur l'entreprise :

```bash
python -m ananas.seed --link-only     # relie tout scraper dont key == slug
python -m ananas.worker.main --list-scrapers
python -m ananas.worker.main --scrape-only --company acme-biotech
```

Si la cle ne peut pas egaler le slug, renseigne `companies.scraper_key` a la main.

**Reflexes utiles**

- Cherche un flux structure avant de parser du HTML : RSS, ou l'API publique de
  l'ATS (Greenhouse, Lever, Recruitee, Teamtailor, Workable, SmartRecruiters en
  ont tous une). Ça survit aux refontes graphiques.
- Renseigne `external_id` des que le site expose un identifiant : il survit a un
  changement d'URL ou de titre, contrairement au fingerprint calcule.
- `run()` (herite) s'occupe du chronometrage, de la capture d'erreur, de la
  deduplication et du rejet des offres incompletes. Ne le surcharge pas.
- Une exception levee dans `fetch()` marque l'entreprise en erreur et laisse le
  reste du run continuer. Surtout, aucune offre n'est fermee ce jour-la.

Trois familles d'ATS sont deja factorisees, chacune reutilisable pour une autre
entreprise en quelques lignes :

| module | ATS | entreprises | ce qu'il faut declarer |
|---|---|---|---|
| `qbd_group.py` | Teamtailor (flux RSS) | QbD Group | `base_url` |
| `phenom.py` + `gsk.py` | Phenom People (`phApp.ddo`) | GSK Wavre, GSK Rixensart | `base_url`, `search_location`, `town` |
| `attrax.py` + `abbvie.py` | Attrax (JSON-LD `JobPosting`) | AbbVie Belgium | `base_url`, `country` |

**Piege Phenom, non evident.** La recherche par lieu de ces sites est une
recherche de *proximite*, pas un filtre : interroger « Rixensart » renvoie une
cinquantaine de postes dont plusieurs a Londres ou Collegeville. D'ou
l'attribut `town` et le filtrage sur `multi_location` — et non sur `city`, car
un poste ouvert a la fois a Londres et a Rixensart porte `city = London` tout
en concernant bien le site local.

Ces sites sont rendus en JavaScript, mais le serveur embarque l'etat initial
dans `phApp.ddo` : aucun navigateur headless n'est necessaire.

**Attrax, plus simple : pas de piege de proximite.** Le filtre `li=<code
pays>` est un filtre exact — un poste liste pour `li=BE` est bien en Belgique,
aucun post-filtrage requis. La liste ne rend que des vignettes (titre, lieu) ;
la fiche embarque un bloc `<script type="application/ld+json">` au format
schema.org `JobPosting` avec titre, lieu, description complete, date de
publication et un identifiant stable — un vocabulaire fixe par la
specification, plus robuste que des classes CSS maison qui changent a chaque
refonte du theme.

## Correspondance offre / profil

Deux etapes deliberement separees, dans `ananas/ai/` :

1. **Extraction** (`extraction.py`) — la seule qui appelle un modele. Une offre
   est structuree **une fois pour tous les utilisateurs** (`job_features`) ; un
   profil l'est a chaque enregistrement du CV (`user_profiles`). Les deux
   produisent le *meme vocabulaire* : memes echelles de seniorite, memes listes
   de competences en minuscules.
2. **Comparaison** (`matching.py`) — **aucun appel au modele**. Du Python
   deterministe qui pondere competences, famille de metier, seniorite, secteur,
   langues, lieu et teletravail, et retourne un score 0-100 avec ses raisons.

Ce decoupage n'est pas une economie de moyens :

- **cout** — comparer par LLM couterait N_utilisateurs x N_offres appels, a
  refaire des qu'un profil change. Ici c'est gratuit, donc toutes les paires
  sont materialisees dans `job_matches` et « les offres pertinentes de cette
  entreprise » devient un `WHERE score >= seuil` ;
- **explicabilite** — l'interface affiche *pourquoi* une offre matche ;
- **stabilite** — deux executions donnent le meme score ;
- **portabilite** — passer a un modele local ne touche que `ananas/ai/`.

### Import d'un CV en PDF

`ananas/cv_import.py`. Deux chemins, dans cet ordre :

1. **Extraction locale** (pypdf) — gratuite, instantanee, independante du
   fournisseur. C'est le cas de la plupart des CV, exportes depuis un
   traitement de texte. Le texte est recolle (cesures, retours au milieu des
   phrases) : sans ça le modele lit des mots coupes.
2. **Repli sur le modele** pour les PDF *scannes*, qui n'ont aucune couche
   texte. C'est une capacite **optionnelle** de `BaseLLM.read_document` : un
   fournisseur qui ne la gere pas leve `NotImplementedError` et l'utilisateur
   recoit une consigne claire, plutot qu'un profil vide.

Le texte extrait n'est jamais analyse directement : il remplit le champ CV, que
l'utilisateur relit avant de lancer l'analyse. Une extraction PDF melange
souvent les colonnes, et un profil faux produirait des scores faux sans que
rien ne le signale.

### Changer de fournisseur

`ananas/ai/base.py` ne demande qu'une capacite obligatoire :
`complete_json(system, prompt, schema)`. Ajouter un modele local = une
sous-classe de `BaseLLM` decoree `@register` dans `ananas/ai/`, puis
`AI_PROVIDER=<cle>` dans le `.env`. Le scoring, les modeles de donnees, le
worker et l'interface ne bougent pas — sauf le mode lot ci-dessous, qui est
optionnel.

### Extraction des offres, en direct ou par lot

Deux vitesses pour la meme extraction, choisies par l'appelant
(`ananas/ai/service.py`) :

- **En direct** (`extract_missing_features`) — un appel modele par offre,
  reponse immediate. Utilise par les commandes interactives
  (`--extract-only`, `--now`, et le flux habituel d'ajout d'un scraper :
  `--scrape-only` puis verification) : une reponse tout de suite compte plus
  que le cout quand quelqu'un attend a l'ecran, y compris quand un tout
  nouveau scraper ramene d'un coup son historique complet.
- **Par lot** (`submit_extraction_batch` / `collect_extraction_batches`) —
  toutes les offres manquantes en une seule requete `batchGenerateContent`
  chez Gemini, a moitie prix, mais sans delai garanti (cible officielle 24h,
  en pratique souvent bien plus rapide). Reserve au cycle automatique du
  worker, personne n'y attend a l'ecran.

C'est une capacite **optionnelle** de `BaseLLM`
(`supports_batch`/`submit_batch`/`poll_batch`, meme principe que
`read_document`) : un fournisseur qui ne la propose pas continue de
fonctionner, le worker retombe alors sur l'extraction en direct.

**Le cycle automatique tient sur deux passes planifiees, pas une** (voir
`ananas/worker/main.py`) :

| heure par defaut | passe | fait quoi |
|---|---|---|
| minuit (`SCRAPE_CRON_HOUR/MINUTE`) | `midnight_job` | scrape, puis soumet un lot pour tout ce qui manque de caracteristiques |
| 7h (`NOTIFY_CRON_HOUR/MINUTE`) | `morning_job` | recolte le lot — tel quel s'il n'est pas fini — puis notifie |

Toute la nuit separe les deux, pour laisser sa chance au lot. `morning_job`
**ne l'attend pas** : un lot pas termine a 7h laisse ses offres sans
caracteristiques, elles restent visibles dans la notification (simplement non
triees, en fin de liste) plutot que de retarder tout le monde — et repartent
d'elles-memes dans le lot de la nuit suivante, puisqu'elles restent sans
`job_features`. `ExtractionBatch.job_ids` retient quelles offres sont deja
"en vol" pour ne pas les soumettre deux fois pendant qu'on attend.

```bash
python -m ananas.worker.main --batch-status    # ou en sont les lots, et combien d'offres attendent
python -m ananas.worker.main --batch-collect   # recolte les lots termines, maintenant
python -m ananas.worker.main --batch-submit    # soumet un lot pour les offres restantes
python -m ananas.worker.main --extract-only    # extraction en direct (1 appel par offre), hors cron
```

**Un lot qui n'aboutit jamais.** `ExtractionBatch.job_ids` excluant ses offres
de toute nouvelle soumission, un lot bloque en `pending` gele definitivement
les offres qu'il transporte. Deux protections :

- `poll_batch` accepte les deux formes de reponse de l'API. `GET
  /v1beta/batches/{id}` renvoie un `longrunning.Operation` qui range l'etat
  dans `metadata.state` avec le vocabulaire `BATCH_STATE_*`, alors que le SDK
  expose un objet plat (`state`, `dest.inlinedResponses`) en `JOB_STATE_*`.
  Ne lire que la seconde forme faisait valoir "pas encore fini" a un etat
  simplement introuvable — *le* bug qui laissait les lots tourner sans fin.
- `BATCH_MAX_AGE_HOURS` (48h, la duree de vie annoncee d'un lot Gemini) :
  au-dela, le lot est declare perdu et ses offres repartent dans le suivant.
  C'est le filet quand la forme de la reponse change encore.

**Declencheurs de recalcul du score**, inchanges par le mode lot :

- une offre gagne des caracteristiques (en direct ou par lot) -> scoree pour
  tous les profils prets ;
- un profil est (re)extrait -> toutes les offres sont rescorees pour lui.

## Liaison Telegram

`ananas/telegram_link.py`. Le token du bot est un secret serveur partage par
tous les comptes : il ne doit jamais etre communique a un utilisateur, ce qui
exclut de lui faire ouvrir `getUpdates` lui-meme. Et un bot Telegram ne peut
pas ecrire a quelqu'un qui ne lui a jamais parle : l'initiative doit venir de
l'utilisateur.

D'ou le protocole : le serveur tire un code a usage unique et construit
`https://t.me/<bot>?start=<code>` ; l'utilisateur appuie sur « Demarrer » ;
le serveur retrouve le code dans `getUpdates` et enregistre le `chat.id`.

Deux pieges, tous deux couverts par `tests/test_telegram_link.py` :

- **`getUpdates` est exclusif et destructif.** Chaque appel avec un `offset`
  confirme definitivement le lot precedent, que Telegram ne rejouera plus. Deux
  requetes concurrentes se voleraient leurs messages : d'ou le verrou, et le
  fait que chaque vidange confronte les mises a jour a *tous* les codes en
  attente, pas seulement a celui de l'appelant.
- **L'offset doit survivre a un redemarrage**, sinon on retraite ou on perd des
  liaisons. Il est persiste dans la table `app_state`.

## Ajouter un canal de notification

Meme principe dans `ananas/notifiers/` : sous-classe `BaseNotifier`, decore avec
`@register`, implemente `send`, `send_test` et `validate_target`. Le worker
resout le transport depuis `notification_channels.type`, il n'a pas a etre modifie.

### Entreprises suivies sans scraper

Une notification envoyee ajoute un pied de page listant les entreprises
suivies dont aucune offre n'a pu etre relevee automatiquement —
`scraper_key` vide, ou renseignee mais absente du registre (module retire ou
en erreur au chargement). Sans lui, un silence sur cette entreprise se
confondrait avec "rien de nouveau" ; le pied de page invite a aller regarder
sa page carrieres a la main.

`ananas/worker/notify.py:unscraped_saved_companies` calcule la liste,
`Digest.unscraped_companies` la transporte jusqu'au notifier. Ce n'est jamais
un message a lui seul : la regle "rien de nouveau, aucun message" s'applique
toujours a l'ensemble du digest.

## CLI du worker

```bash
python -m ananas.worker.main                        # daemon, deux passes planifiees (minuit + 7h)
python -m ananas.worker.main --now                  # scrape + extraction en direct + notifie, tout de suite
python -m ananas.worker.main --scrape-only --company qbd-group
python -m ananas.worker.main --notify-only
python -m ananas.worker.main --list-scrapers
```

`--now` et les autres flags restent entierement synchrones (voir "Extraction
des offres, en direct ou par lot" plus haut) : ils ne passent jamais par le
mode lot, pour une reponse immediate.

## Tests

```bash
pip install -e ".[dev]"
pytest
```

Les tests couvrent le fingerprint, qui decide de ce qui est une nouvelle offre :
s'il est instable l'utilisateur recoit tous les jours la meme offre, s'il
collisionne il en rate.

## Geocodage

`ananas/geocoding.py` est porte du POC, ou la cascade avait ete mise au point
contre les 81 adresses reelles de BioWin. Elle degrade au lieu d'echouer:

    rue complete -> rue nettoyee -> ville -> code postal -> nom de la commune

et retourne **comment** le point a ete place (`adresse`, `ville`,
`approx. (nom)`, `non localise`), pour que l'interface le signale. Appelee a la
soumission d'une entreprise (~1 s, limite de debit Nominatim oblige), avec un
cache process-local qui retient aussi les echecs.

Le seed, lui, ne geocode **jamais**: il lit des coordonnees deja presentes dans
le CSV. Sinon chaque demarrage repaierait la seconde par ligne. Le prix est
paye une fois par `python -m ananas.geocode_csv <fichier>`, qui ne reprend que
les lignes sans coordonnees et versionne le resultat avec le CSV.

## Migrations

```bash
alembic revision --autogenerate -m "description"
alembic upgrade head
```

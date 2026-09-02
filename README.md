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
python -m ananas.seed            # importe les 81 entreprises de data/partners.csv
uvicorn ananas.api.main:app --reload
```

## Ce qu'il y a dedans

```
ananas/
├── models.py        7 tables SQLAlchemy
├── security.py      argon2 + JWT en cookie httpOnly
├── seed.py          import CSV + auto-liage des scrapers
├── api/             routes FastAPI
├── scrapers/        BaseScraper, registre, exemple QbD Group
├── notifiers/       BaseNotifier, registre, Telegram
└── worker/          planification, scrape, notification
```

### Deux provenances, un seul vocabulaire de tags

`companies.source` vaut `biowin` (les 81 importees du CSV) ou `from_user`
(proposees via `POST /api/companies`). Une entreprise proposee est une
entreprise a part entiere: visible, filtrable et enregistrable par tous.

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

`ananas/scrapers/qbd_group.py` est un exemple complet et commente, qui factorise
la logique par ATS (`TeamtailorScraper`) plutot que par entreprise.

## Ajouter un canal de notification

Meme principe dans `ananas/notifiers/` : sous-classe `BaseNotifier`, decore avec
`@register`, implemente `send`, `send_test` et `validate_target`. Le worker
resout le transport depuis `notification_channels.type`, il n'a pas a etre modifie.

## CLI du worker

```bash
python -m ananas.worker.main                        # daemon, passe quotidienne
python -m ananas.worker.main --now                  # scrape + notifie maintenant
python -m ananas.worker.main --scrape-only --company qbd-group
python -m ananas.worker.main --notify-only
python -m ananas.worker.main --list-scrapers
```

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

## Migrations

```bash
alembic revision --autogenerate -m "description"
alembic upgrade head
```

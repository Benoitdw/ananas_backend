# Commandes utiles (dans le docker)

Recettes verifiees pour les operations qui n'ont pas d'interface : promouvoir un
compte, sortir des donnees d'un utilisateur, faire evoluer le schema.

Toutes les commandes se lancent **depuis le dossier parent** (`../`), la ou vit
le `docker-compose.yml` — pas depuis `api/`. Deux points d'entree :

| service | ce qu'on y lance |
|---|---|
| `backend` | tout ce qui est Python : `python -m ananas.*`, `alembic` (le `WORKDIR` est `/app`) |
| `db` | tout ce qui est SQL : `psql` |

```bash
docker compose exec backend <commande python|alembic>
docker compose exec db psql -U ananas -d ananas
```

Le `-T` ajoute ci-dessous desactive le pseudo-TTY : indispensable quand la
commande recoit un heredoc ou que sa sortie est redirigee vers un fichier,
inutile en interactif.

---

## Mettre une adresse mail en admin

`is_admin` ne peut etre leve par **aucune route HTTP** — c'est delibere (voir
`ananas/admin.py`). Une elevation de privilege demande donc un acces au
serveur.

### Le cas normal : le compte du `.env`

Idempotent : cree le compte s'il n'existe pas, le promeut s'il existe.

```bash
docker compose exec backend python -m ananas.admin
# -> admin@ananas.com cree — administrateur
```

Il lit `ADMIN_EMAIL` / `ADMIN_PASSWORD` du `.env`. Pour changer le mot de passe
admin : editer le `.env`, `docker compose up -d backend`, relancer la commande.

### Un compte precis

```bash
docker compose exec backend python -m ananas.admin \
  --email benoit@mlmlml.com --password 'un-mot-de-passe-de-8-caracteres-mini'
```

> **Attention** — cette commande **reecrit le mot de passe** du compte a chaque
> passage. Sur un compte existant qui a deja son mot de passe, elle le change.
> Pour seulement promouvoir sans y toucher, voir juste en dessous.

### Promouvoir sans toucher au mot de passe

```bash
docker compose exec -T backend python -c "
from sqlalchemy import select
from ananas.db import session_scope
from ananas.models import User
from ananas.security import normalize_email

EMAIL = 'benoit@mlmlml.com'

with session_scope() as db:
    u = db.scalar(select(User).where(User.email == normalize_email(EMAIL)))
    if u is None:
        raise SystemExit(f'Aucun compte pour {EMAIL}')
    u.is_admin = True
    u.is_active = True
    print(f'{u.email} est maintenant administrateur')
"
```

`normalize_email` est important : les mails sont toujours stockes en
minuscules. Un `WHERE email = 'Admin@ananas.com'` en SQL brut ne trouverait
rien.

### Retirer le droit

```bash
docker compose exec backend python -m ananas.admin --revoke benoit@mlmlml.com
```

### Verifier

```bash
docker compose exec db psql -U ananas -d ananas \
  -c "SELECT id, email, is_admin, is_active FROM users ORDER BY id;"
```

```
 id |       email       | is_admin | is_active
----+-------------------+----------+-----------
  2 | benoit@mlmlml.com | f        | t
 29 | admin@ananas.com  | t        | t
```

---

## Extraire la liste des entreprises suivies d'un utilisateur

« Suivie » = une ligne dans `saved_companies` — c'est ce qui declenche la veille
sur cette entreprise.

### En SQL, lisible

```bash
docker compose exec db psql -U ananas -d ananas -c "
SELECT c.id, c.name, c.city, c.scraper_key, s.saved_at
FROM saved_companies s
JOIN companies c ON c.id = s.company_id
JOIN users u     ON u.id = s.user_id
WHERE u.email = 'benoit@mlmlml.com'
ORDER BY s.saved_at DESC;"
```

```
 id |   name    |      city      | scraper_key |           saved_at
----+-----------+----------------+-------------+-------------------------------
 86 | OncoDNA   | 6041 Gosselies |             | 2026-09-02 09:52:46.609264+00
 61 | QbD Group | 6041 Gosselies | qbd-group   | 2026-09-02 09:38:24.34667+00
```

`scraper_key` vide = entreprise suivie mais **pas encore scrapee** : elle ne
generera aucune notification. C'est la colonne a regarder quand un utilisateur
dit ne rien recevoir.

### En CSV, pour l'exporter

```bash
docker compose exec -T db psql -U ananas -d ananas -c "\copy (
  SELECT c.name, c.city, c.website, c.careers_url, c.scraper_key, s.saved_at
  FROM saved_companies s
  JOIN companies c ON c.id = s.company_id
  JOIN users u     ON u.id = s.user_id
  WHERE u.email = 'benoit@mlmlml.com'
  ORDER BY c.name
) TO STDOUT WITH CSV HEADER" > suivies.csv
```

`\copy` (client) et non `COPY` (serveur) : le fichier atterrit sur **l'hote**,
pas dans le conteneur.

### En Python, avec les modeles

Utile pour enchainer sur autre chose (offres, scores, envoi).

```bash
docker compose exec -T backend python - <<'PY'
from sqlalchemy import select
from ananas.db import session_scope
from ananas.models import User, Company, SavedCompany
from ananas.security import normalize_email

EMAIL = "benoit@mlmlml.com"

with session_scope() as db:
    user = db.scalar(select(User).where(User.email == normalize_email(EMAIL)))
    if user is None:
        raise SystemExit(f"Aucun compte pour {EMAIL}")

    rows = db.execute(
        select(Company, SavedCompany.saved_at)
        .join(SavedCompany, SavedCompany.company_id == Company.id)
        .where(SavedCompany.user_id == user.id)
        .order_by(SavedCompany.saved_at.desc())
    ).all()

    print(f"{len(rows)} entreprise(s) suivie(s) par {user.email}")
    for c, saved_at in rows:
        print(f"- {c.name} ({c.city or 'ville inconnue'}) — {c.website or 'pas de site'} — suivie le {saved_at:%Y-%m-%d}")
PY
```

```
2 entreprise(s) suivie(s) par benoit@mlmlml.com
- OncoDNA (6041 Gosselies) — https://oncodna.com/ — suivie le 2026-09-02
- QbD Group (6041 Gosselies) — pas de site — suivie le 2026-09-02
```

### Le miroir : les entreprises masquees

`hidden_companies` est exclusif de `saved_companies` (masquer retire des
favoris, enregistrer demasque). Meme requete, autre table :

```bash
docker compose exec db psql -U ananas -d ananas -c "
SELECT c.name, h.hidden_at
FROM hidden_companies h
JOIN companies c ON c.id = h.company_id
JOIN users u     ON u.id = h.user_id
WHERE u.email = 'benoit@mlmlml.com'
ORDER BY h.hidden_at DESC;"
```

### Qui suit quoi, en un coup d'oeil

```bash
docker compose exec db psql -U ananas -d ananas -c "
SELECT u.email, count(s.company_id) AS suivies
FROM users u
LEFT JOIN saved_companies s ON s.user_id = u.id
GROUP BY u.email
ORDER BY suivies DESC;"
```

---

## Migration de base de donnees

Alembic prend son URL depuis `ananas.config`, **pas** depuis `alembic.ini` — il
n'y a donc qu'un seul endroit ou definir `DATABASE_URL` (le `.env`).

### Ou en est-on

```bash
docker compose exec backend alembic current   # revision appliquee en base
docker compose exec backend alembic heads     # derniere revision du code
docker compose exec backend alembic history   # tout l'historique
```

Les deux premieres doivent afficher la meme chose. Sinon : `upgrade head`.

### Appliquer les migrations

```bash
docker compose exec backend alembic upgrade head
```

A faire apres chaque `git pull` qui touche `migrations/versions/`.

### Creer une migration

```bash
# 1. modifier ananas/models.py
# 2. autogenerer le diff modeles <-> base
docker compose exec backend alembic revision --autogenerate -m "description courte"
# 3. RELIRE le fichier genere dans migrations/versions/
# 4. appliquer
docker compose exec backend alembic upgrade head
```

Trois choses a savoir :

- **Toujours relire le fichier genere.** L'autogenerate ne voit pas les
  renommages (il produit un `drop_column` + `add_column`, qui perd les
  donnees), ni les changements de type serveur, ni les donnees a migrer.
- **Le fichier apparait sur l'hote** grace au bind mount `./api:/app`, mais il
  est ecrit par `root` dans le conteneur. Si git rale :
  `sudo chown $USER: api/migrations/versions/<fichier>.py`.
- **Un `server_default` est obligatoire** sur une colonne `NOT NULL` ajoutee a
  une table deja peuplee — c'est le motif suivi partout dans `models.py`
  (`server_default="true"`, `server_default="55"`...).

### Verifier que la base colle aux modeles

```bash
docker compose exec backend alembic check
# -> No new upgrade operations detected.
```

Repond a « ai-je oublie de generer une migration ? ». Les lignes
`Detected sequence named ... assuming SERIAL and omitting` sont normales.

### Revenir en arriere

```bash
docker compose exec backend alembic downgrade -1              # une revision
docker compose exec backend alembic downgrade a9c4e18b7d53    # une revision precise
docker compose exec backend alembic downgrade base            # tout defaire
```

### Repartir de zero (dev uniquement)

Detruit **toutes** les donnees, y compris le volume `ananas_pgdata`.

```bash
docker compose down -v
docker compose up -d db backend
docker compose exec backend alembic upgrade head
docker compose exec backend python -m ananas.seed   # reimporte les entreprises des CSV de data/
docker compose exec backend python -m ananas.admin  # recree le compte admin du .env
```

### Sauvegarder / restaurer

Le reflexe avant toute migration sur des donnees qui comptent.

```bash
# dump
docker compose exec -T db pg_dump -U ananas -d ananas > backup-$(date +%F).sql

# restauration dans une base vide
docker compose exec -T db psql -U ananas -d ananas < backup-2026-09-08.sql
```

---

## Aide-memoire

```bash
docker compose up -d db backend            # demarrer le minimum
docker compose logs -f backend             # suivre les logs
docker compose exec backend bash           # shell dans le conteneur (WORKDIR /app)
docker compose exec db psql -U ananas -d ananas   # psql interactif (\dt, \d users, \q)
docker compose restart backend             # apres un changement de .env
```

Le worker (`python -m ananas.worker.main`) est commente dans le
`docker-compose.yml`. Ses commandes ponctuelles se lancent donc depuis
`backend`, qui a le meme code et le meme environnement :

```bash
docker compose exec backend python -m ananas.worker.main --list-scrapers
docker compose exec backend python -m ananas.worker.main --scrape-only --company qbd-group
```

Voir `README.md` (worker, scrapers, extraction par lot) et `SCRAPERS.md`
(ecrire un scraper).

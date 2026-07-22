# 🧗 Cordiste Prospection AI

Agent de prospection commerciale **autonome** pour **Cordiste Île-de-France**
(travaux sur corde, travaux en hauteur, désamiantage, nettoyage de façades,
inspection et maintenance difficile d'accès).

Chaque jour, l'application recherche automatiquement de nouvelles entreprises
**privées** en Île-de-France susceptibles d'avoir besoin de travaux sur corde,
construit progressivement votre **propre base commerciale**, évite les doublons,
attribue un **score commercial** et vous envoie un **rapport quotidien par email**.

> Aucune base préremplie. Au premier lancement, une base **vide** est créée puis
> remplie automatiquement au fil des recherches. La base n'est **jamais** remise à zéro.

---

## Sommaire

- [Fonctionnalités](#fonctionnalités)
- [Comment l'IA trouve les prospects](#comment-lia-trouve-les-prospects)
- [Score commercial](#score-commercial)
- [Installation rapide](#installation-rapide)
- [Envoi des rapports (SMTP LWS)](#envoi-des-rapports-smtp-lws)
- [Tableau de bord](#tableau-de-bord)
- [Automatisation](#automatisation)
- [API](#api)
- [Architecture](#architecture)
- [Tests](#tests)
- [Conformité](#conformité-rgpd--cgu)

---

## Fonctionnalités

- 🔎 **Recherche automatique quotidienne** de prospects (agences immobilières, hôtels,
  résidences, centres commerciaux, gestionnaires de patrimoine immobilier).
- 🗺️ **Zone ciblée** : Paris (75), 77, 78, 91, 92, 93, 94, 95.
- 🧠 **Mémoire permanente** : détection de doublons sur SIRET, SIREN, site, email,
  téléphone et empreinte nom + ville. Les fiches existantes sont **mises à jour**, pas dupliquées.
- 🏆 **Score commercial automatique** : 🔥 / 🟠 / ⚪.
- 📊 **Tableau de bord web moderne** : total, nouveaux, recherche, filtres, classement,
  export CSV, historique des recherches.
- 📧 **Rapport quotidien par email** via votre hébergement LWS.
- 🕒 **Fonctionne sans intervention humaine** (scheduler interne, ou cron / systemd).
- 🐳 **Docker & Docker Compose**, déploiement VPS documenté, CI GitHub Actions.

---

## Comment l'IA trouve les prospects

La source principale est l'**API publique « Recherche d'entreprises »**
(`recherche-entreprises.api.gouv.fr`, base SIRENE de l'INSEE via la DINUM) :
gratuite, officielle, sans clé, **100 % conforme**. Elle fournit pour chaque entreprise :

nom, SIREN/SIRET, code d'activité (NAF), adresse, ville, département, tranche
d'effectif, catégorie (PME/ETI/GE), chiffre d'affaires et dirigeants.

L'IA filtre par **codes NAF cibles** (hôtellerie, immobilier, gestion de patrimoine…)
et par **département d'Île-de-France**, puis normalise chaque résultat, le déduplique
et le score.

> **Marchés publics / appels d'offres : exclus par conception.** On ne requête que le
> registre des entreprises privées ; aucune source d'appels d'offres n'est interrogée.

### Téléphone, email, site internet

La base SIRENE **ne fournit pas** ces coordonnées de contact. Les colonnes existent
dans la base et restent vides tant qu'elles ne sont pas complétées. L'architecture
prévoit une **interface d'enrichissement** (`app/sources/base.py`) : on peut brancher
plus tard une source complémentaire (ex. Google Places API, annuaire pro) sans toucher
au reste du code. Voir [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

---

## Score commercial

Le score (0–100) combine le potentiel du secteur, la taille de l'entreprise
(tranche d'effectif INSEE), la catégorie (PME/ETI/GE), le chiffre d'affaires connu
et la présence de coordonnées de contact.

| Label | Seuil | Signification |
|-------|-------|---------------|
| 🔥 Très fort potentiel | score ≥ 70 | grand parc immobilier / façades, à prioriser |
| 🟠 Potentiel intéressant | 40–69 | à qualifier |
| ⚪ Faible potentiel | < 40 | veille |

Logique dans [`app/scoring.py`](app/scoring.py).

---

## Installation rapide

### Avec Docker (recommandé)

```bash
git clone https://github.com/<votre-compte>/cordiste-prospection-ai.git
cd cordiste-prospection-ai
cp .env.example .env      # puis renseignez SMTP_PASSWORD
docker compose up -d --build
```

Tableau de bord : http://localhost:8000

### En local (Python 3.12+)

```bash
python -m venv .venv && source .venv/bin/activate   # Windows : .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env      # renseignez SMTP_PASSWORD
uvicorn app.main:app --reload
```

Lancer une recherche manuellement (sans email) :

```bash
python -m scripts.run_daily --no-email
```

Déploiement VPS complet : voir [deploy/vps-setup.md](deploy/vps-setup.md).

---

## Envoi des rapports (SMTP LWS)

Le système se connecte à votre **vraie boîte mail LWS** et envoie le rapport depuis
`contact@cordiste-ile-de-france.fr` (connexion SMTP authentifiée, ce n'est pas de
l'usurpation d'adresse). Configuration dans `.env` :

```env
SMTP_HOST=mail.cordiste-ile-de-france.fr
SMTP_PORT=465
SMTP_SECURE=true
SMTP_USER=contact@cordiste-ile-de-france.fr
SMTP_PASSWORD=            # mot de passe de la boîte (panel LWS)
SMTP_HOST_BACKUP=mail01.lwspanel.com
REPORT_RECIPIENT=contact@cordiste-ile-de-france.fr
```

- Port **465** → SSL implicite. Port **587** → mettez `SMTP_SECURE=false` (STARTTLS).
- Bascule **automatique** sur `SMTP_HOST_BACKUP` si le serveur principal échoue.
- 🔒 **Le mot de passe n'est jamais dans le code ni sur GitHub** : il vit uniquement
  dans `.env`, ignoré par `.gitignore`.

---

## Tableau de bord

Interface unique sur `/` :

- Cartes : total de prospects, découverts aujourd'hui, répartition par score.
- Recherche plein texte (nom, ville, activité), filtres par département / secteur / score.
- Tri par colonne (score, nom, ville, date).
- **Export CSV** en un clic.
- **Bouton « Lancer une recherche »** pour un cycle manuel immédiat.
- Onglet **Historique** : journal de chaque exécution (examinés, nouveaux, doublons, durée, envoi du rapport).

---

## Automatisation

Trois options (choisissez-en une) :

1. **Scheduler interne** (par défaut, `ENABLE_SCHEDULER=true`) : APScheduler déclenche
   la recherche chaque jour à `DAILY_HOUR:DAILY_MINUTE` (Europe/Paris).
2. **Timer systemd** : `deploy/cordiste-prospection.timer` (mettre `ENABLE_SCHEDULER=false`).
3. **Cron classique** : voir `deploy/crontab.example`.

Chaque exécution est journalisée en base (table `journal_recherche`) et visible dans le dashboard.

---

## API

| Méthode | Route | Description |
|---------|-------|-------------|
| GET | `/` | Tableau de bord |
| GET | `/api/health` | État + SMTP configuré ? |
| GET | `/api/stats` | Statistiques agrégées |
| GET | `/api/prospects` | Liste filtrable/triable (`q`, `departement`, `secteur`, `score_min`, `tri`, `ordre`) |
| GET | `/api/journal` | Historique des recherches |
| GET | `/api/export.csv` | Export CSV complet |
| POST | `/api/run?send_email=false` | Déclenche un cycle manuel |

Documentation interactive : `http://localhost:8000/docs` (Swagger, fourni par FastAPI).

---

## Architecture

```
app/
  config.py        Configuration (.env)
  database.py      SQLAlchemy — base SQLite (PostgreSQL possible)
  models.py        Prospect + JournalRecherche
  sectors.py       Secteurs cibles & codes NAF
  sources/         Sources de prospection (interface + SIRENE)
  dedup.py         Détection de doublons (mémoire permanente)
  scoring.py       Score commercial
  prospecting.py   Orchestration d'un cycle
  mailer.py        Envoi SMTP (LWS + secours)
  report.py        Contenu du rapport (HTML + texte)
  jobs.py          Tâche quotidienne (recherche + rapport)
  scheduler.py     Cron interne (APScheduler)
  main.py          API FastAPI + dashboard
scripts/run_daily.py   Exécution CLI (cron/systemd)
tests/                 Tests unitaires & d'intégration
deploy/                systemd, timer, cron, guide VPS
```

Détails : [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

---

## Tests

```bash
pip install -r requirements.txt
pytest
```

Les tests n'appellent **jamais** l'API réelle (sources factices), ils tournent hors-ligne.

---

## Conformité (RGPD / CGU)

- Données issues d'une **source publique et officielle** (SIRENE / registre des entreprises).
- Cible **B2B uniquement** : entreprises privées, pas de particuliers.
- Le champ « contact » ne reprend que des **dirigeants diffusés publiquement** par le registre.
- Prospection commerciale B2B : informez les personnes de leur droit d'opposition et
  n'utilisez les coordonnées que pour une offre en lien avec leur activité professionnelle.
- Aucune source n'est scrapée en violation de ses CGU ; l'API publique est appelée avec
  un rythme raisonnable.

Ce dépôt est un outil ; l'usage conforme (RGPD, e-privacy, CGU des services tiers
éventuellement ajoutés) relève de l'exploitant.

---

## Licence

MIT — voir [LICENSE](LICENSE).

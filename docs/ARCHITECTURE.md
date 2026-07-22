# Architecture

## Flux d'un cycle de prospection

```
scheduler / cron / bouton dashboard
        │
        ▼
  jobs.run_daily_job()
        │
        ▼
  prospecting.run_prospection(session, sources)
        │
        ├─ pour chaque source (SireneSource, …)
        │     source.fetch()  ──► candidats normalisés (dict)
        │
        ├─ filtre département Île-de-France
        ├─ dédup intra-run (SIRET / empreinte)
        ├─ scoring.compute_score()  ──► score + label
        ├─ dedup.find_existing()
        │     ├─ existant ──► apply_updates() (MAJ des champs modifiés)
        │     └─ nouveau  ──► INSERT Prospect
        │
        └─ écrit une ligne dans journal_recherche
        │
        ▼
  report.build_html/text()  ──►  mailer.send_report()  (SMTP LWS)
```

## Principes

**Mémoire permanente.** La base SQLite (`data/prospects.db`) n'est jamais réinitialisée.
`init_db()` fait un `CREATE TABLE IF NOT EXISTS` : premier lancement = base vide, ensuite
on ne fait qu'ajouter/mettre à jour.

**Déduplication en cascade** (`dedup.find_existing`) : SIRET → SIREN → domaine du site →
email → téléphone → empreinte `nom+ville` normalisée. Le premier critère qui matche gagne.
`apply_updates` ne modifie que les champs réellement différents et renvoie la liste des
changements (permet de distinguer « mis à jour » de « doublon sans changement »).

**Sources extensibles.** Toute source implémente `ProspectSource.fetch()` et renvoie des
dictionnaires au schéma commun (voir `sources/base.py`). Ajouter Google Places, un annuaire
professionnel ou un enrichissement LLM = ajouter une classe et l'inscrire dans
`prospecting.default_sources()`. Rien d'autre à modifier : dédup, scoring, rapport et
dashboard fonctionnent tels quels.

**Scoring configurable.** Les pondérations vivent dans `scoring.py` et `sectors.py`
(poids par secteur, points par tranche d'effectif, catégorie, CA). Ajustables sans toucher
à la logique.

## Base de données

Deux tables :

- `prospects` — la fiche commerciale (contrainte d'unicité sur `siret`).
- `journal_recherche` — une ligne par exécution (audit + onglet Historique).

Passage à PostgreSQL : renseigner `DATABASE_URL` dans `.env`, décommenter
`psycopg2-binary` dans `requirements.txt` et le service `db` dans `docker-compose.yml`.
Aucune modification de code (SQLAlchemy abstrait le moteur).

## Sécurité des secrets

Le mot de passe SMTP n'existe que dans `.env` (chargé par `python-dotenv`), ignoré par
`.gitignore`. Aucune valeur sensible n'est écrite en dur dans le code ni committée.

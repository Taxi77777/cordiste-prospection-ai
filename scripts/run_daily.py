#!/usr/bin/env python3
"""Exécute un cycle de prospection en ligne de commande.

Utilisé par le cron système / GitHub Actions / lancement manuel :

    python -m scripts.run_daily            # recherche + envoi du rapport
    python -m scripts.run_daily --no-email # recherche seule (test)
"""
from __future__ import annotations

import argparse
import logging

from app.database import init_db
from app.jobs import run_daily_job


def main() -> None:
    parser = argparse.ArgumentParser(description="Cordiste Prospection AI — tâche quotidienne")
    parser.add_argument("--no-email", action="store_true", help="ne pas envoyer le rapport")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
    init_db()  # crée la base vide si premier lancement
    result = run_daily_job(send_email=not args.no_email)

    print(
        f"Terminé : {result.nouveaux} nouveaux, {result.mis_a_jour} mis à jour, "
        f"{result.doublons} doublons évités ({result.examines} examinés, "
        f"{result.duree_secondes}s)."
    )
    if result.erreur:
        print(f"Erreur : {result.erreur}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()

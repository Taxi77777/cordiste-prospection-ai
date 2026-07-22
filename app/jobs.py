"""Tâche quotidienne : prospecter puis envoyer le rapport par email."""
from __future__ import annotations

import logging

from sqlalchemy import select

from .database import SessionLocal
from .mailer import MailError, send_report
from .models import JournalRecherche
from .prospecting import RunResult, run_prospection
from .report import build_html, build_subject, build_text

logger = logging.getLogger(__name__)


def run_daily_job(send_email: bool = True) -> RunResult:
    """Cycle complet : recherche + rapport. Utilisé par le cron et le CLI."""
    session = SessionLocal()
    try:
        result = run_prospection(session)

        rapport_statut = "non"
        if send_email:
            try:
                send_report(
                    subject=build_subject(result),
                    html_body=build_html(result),
                    text_body=build_text(result),
                )
                rapport_statut = "oui"
            except MailError as exc:
                rapport_statut = "erreur"
                logger.error("Rapport non envoyé : %s", exc)

        # Met à jour la dernière ligne du journal avec le statut d'envoi.
        last = session.scalar(
            select(JournalRecherche).order_by(JournalRecherche.id.desc())
        )
        if last:
            last.rapport_envoye = rapport_statut
            session.commit()

        return result
    finally:
        session.close()

"""Envoi du rapport quotidien par email via SMTP (hébergement LWS).

- Port 465 + SSL implicite (SMTP_SECURE=true) : connexion SMTP_SSL.
- Port 587 + STARTTLS : SMTP puis .starttls().
- Bascule automatiquement sur le serveur de secours (SMTP_HOST_BACKUP) en cas d'échec.
Le mot de passe provient exclusivement de la variable d'environnement SMTP_PASSWORD.
"""
from __future__ import annotations

import logging
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr

from .config import settings

logger = logging.getLogger(__name__)


class MailError(RuntimeError):
    pass


def _send_via(host: str, msg: MIMEMultipart) -> None:
    smtp = settings.smtp
    context = ssl.create_default_context()
    if smtp.secure or smtp.port == 465:
        with smtplib.SMTP_SSL(host, smtp.port, context=context, timeout=30) as server:
            server.login(smtp.user, smtp.password)
            server.send_message(msg)
    else:
        with smtplib.SMTP(host, smtp.port, timeout=30) as server:
            server.ehlo()
            server.starttls(context=context)
            server.login(smtp.user, smtp.password)
            server.send_message(msg)


def send_report(subject: str, html_body: str, text_body: str | None = None) -> None:
    """Envoie le rapport. Lève MailError si tous les serveurs échouent."""
    smtp = settings.smtp
    if not smtp.is_configured:
        raise MailError(
            "SMTP non configuré : renseignez SMTP_USER et SMTP_PASSWORD dans .env"
        )

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = formataddr((settings.report_sender_name, smtp.user))
    msg["To"] = settings.report_recipient
    msg.attach(MIMEText(text_body or "Rapport de prospection Cordiste IDF.", "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    last_error: Exception | None = None
    for host in (smtp.host, smtp.host_backup):
        if not host:
            continue
        try:
            _send_via(host, msg)
            logger.info("Rapport envoyé via %s à %s", host, settings.report_recipient)
            return
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            logger.warning("Echec envoi via %s : %s", host, exc)

    raise MailError(f"Impossible d'envoyer le rapport : {last_error}")

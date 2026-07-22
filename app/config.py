"""Configuration centralisée, chargée depuis les variables d'environnement (.env)."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

# Charge .env si présent (aucune erreur si absent).
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)


def _get_bool(key: str, default: bool = False) -> bool:
    val = os.getenv(key)
    if val is None:
        return default
    return val.strip().lower() in {"1", "true", "yes", "on", "oui"}


def _get_int(key: str, default: int) -> int:
    try:
        return int(os.getenv(key, default))
    except (TypeError, ValueError):
        return default


@dataclass
class SMTPConfig:
    host: str = os.getenv("SMTP_HOST", "mail.cordiste-ile-de-france.fr")
    host_backup: str = os.getenv("SMTP_HOST_BACKUP", "mail01.lwspanel.com")
    port: int = _get_int("SMTP_PORT", 465)
    secure: bool = _get_bool("SMTP_SECURE", True)  # True = SSL/TLS implicite (port 465)
    user: str = os.getenv("SMTP_USER", "contact@cordiste-ile-de-france.fr")
    password: str = os.getenv("SMTP_PASSWORD", "")

    @property
    def is_configured(self) -> bool:
        return bool(self.host and self.user and self.password)


@dataclass
class AppConfig:
    # Base de données : SQLite par défaut, PostgreSQL possible via DATABASE_URL.
    database_url: str = os.getenv("DATABASE_URL", f"sqlite:///{DATA_DIR / 'prospects.db'}")

    # Destinataire du rapport quotidien.
    report_recipient: str = os.getenv("REPORT_RECIPIENT", "contact@cordiste-ile-de-france.fr")
    report_sender_name: str = os.getenv("REPORT_SENDER_NAME", "Cordiste Prospection AI")

    # Planification du cron interne (heure locale du serveur).
    daily_hour: int = _get_int("DAILY_HOUR", 7)
    daily_minute: int = _get_int("DAILY_MINUTE", 30)
    enable_scheduler: bool = _get_bool("ENABLE_SCHEDULER", True)

    # Volume de recherche par exécution (limite d'appels API par catégorie/département).
    max_pages_per_query: int = _get_int("MAX_PAGES_PER_QUERY", 2)
    per_page: int = _get_int("PER_PAGE", 25)
    request_timeout: int = _get_int("REQUEST_TIMEOUT", 30)

    # Départements d'Île-de-France ciblés.
    departements: list[str] = field(
        default_factory=lambda: os.getenv(
            "DEPARTEMENTS", "75,77,78,91,92,93,94,95"
        ).split(",")
    )

    # N'enregistrer que les entreprises actives.
    only_active: bool = _get_bool("ONLY_ACTIVE", True)

    smtp: SMTPConfig = field(default_factory=SMTPConfig)


settings = AppConfig()

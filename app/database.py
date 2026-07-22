"""Configuration de la base de données (SQLAlchemy).

Au premier lancement, la base est créée automatiquement et VIDE.
SQLite par défaut ; passage à PostgreSQL possible via DATABASE_URL sans changer le code.
"""
from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import settings


class Base(DeclarativeBase):
    pass


_connect_args = {}
if settings.database_url.startswith("sqlite"):
    # Nécessaire pour l'usage multi-thread (FastAPI + scheduler).
    _connect_args = {"check_same_thread": False}

engine = create_engine(
    settings.database_url,
    echo=False,
    future=True,
    connect_args=_connect_args,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def init_db() -> None:
    """Crée les tables si elles n'existent pas (base vide au 1er lancement)."""
    from . import models  # noqa: F401  (import pour enregistrer les modèles)

    Base.metadata.create_all(bind=engine)


def get_session() -> Generator[Session, None, None]:
    """Dépendance FastAPI : fournit une session et la referme proprement."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

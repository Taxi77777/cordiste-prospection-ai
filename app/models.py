"""Modèles ORM : Prospect et JournalRecherche (historique / logs)."""
from __future__ import annotations

from datetime import datetime, date

from sqlalchemy import (
    Date,
    DateTime,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class Prospect(Base):
    __tablename__ = "prospects"
    __table_args__ = (
        # SIRET unique quand présent : garde-fou anti-doublon au niveau base.
        UniqueConstraint("siret", name="uq_prospect_siret"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Identité
    nom: Mapped[str] = mapped_column(String(300), index=True)
    activite: Mapped[str | None] = mapped_column(String(200))
    secteur: Mapped[str | None] = mapped_column(String(120), index=True)
    naf: Mapped[str | None] = mapped_column(String(10))

    # Localisation
    adresse: Mapped[str | None] = mapped_column(String(400))
    ville: Mapped[str | None] = mapped_column(String(200), index=True)
    code_postal: Mapped[str | None] = mapped_column(String(10))
    departement: Mapped[str | None] = mapped_column(String(5), index=True)

    # Coordonnées professionnelles (publiques, souvent à enrichir)
    telephone: Mapped[str | None] = mapped_column(String(40))
    email: Mapped[str | None] = mapped_column(String(200))
    site_internet: Mapped[str | None] = mapped_column(String(300))
    contact_nom: Mapped[str | None] = mapped_column(String(200))

    # Données servant au scoring
    siret: Mapped[str | None] = mapped_column(String(20), index=True)
    siren: Mapped[str | None] = mapped_column(String(15), index=True)
    tranche_effectif: Mapped[str | None] = mapped_column(String(5))
    categorie_entreprise: Mapped[str | None] = mapped_column(String(10))  # PME/ETI/GE
    chiffre_affaires: Mapped[int | None] = mapped_column(Integer)

    # Score commercial
    score: Mapped[int | None] = mapped_column(Integer, default=0)
    score_label: Mapped[str | None] = mapped_column(String(40))  # 🔥 / 🟠 / ⚪
    # Champs alimentés par l'IA (optionnels).
    score_justification: Mapped[str | None] = mapped_column(Text)
    message_prospection: Mapped[str | None] = mapped_column(Text)

    # Traçabilité
    source: Mapped[str | None] = mapped_column(String(80))
    date_decouverte: Mapped[date] = mapped_column(Date, default=date.today, index=True)
    date_maj: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now()
    )
    # Empreinte anti-doublon (nom + ville normalisés) quand SIRET absent.
    fingerprint: Mapped[str | None] = mapped_column(String(255), index=True)

    notes: Mapped[str | None] = mapped_column(Text)

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "nom": self.nom,
            "activite": self.activite,
            "secteur": self.secteur,
            "naf": self.naf,
            "adresse": self.adresse,
            "ville": self.ville,
            "code_postal": self.code_postal,
            "departement": self.departement,
            "telephone": self.telephone,
            "email": self.email,
            "site_internet": self.site_internet,
            "contact_nom": self.contact_nom,
            "siret": self.siret,
            "siren": self.siren,
            "tranche_effectif": self.tranche_effectif,
            "categorie_entreprise": self.categorie_entreprise,
            "chiffre_affaires": self.chiffre_affaires,
            "score": self.score,
            "score_label": self.score_label,
            "score_justification": self.score_justification,
            "message_prospection": self.message_prospection,
            "source": self.source,
            "date_decouverte": self.date_decouverte.isoformat() if self.date_decouverte else None,
            "date_maj": self.date_maj.isoformat() if self.date_maj else None,
        }


class JournalRecherche(Base):
    """Historique des exécutions de recherche (audit + tableau de bord)."""

    __tablename__ = "journal_recherche"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    horodatage: Mapped[datetime] = mapped_column(DateTime, default=func.now(), index=True)
    statut: Mapped[str] = mapped_column(String(20))  # succes / erreur
    examines: Mapped[int] = mapped_column(Integer, default=0)
    nouveaux: Mapped[int] = mapped_column(Integer, default=0)
    mis_a_jour: Mapped[int] = mapped_column(Integer, default=0)
    doublons: Mapped[int] = mapped_column(Integer, default=0)
    duree_secondes: Mapped[float | None] = mapped_column()
    rapport_envoye: Mapped[str | None] = mapped_column(String(20))  # oui/non/erreur
    message: Mapped[str | None] = mapped_column(Text)

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "horodatage": self.horodatage.isoformat() if self.horodatage else None,
            "statut": self.statut,
            "examines": self.examines,
            "nouveaux": self.nouveaux,
            "mis_a_jour": self.mis_a_jour,
            "doublons": self.doublons,
            "duree_secondes": self.duree_secondes,
            "rapport_envoye": self.rapport_envoye,
            "message": self.message,
        }

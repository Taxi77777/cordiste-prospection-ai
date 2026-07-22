"""Détection de doublons (mémoire permanente de l'IA).

Ordre de vérification :
  1. SIRET (identifiant unique le plus fiable)
  2. SIREN
  3. Site internet (domaine normalisé)
  4. Email professionnel
  5. Téléphone (chiffres uniquement)
  6. Empreinte nom + ville (normalisée) en dernier recours
"""
from __future__ import annotations

import re
import unicodedata

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Prospect


def _strip_accents(text: str) -> str:
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def normalize_name(name: str | None) -> str:
    if not name:
        return ""
    name = _strip_accents(name).lower()
    # Retire formes juridiques et ponctuation pour comparer le « vrai » nom.
    name = re.sub(r"\b(sarl|sas|sasu|sa|eurl|sci|snc|scp|selarl|group|groupe)\b", " ", name)
    name = re.sub(r"[^a-z0-9]+", " ", name)
    return re.sub(r"\s+", " ", name).strip()


def normalize_city(city: str | None) -> str:
    if not city:
        return ""
    return re.sub(r"\s+", " ", _strip_accents(city).lower()).strip()


def normalize_phone(phone: str | None) -> str:
    if not phone:
        return ""
    digits = re.sub(r"\D", "", phone)
    # Normalise le préfixe international français.
    if digits.startswith("33") and len(digits) == 11:
        digits = "0" + digits[2:]
    return digits


def normalize_domain(url: str | None) -> str:
    if not url:
        return ""
    url = url.strip().lower()
    url = re.sub(r"^https?://", "", url)
    url = re.sub(r"^www\.", "", url)
    return url.split("/")[0].strip()


def normalize_email(email: str | None) -> str:
    return email.strip().lower() if email else ""


def make_fingerprint(nom: str | None, ville: str | None) -> str:
    return f"{normalize_name(nom)}|{normalize_city(ville)}"


def find_existing(session: Session, candidate: dict) -> Prospect | None:
    """Renvoie le prospect existant correspondant, sinon None."""
    # 1. SIRET
    siret = (candidate.get("siret") or "").strip()
    if siret:
        found = session.scalar(select(Prospect).where(Prospect.siret == siret))
        if found:
            return found

    # 2. SIREN
    siren = (candidate.get("siren") or "").strip()
    if siren:
        found = session.scalar(select(Prospect).where(Prospect.siren == siren))
        if found:
            return found

    # 3. Domaine site internet
    domain = normalize_domain(candidate.get("site_internet"))
    if domain:
        for p in session.scalars(
            select(Prospect).where(Prospect.site_internet.isnot(None))
        ):
            if normalize_domain(p.site_internet) == domain:
                return p

    # 4. Email
    email = normalize_email(candidate.get("email"))
    if email:
        for p in session.scalars(select(Prospect).where(Prospect.email.isnot(None))):
            if normalize_email(p.email) == email:
                return p

    # 5. Téléphone
    phone = normalize_phone(candidate.get("telephone"))
    if phone:
        for p in session.scalars(select(Prospect).where(Prospect.telephone.isnot(None))):
            if normalize_phone(p.telephone) == phone:
                return p

    # 6. Empreinte nom + ville
    fp = make_fingerprint(candidate.get("nom"), candidate.get("ville"))
    if fp and fp != "|":
        found = session.scalar(select(Prospect).where(Prospect.fingerprint == fp))
        if found:
            return found

    return None


# Champs pouvant être complétés/mis à jour sur un prospect existant.
UPDATABLE_FIELDS = (
    "activite",
    "secteur",
    "naf",
    "adresse",
    "ville",
    "code_postal",
    "departement",
    "telephone",
    "email",
    "site_internet",
    "contact_nom",
    "tranche_effectif",
    "categorie_entreprise",
    "chiffre_affaires",
    "siret",
    "siren",
)


def apply_updates(existing: Prospect, candidate: dict) -> list[str]:
    """Met à jour uniquement les champs qui ont changé. Renvoie la liste des champs modifiés."""
    changed: list[str] = []
    for field in UPDATABLE_FIELDS:
        new_val = candidate.get(field)
        if new_val in (None, ""):
            continue
        old_val = getattr(existing, field)
        # On complète les champs vides et on met à jour les valeurs différentes.
        if old_val in (None, "") or str(old_val) != str(new_val):
            setattr(existing, field, new_val)
            changed.append(field)
    return changed

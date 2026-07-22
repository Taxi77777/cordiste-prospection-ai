"""Source SIRENE via l'API publique « Recherche d'entreprises » (data.gouv / DINUM).

API ouverte, gratuite, sans clé : https://recherche-entreprises.api.gouv.fr
Base officielle des entreprises françaises — usage 100 % conforme.

Elle fournit : identité, SIREN/SIRET, code NAF, adresse, effectifs, catégorie,
chiffre d'affaires et dirigeants. Le téléphone / email / site ne sont PAS fournis
par cette source : ces champs restent vides et pourront être complétés plus tard
par une source d'enrichissement (voir sources/base.py).
"""
from __future__ import annotations

import logging
import time
from collections.abc import Iterable

import requests

from ..config import settings
from ..sectors import SECTORS, sector_for_naf
from .base import ProspectSource

logger = logging.getLogger(__name__)

API_URL = "https://recherche-entreprises.api.gouv.fr/search"
USER_AGENT = "cordiste-prospection-ai/1.0 (+https://cordiste-ile-de-france.fr)"


class SireneSource(ProspectSource):
    name = "SIRENE / recherche-entreprises.api.gouv.fr"

    def __init__(self, session: requests.Session | None = None) -> None:
        self.http = session or requests.Session()
        self.http.headers.update({"User-Agent": USER_AGENT})

    # -- Appel HTTP unitaire ------------------------------------------------
    def _query(self, naf: str, departement: str, page: int) -> dict:
        params = {
            "activite_principale": naf,
            "departement": departement,
            "etat_administratif": "A" if settings.only_active else None,
            "page": page,
            "per_page": settings.per_page,
        }
        params = {k: v for k, v in params.items() if v is not None}
        resp = self.http.get(API_URL, params=params, timeout=settings.request_timeout)
        resp.raise_for_status()
        return resp.json()

    # -- Normalisation d'un résultat API -> candidat ------------------------
    @staticmethod
    def _to_candidate(item: dict) -> dict | None:
        siege = item.get("siege") or {}
        naf = item.get("activite_principale") or siege.get("activite_principale")
        sector = sector_for_naf(naf)

        # Contact = premier dirigeant personne physique, si diffusé publiquement.
        contact_nom = None
        for d in item.get("dirigeants") or []:
            if d.get("type_dirigeant") == "personne physique":
                prenom = (d.get("prenoms") or "").strip()
                nom = (d.get("nom") or "").strip()
                full = f"{prenom} {nom}".strip()
                if full:
                    contact_nom = full
                    break

        # Chiffre d'affaires : dernière année disponible.
        ca = None
        finances = item.get("finances") or {}
        if finances:
            try:
                last_year = max(finances.keys())
                ca = (finances[last_year] or {}).get("ca")
            except (ValueError, TypeError):
                ca = None

        nom = item.get("nom_complet") or item.get("nom_raison_sociale")
        if not nom:
            return None

        return {
            "nom": nom,
            "activite": sector.label if sector else None,
            "secteur": sector.key if sector else None,
            "naf": naf,
            "adresse": siege.get("geo_adresse") or siege.get("adresse"),
            "ville": siege.get("libelle_commune"),
            "code_postal": siege.get("code_postal"),
            "departement": siege.get("departement"),
            "telephone": None,          # non fourni par SIRENE
            "email": None,              # non fourni par SIRENE
            "site_internet": None,      # non fourni par SIRENE
            "contact_nom": contact_nom,
            "siret": siege.get("siret"),
            "siren": item.get("siren"),
            "tranche_effectif": item.get("tranche_effectif_salarie"),
            "categorie_entreprise": item.get("categorie_entreprise"),
            "chiffre_affaires": ca,
            "source": "SIRENE",
        }

    # -- Génération de tous les candidats -----------------------------------
    def fetch(self) -> Iterable[dict]:
        for sector in SECTORS:
            for naf in sector.naf_codes:
                for dept in settings.departements:
                    dept = dept.strip()
                    yield from self._fetch_query(naf, dept)

    def _fetch_query(self, naf: str, dept: str) -> Iterable[dict]:
        for page in range(1, settings.max_pages_per_query + 1):
            try:
                data = self._query(naf, dept, page)
            except requests.RequestException as exc:
                logger.warning("Echec requête SIRENE naf=%s dept=%s page=%s : %s",
                               naf, dept, page, exc)
                break

            results = data.get("results") or []
            if not results:
                break

            for item in results:
                cand = self._to_candidate(item)
                if cand:
                    yield cand

            if page >= (data.get("total_pages") or 1):
                break
            time.sleep(0.2)  # courtoisie envers l'API publique

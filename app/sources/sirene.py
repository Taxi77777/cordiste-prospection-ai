"""Source SIRENE via l'API publique « Recherche d'entreprises » (data.gouv / DINUM).

API ouverte, gratuite, sans clé : https://recherche-entreprises.api.gouv.fr
Base officielle des entreprises françaises — usage 100 % conforme.

Gère le débit : l'API limite le nombre de requêtes par seconde (sinon 429).
On espace les appels et on réessaie automatiquement en cas de 429/5xx.
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

# Rythme respectueux de l'API publique (limite ~7 req/s ; les rafales renvoient 429).
THROTTLE_SECONDS = 1.2
MAX_RETRIES = 4


class SireneSource(ProspectSource):
    name = "SIRENE / recherche-entreprises.api.gouv.fr"

    def __init__(self, session: requests.Session | None = None) -> None:
        self.http = session or requests.Session()
        self.http.headers.update({"User-Agent": USER_AGENT})

    # -- Appel HTTP avec throttle + réessais -------------------------------
    def _get(self, params: dict) -> dict:
        backoff = 5.0
        for attempt in range(1, MAX_RETRIES + 1):
            resp = self.http.get(API_URL, params=params, timeout=settings.request_timeout)
            if resp.status_code == 429 or resp.status_code >= 500:
                wait = float(resp.headers.get("Retry-After") or backoff)
                logger.warning("SIRENE %s — pause %.0fs (tentative %s/%s)",
                               resp.status_code, wait, attempt, MAX_RETRIES)
                time.sleep(wait)
                backoff = min(backoff * 2, 60)
                continue
            resp.raise_for_status()
            time.sleep(THROTTLE_SECONDS)  # espace les requêtes pour éviter les 429
            return resp.json()
        logger.warning("SIRENE : abandon après %s tentatives (params=%s)", MAX_RETRIES, params)
        return {"results": [], "total_pages": 0}

    def _query(self, naf: str, departement: str, page: int) -> dict:
        params = {
            "activite_principale": naf,
            "departement": departement,
            "etat_administratif": "A" if settings.only_active else None,
            "page": page,
            "per_page": settings.per_page,
        }
        params = {k: v for k, v in params.items() if v is not None}
        return self._get(params)

    # -- Normalisation d'un résultat API -> candidat ------------------------
    @staticmethod
    def _to_candidate(item: dict) -> dict | None:
        siege = item.get("siege") or {}
        naf = item.get("activite_principale") or siege.get("activite_principale")
        sector = sector_for_naf(naf)

        contact_nom = None
        for d in item.get("dirigeants") or []:
            if d.get("type_dirigeant") == "personne physique":
                prenom = (d.get("prenoms") or "").strip()
                nom = (d.get("nom") or "").strip()
                full = f"{prenom} {nom}".strip()
                if full:
                    contact_nom = full
                    break

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
            "telephone": None,
            "email": None,
            "site_internet": None,
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

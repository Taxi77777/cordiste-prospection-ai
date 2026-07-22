"""Interface commune des sources de prospection.

Ajouter une nouvelle source (Google Places, enrichissement LLM, etc.) revient à
implémenter `fetch()` en renvoyant des dictionnaires normalisés — aucun autre code
à modifier. Le champ retourné doit correspondre aux clés utilisées par dedup/scoring.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable


# Schéma d'un candidat normalisé renvoyé par une source :
#   {
#     "nom", "activite", "secteur", "naf",
#     "adresse", "ville", "code_postal", "departement",
#     "telephone", "email", "site_internet", "contact_nom",
#     "siret", "siren", "tranche_effectif", "categorie_entreprise",
#     "chiffre_affaires", "source"
#   }


class ProspectSource(ABC):
    name: str = "abstract"

    @abstractmethod
    def fetch(self) -> Iterable[dict]:
        """Génère des prospects candidats normalisés (dictionnaires)."""
        raise NotImplementedError

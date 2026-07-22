"""Secteurs cibles et codes NAF associés.

On cible uniquement des entreprises PRIVÉES susceptibles d'avoir régulièrement
besoin de travaux sur corde / travaux en hauteur : gestionnaires de patrimoine
immobilier, agences immobilières, hôtels, résidences, centres commerciaux.

Chaque secteur porte un `base_weight` (0-100) qui alimente le score commercial :
plus le secteur a de façades / hauteur / parc à entretenir, plus il est prioritaire.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Sector:
    key: str
    label: str
    naf_codes: tuple[str, ...]
    base_weight: int  # potentiel intrinsèque du secteur (0-100)


# Codes NAF (nomenclature INSEE). Format « 68.31Z ».
SECTORS: tuple[Sector, ...] = (
    Sector(
        key="gestion_immobiliere",
        label="Gestionnaire de patrimoine immobilier",
        naf_codes=("68.32A", "68.32B", "68.20B"),
        base_weight=95,
    ),
    Sector(
        key="agence_immobiliere",
        label="Agence immobilière",
        naf_codes=("68.31Z",),
        base_weight=80,
    ),
    Sector(
        key="hotel",
        label="Hôtel",
        naf_codes=("55.10Z",),
        base_weight=85,
    ),
    Sector(
        key="residence",
        label="Résidence / hébergement",
        naf_codes=("55.20Z", "55.90Z", "68.20A"),
        base_weight=75,
    ),
    Sector(
        key="centre_commercial",
        label="Centre commercial / immobilier non résidentiel",
        naf_codes=("68.20B", "68.32A"),
        base_weight=90,
    ),
)

# Index code NAF -> secteur (le premier secteur déclarant le code gagne).
_NAF_TO_SECTOR: dict[str, Sector] = {}
for _s in SECTORS:
    for _code in _s.naf_codes:
        _NAF_TO_SECTOR.setdefault(_code, _s)


def all_naf_codes() -> list[str]:
    """Liste dédupliquée de tous les codes NAF ciblés."""
    seen: dict[str, None] = {}
    for s in SECTORS:
        for c in s.naf_codes:
            seen.setdefault(c, None)
    return list(seen.keys())


def sector_for_naf(naf: str | None) -> Sector | None:
    if not naf:
        return None
    return _NAF_TO_SECTOR.get(naf.strip().upper())

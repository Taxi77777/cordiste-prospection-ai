"""Score commercial automatique.

Combine :
  - le potentiel du secteur (base_weight),
  - la taille de l'entreprise (tranche d'effectif INSEE),
  - la catégorie d'entreprise (PME/ETI/GE),
  - le chiffre d'affaires connu,
  - un bonus si des coordonnées de contact directes existent.

Renvoie un score 0-100 et un label :
  🔥 Très fort potentiel     (>= 70)
  🟠 Potentiel intéressant   (40-69)
  ⚪ Faible potentiel        (< 40)
"""
from __future__ import annotations

from .sectors import sector_for_naf

LABEL_HOT = "🔥 Très fort potentiel"
LABEL_WARM = "🟠 Potentiel intéressant"
LABEL_COLD = "⚪ Faible potentiel"

# Tranches d'effectif INSEE -> points (0-30).
# Codes : NN=non renseigné, 00=0 sal., 01=1-2, 02=3-5, 03=6-9, 11=10-19,
# 12=20-49, 21=50-99, 22=100-199, 31=200-249, 32=250-499, 41=500-999,
# 42=1000-1999, 51=2000-4999, 52=5000-9999, 53=10000+.
_EFFECTIF_POINTS = {
    "00": 0, "01": 2, "02": 4, "03": 6,
    "11": 10, "12": 16, "21": 22, "22": 26,
    "31": 28, "32": 30, "41": 30, "42": 30,
    "51": 30, "52": 30, "53": 30,
}

_CATEGORIE_POINTS = {"PME": 8, "ETI": 15, "GE": 20}


def _effectif_points(tranche: str | None) -> int:
    if not tranche:
        return 0
    return _EFFECTIF_POINTS.get(tranche.strip(), 0)


def _ca_points(ca: int | None) -> int:
    if not ca or ca <= 0:
        return 0
    if ca >= 50_000_000:
        return 15
    if ca >= 10_000_000:
        return 12
    if ca >= 2_000_000:
        return 8
    if ca >= 500_000:
        return 4
    return 2


def compute_score(candidate: dict) -> tuple[int, str]:
    """Calcule (score, label) pour un prospect candidat."""
    score = 0

    sector = sector_for_naf(candidate.get("naf"))
    # Potentiel secteur ramené sur 35 points.
    if sector:
        score += round(sector.base_weight * 0.35)

    score += _effectif_points(candidate.get("tranche_effectif"))
    score += _CATEGORIE_POINTS.get((candidate.get("categorie_entreprise") or "").upper(), 0)
    score += _ca_points(candidate.get("chiffre_affaires"))

    # Bonus joignabilité : un prospect qu'on peut contacter directement vaut plus.
    if candidate.get("telephone"):
        score += 3
    if candidate.get("email"):
        score += 4
    if candidate.get("site_internet"):
        score += 3

    score = max(0, min(100, score))
    return score, label_for_score(score)


def label_for_score(score: int) -> str:
    """Renvoie le label 🔥/🟠/⚪ correspondant à un score (utilisé aussi par l'IA)."""
    if score >= 70:
        return LABEL_HOT
    if score >= 40:
        return LABEL_WARM
    return LABEL_COLD

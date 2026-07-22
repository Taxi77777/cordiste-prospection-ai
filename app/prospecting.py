"""Orchestration d'un cycle de prospection.

Enchaîne : source(s) -> déduplication -> scoring -> écriture DB -> journal.
Renvoie la liste des NOUVEAUX prospects (pour le rapport quotidien).
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import date

from sqlalchemy.orm import Session

from . import ai, dedup
from .config import settings
from .models import JournalRecherche, Prospect
from .scoring import compute_score, label_for_score
from .sources import ProspectSource, SireneSource

logger = logging.getLogger(__name__)


@dataclass
class RunResult:
    examines: int = 0
    nouveaux: int = 0
    mis_a_jour: int = 0
    doublons: int = 0
    duree_secondes: float = 0.0
    nouveaux_prospects: list[dict] = field(default_factory=list)
    erreur: str | None = None


def default_sources() -> list[ProspectSource]:
    """Sources actives. Ajoutez ici Google Places / enrichissement plus tard."""
    return [SireneSource()]


def run_prospection(
    session: Session,
    sources: list[ProspectSource] | None = None,
) -> RunResult:
    """Exécute un cycle complet et enregistre le résultat dans le journal."""
    start = time.perf_counter()
    sources = sources or default_sources()
    result = RunResult()

    try:
        seen_this_run: set[str] = set()
        for source in sources:
            for cand in source.fetch():
                result.examines += 1

                # Filtre départements Île-de-France.
                dept = (cand.get("departement") or "").strip()
                if settings.departements and dept not in settings.departements:
                    continue

                # Dédup intra-exécution (même SIRET vu plusieurs fois).
                key = cand.get("siret") or dedup.make_fingerprint(
                    cand.get("nom"), cand.get("ville")
                )
                if key in seen_this_run:
                    result.doublons += 1
                    continue
                seen_this_run.add(key)

                score, label = compute_score(cand)
                cand["score"] = score
                cand["score_label"] = label
                cand["score_justification"] = None
                cand["message_prospection"] = None

                # Enrichissement IA optionnel : n'écrase les règles que si l'IA répond.
                if ai.is_available():
                    ai_res = ai.score_prospect(cand)
                    if ai_res:
                        score = ai_res["score"]
                        label = label_for_score(score)
                        cand["score"] = score
                        cand["score_label"] = label
                        cand["score_justification"] = ai_res.get("justification")
                    msg = ai.generate_outreach(cand)
                    if msg:
                        cand["message_prospection"] = msg

                existing = dedup.find_existing(session, cand)
                if existing:
                    changed = dedup.apply_updates(existing, cand)
                    # Recalcule le score si des données pertinentes ont changé.
                    existing.score, existing.score_label = compute_score(existing.as_dict())
                    if changed:
                        result.mis_a_jour += 1
                    else:
                        result.doublons += 1
                    continue

                prospect = Prospect(
                    nom=cand.get("nom"),
                    activite=cand.get("activite"),
                    secteur=cand.get("secteur"),
                    naf=cand.get("naf"),
                    adresse=cand.get("adresse"),
                    ville=cand.get("ville"),
                    code_postal=cand.get("code_postal"),
                    departement=dept,
                    telephone=cand.get("telephone"),
                    email=cand.get("email"),
                    site_internet=cand.get("site_internet"),
                    contact_nom=cand.get("contact_nom"),
                    siret=cand.get("siret"),
                    siren=cand.get("siren"),
                    tranche_effectif=cand.get("tranche_effectif"),
                    categorie_entreprise=cand.get("categorie_entreprise"),
                    chiffre_affaires=cand.get("chiffre_affaires"),
                    score=score,
                    score_label=label,
                    score_justification=cand.get("score_justification"),
                    message_prospection=cand.get("message_prospection"),
                    source=cand.get("source"),
                    date_decouverte=date.today(),
                    fingerprint=dedup.make_fingerprint(cand.get("nom"), cand.get("ville")),
                )
                session.add(prospect)
                session.flush()  # obtient l'id + garantit la contrainte SIRET
                result.nouveaux += 1
                result.nouveaux_prospects.append(prospect.as_dict())

        session.commit()

    except Exception as exc:  # noqa: BLE001 — on journalise toute erreur
        session.rollback()
        result.erreur = str(exc)
        logger.exception("Erreur pendant la prospection")

    result.duree_secondes = round(time.perf_counter() - start, 2)

    journal = JournalRecherche(
        statut="erreur" if result.erreur else "succes",
        examines=result.examines,
        nouveaux=result.nouveaux,
        mis_a_jour=result.mis_a_jour,
        doublons=result.doublons,
        duree_secondes=result.duree_secondes,
        message=result.erreur,
    )
    session.add(journal)
    session.commit()
    result_journal_id = journal.id
    logger.info(
        "Prospection terminée (journal #%s) : %s nouveaux, %s mis à jour, %s doublons",
        result_journal_id, result.nouveaux, result.mis_a_jour, result.doublons,
    )
    return result

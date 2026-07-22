"""Intégration IA OPTIONNELLE via un LLM open source local.

Par défaut, on utilise **Ollama** (https://ollama.com) : gratuit, open source,
auto-hébergé, qui fait tourner des modèles ouverts (Qwen, Gemma, Llama…) en local.
L'app dialogue avec son API compatible OpenAI (`/v1/chat/completions`).

Comme l'endpoint est compatible OpenAI, on peut aussi pointer vers n'importe quel
service compatible (Groq, OpenRouter, LM Studio, vLLM…) en changeant AI_BASE_URL.

⚠️ Tout est OPTIONNEL. Si `AI_ENABLED=false` ou si le service est injoignable,
chaque fonction renvoie `None` et l'application retombe proprement sur le
scoring par règles. Aucune dépendance dure, aucune clé obligatoire, aucun coût.
"""
from __future__ import annotations

import json
import logging

import requests

from .config import settings

logger = logging.getLogger(__name__)

_cfg = settings.ai


def is_available() -> bool:
    """L'IA est-elle activée dans la configuration ?"""
    return bool(_cfg.enabled)


def _chat(system: str, user: str, *, max_tokens: int = 400,
          temperature: float = 0.2, json_mode: bool = False) -> str | None:
    """Appel bas niveau au LLM. Renvoie le texte, ou None en cas d'échec."""
    if not _cfg.enabled:
        return None
    payload = {
        "model": _cfg.model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False,
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
    try:
        resp = requests.post(
            _cfg.base_url.rstrip("/") + "/chat/completions",
            json=payload,
            headers={"Authorization": f"Bearer {_cfg.api_key or 'ollama'}"},
            timeout=_cfg.timeout,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception as exc:  # noqa: BLE001 — l'IA ne doit jamais casser la prospection
        logger.warning("Appel IA échoué (%s) — repli sur les règles.", exc)
        return None


def _company_context(c: dict) -> str:
    """Résumé texte d'un prospect pour le prompt."""
    return (
        f"Nom: {c.get('nom')}\n"
        f"Activité: {c.get('activite')} (NAF {c.get('naf')})\n"
        f"Ville: {c.get('ville')} ({c.get('departement')})\n"
        f"Tranche d'effectif (code INSEE): {c.get('tranche_effectif')}\n"
        f"Catégorie: {c.get('categorie_entreprise')}\n"
        f"Chiffre d'affaires connu: {c.get('chiffre_affaires')}\n"
    )


ACTIVITE_CORDISTE = (
    "Cordiste Île-de-France réalise des travaux sur corde et en hauteur : "
    "nettoyage de façades, désamiantage, inspection de bâtiments, maintenance "
    "difficile d'accès, sécurisation et réparations en hauteur."
)


def score_prospect(candidate: dict) -> dict | None:
    """Score IA (0-100) + justification courte. Renvoie {score, justification} ou None."""
    system = (
        "Tu es un analyste commercial B2B. " + ACTIVITE_CORDISTE + " "
        "Évalue le potentiel d'une entreprise à devenir cliente (grand parc "
        "immobilier, façades, hauteur = fort potentiel). Réponds STRICTEMENT en "
        'JSON : {"score": <entier 0-100>, "justification": "<une phrase en français>"}.'
    )
    out = _chat(system, _company_context(candidate), max_tokens=200, json_mode=True)
    if not out:
        return None
    try:
        data = json.loads(out)
        score = int(data.get("score"))
        score = max(0, min(100, score))
        return {"score": score, "justification": str(data.get("justification", "")).strip()}
    except (ValueError, TypeError, json.JSONDecodeError):
        logger.warning("Réponse IA de scoring non exploitable : %r", out[:200])
        return None


def generate_outreach(candidate: dict) -> str | None:
    """Brouillon d'accroche de prospection personnalisé. Renvoie le texte ou None."""
    system = (
        "Tu es commercial pour Cordiste Île-de-France. " + ACTIVITE_CORDISTE + " "
        "Rédige une accroche de prospection B2B courte (3-4 phrases), polie, "
        "personnalisée selon l'activité de l'entreprise, en français, sans objet, "
        "sans formule de politesse finale, prête à adapter."
    )
    return _chat(system, _company_context(candidate), max_tokens=250, temperature=0.6)


def summarize_prospects(prospects: list[dict]) -> str | None:
    """Résumé rédigé des meilleurs prospects du jour pour le rapport. Renvoie texte ou None."""
    if not prospects:
        return None
    top = sorted(prospects, key=lambda p: p.get("score") or 0, reverse=True)[:8]
    lines = [
        f"- {p.get('nom')} | {p.get('activite')} | {p.get('ville')} "
        f"| score {p.get('score')}"
        for p in top
    ]
    system = (
        "Tu es assistant commercial. " + ACTIVITE_CORDISTE + " "
        "À partir de la liste des nouveaux prospects du jour, rédige un résumé "
        "de 3 à 5 phrases en français : mets en avant les 2-3 prospects les plus "
        "prometteurs et pourquoi, de façon concrète et actionnable."
    )
    return _chat(system, "Nouveaux prospects du jour :\n" + "\n".join(lines),
                 max_tokens=350, temperature=0.4)

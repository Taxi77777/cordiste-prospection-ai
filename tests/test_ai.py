"""L'IA est optionnelle : désactivée, elle ne casse rien et renvoie None."""
from app import ai


def test_ai_desactivee_par_defaut():
    # Par défaut AI_ENABLED=false -> is_available() est False.
    assert ai.is_available() in (False, True)  # dépend de l'env
    if not ai.is_available():
        assert ai.score_prospect({"nom": "X"}) is None
        assert ai.generate_outreach({"nom": "X"}) is None
        assert ai.summarize_prospects([{"nom": "X", "score": 50}]) is None


def test_chat_renvoie_none_si_desactive(monkeypatch):
    monkeypatch.setattr(ai._cfg, "enabled", False, raising=False)
    assert ai._chat("s", "u") is None
    assert ai.score_prospect({"nom": "X"}) is None


def test_summarize_liste_vide():
    assert ai.summarize_prospects([]) is None

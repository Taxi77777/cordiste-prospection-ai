from app.scoring import LABEL_COLD, LABEL_HOT, LABEL_WARM, compute_score


def test_grand_gestionnaire_immobilier_est_tres_fort():
    cand = {
        "naf": "68.32A",              # gestion immobilière (base_weight 95)
        "tranche_effectif": "32",     # 250-499 salariés
        "categorie_entreprise": "ETI",
        "chiffre_affaires": 60_000_000,
        "telephone": "0143293535",
        "email": "contact@example.fr",
        "site_internet": "https://example.fr",
    }
    score, label = compute_score(cand)
    assert score >= 70
    assert label == LABEL_HOT


def test_petite_structure_est_faible():
    cand = {"naf": "68.31Z", "tranche_effectif": "00", "categorie_entreprise": "PME"}
    score, label = compute_score(cand)
    assert label in (LABEL_COLD, LABEL_WARM)
    assert score < 70


def test_secteur_inconnu_score_bas():
    score, label = compute_score({"naf": "01.11Z"})
    assert score == 0
    assert label == LABEL_COLD


def test_score_borne_a_100():
    cand = {
        "naf": "68.20B", "tranche_effectif": "53", "categorie_entreprise": "GE",
        "chiffre_affaires": 999_000_000, "telephone": "x", "email": "y", "site_internet": "z",
    }
    score, _ = compute_score(cand)
    assert 0 <= score <= 100

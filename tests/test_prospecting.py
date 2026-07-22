"""Test d'intégration : la prospection écrit en base et évite les doublons,
sans jamais appeler la vraie API (source factice)."""
from app.prospecting import run_prospection
from app.sources.base import ProspectSource


class FakeSource(ProspectSource):
    name = "fake"

    def __init__(self, items):
        self._items = items

    def fetch(self):
        yield from self._items


CAND = {
    "nom": "GRAND HOTEL DE PARIS", "activite": "Hôtel", "secteur": "hotel",
    "naf": "55.10Z", "adresse": "1 rue de Rivoli", "ville": "Paris",
    "code_postal": "75001", "departement": "75", "siret": "55510101000015",
    "siren": "555101010", "tranche_effectif": "22", "categorie_entreprise": "ETI",
    "chiffre_affaires": 12_000_000, "source": "TEST",
}


def test_ajout_nouveau_prospect(session):
    result = run_prospection(session, sources=[FakeSource([CAND])])
    assert result.nouveaux == 1
    assert result.nouveaux_prospects[0]["score_label"].startswith(("🔥", "🟠"))


def test_pas_de_doublon_deuxieme_run(session):
    run_prospection(session, sources=[FakeSource([CAND])])
    result2 = run_prospection(session, sources=[FakeSource([CAND])])
    assert result2.nouveaux == 0
    assert result2.doublons >= 1


def test_maj_si_nouvelle_info(session):
    run_prospection(session, sources=[FakeSource([CAND])])
    enriched = {**CAND, "telephone": "0143293535", "email": "contact@ghp.fr"}
    result2 = run_prospection(session, sources=[FakeSource([enriched])])
    assert result2.nouveaux == 0
    assert result2.mis_a_jour == 1


def test_filtre_hors_idf(session):
    hors = {**CAND, "siret": "99999999900019", "departement": "13", "ville": "Marseille"}
    result = run_prospection(session, sources=[FakeSource([hors])])
    assert result.nouveaux == 0

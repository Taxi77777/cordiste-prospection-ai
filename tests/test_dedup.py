from app.dedup import (
    apply_updates,
    find_existing,
    make_fingerprint,
    normalize_domain,
    normalize_phone,
)
from app.models import Prospect


def _add(session, **kw):
    kw.setdefault("fingerprint", make_fingerprint(kw.get("nom"), kw.get("ville")))
    p = Prospect(**kw)
    session.add(p)
    session.commit()
    return p


def test_normalisations():
    assert normalize_phone("+33 1 43 29 35 35") == "0143293535"
    assert normalize_domain("https://WWW.Example.fr/contact") == "example.fr"


def test_dedup_par_siret(session):
    _add(session, nom="HOTEL A", ville="Paris", siret="12345678900012")
    hit = find_existing(session, {"nom": "Autre nom", "siret": "12345678900012"})
    assert hit is not None


def test_dedup_par_empreinte_nom_ville(session):
    _add(session, nom="SCI Les Tilleuls", ville="Créteil")
    hit = find_existing(session, {"nom": "les tilleuls", "ville": "CRETEIL"})
    assert hit is not None


def test_pas_de_faux_positif(session):
    _add(session, nom="HOTEL A", ville="Paris", siret="11111111100011")
    hit = find_existing(session, {"nom": "HOTEL B", "ville": "Lyon", "siret": "22222222200022"})
    assert hit is None


def test_apply_updates_complete_les_champs_vides(session):
    p = _add(session, nom="HOTEL A", ville="Paris", siret="33333333300033")
    changed = apply_updates(p, {"telephone": "0102030405", "email": "a@b.fr"})
    assert "telephone" in changed and "email" in changed
    assert p.telephone == "0102030405"

    # Aucune modification si la donnée est identique.
    changed2 = apply_updates(p, {"telephone": "0102030405"})
    assert changed2 == []

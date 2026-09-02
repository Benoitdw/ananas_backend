"""Le fingerprint decide de ce qui est une "nouvelle offre".

S'il est instable, l'utilisateur recoit tous les jours la meme offre; s'il
collisionne, il rate des offres. Ces tests verrouillent les deux cotes.
"""

from datetime import date

from ananas.scrapers.base import JobPosting


def posting(**kwargs) -> JobPosting:
    return JobPosting(**{"title": "Data Engineer", "url": "https://acme.com/jobs/12", **kwargs})


def test_stable_entre_deux_passages():
    assert posting().fingerprint == posting().fingerprint


def test_ignore_les_parametres_de_tracking():
    """Sans ca, une URL avec ?utm_source= change tous les jours et l'offre
    parait nouvelle a chaque run."""
    a = posting(url="https://acme.com/jobs/12")
    b = posting(url="https://acme.com/jobs/12?utm_source=newsletter&ref=abc")
    assert a.fingerprint == b.fingerprint


def test_ignore_slash_final_casse_et_fragment():
    a = posting(url="https://acme.com/jobs/12")
    b = posting(url="https://ACME.com/jobs/12/#description")
    assert a.fingerprint == b.fingerprint


def test_ignore_la_casse_et_les_espaces_du_titre():
    a = posting(title="Data Engineer")
    b = posting(title="  data   engineer ")
    assert a.fingerprint == b.fingerprint


def test_deux_offres_distinctes_different():
    assert posting(url="https://acme.com/jobs/12").fingerprint != (
        posting(url="https://acme.com/jobs/13").fingerprint
    )
    assert posting(title="Data Engineer").fingerprint != posting(title="Data Analyst").fingerprint


def test_external_id_prime_sur_url_et_titre():
    """Un identifiant fourni par le site survit a une refonte des URL et a une
    reformulation du titre — c'est pourquoi il est prioritaire."""
    a = posting(external_id="uuid-42")
    b = posting(external_id="uuid-42", url="https://acme.com/careers/data-engineer", title="Autre")
    assert a.fingerprint == b.fingerprint


def test_champs_descriptifs_sans_effet():
    """Un changement de lieu ou de date ne doit pas faire renotifier."""
    a = posting()
    b = posting(location="Bruxelles", posted_at=date(2026, 1, 1), description="...")
    assert a.fingerprint == b.fingerprint


def test_offre_incomplete_rejetee():
    assert not JobPosting(title="", url="https://acme.com/jobs/1").is_valid()
    assert not JobPosting(title="Data Engineer", url="/jobs/1").is_valid()
    assert posting().is_valid()

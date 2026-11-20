"""Tri des offres de la Liste An pour un profil scientifique.

Les cas viennent d'offres reellement publiees (novembre 2026). Deux promesses:
l'evident part (technicien, informatique, vente...), et le reste passe — en
cas de doute, on garde. Les regles raisonnent par concept: plusieurs
formulations d'une meme idee doivent donner le meme resultat.
"""

from __future__ import annotations

import pytest

from ananas.liste_an import Offer, exclusion_reason


def reason(title: str, slug: str = "biotech-x", **kw) -> str | None:
    return exclusion_reason(slug, Offer(title, **kw))


@pytest.mark.parametrize(
    "title",
    [
        "Research Scientist",
        "Jr. wetenschapper – Onderzoeksproject ‘Chemische analyse van smaakstoffen’",
        "VIE scientist: Biochemistry and Biophysics",
        "Quality Assurance Manager",
        "Regulatory CMC Manager I",
        "Medical Science Liaison Parkinson",
        "Clinical Geneticist",
        "Process Engineer",
        "Technologue de laboratoire",
        "Internship in Data Governance - Quantum Project",
        # « recrutement » dans un titre scientifique n'en fait pas un poste RH
        "Technologue de laboratoire - Réserve de recrutement (H/F/X)",
    ],
)
def test_les_postes_scientifiques_passent(title):
    assert reason(title) is None


@pytest.mark.parametrize(
    "title, expected",
    [
        # meme concept, formulations differentes
        ("Technicien(ne) de Production en CDD de 6 mois", "technique / maintenance"),
        ("Technicien.ne Biomanufacturing - Media & Buffer", "technique / maintenance"),
        ("Laboratory Technician I, Genomics Services", "technique / maintenance"),
        ("Staalnemer / Technieker Milieu", "technique / maintenance"),
        ("Opérateur(rice) de Maintenance - CDD 3 mois", "technique / maintenance"),
        ("IT application Specialist", "informatique"),
        ("Technical solution architect - Data platform", "informatique"),
        ("Industrial Cyber Security Expert", "informatique"),
        ("Aankoper - Openbare aanbestedingen", "achats / logistique"),
        ("Category Buyer", "achats / logistique"),
        ("Account Manager", "commercial / marketing"),
        ("Payroll Coordinator", "administratif / finance"),
        ("Un(e) assistant(e) administratif(ve) (m/f/x)", "administratif / finance"),
        ("Talent Partner Patient Supply", "RH"),
        ("Infirmier (H/F/X) - Bloc opératoire", "soins / paramedical"),
        ("Klinisch Verpleegkundige", "soins / paramedical"),
    ],
)
def test_l_evident_est_ecarte(title, expected):
    assert reason(title) == expected


@pytest.mark.parametrize(
    "title, kept",
    [
        ("PATO-9485 - Technologue de Laboratoire- Hématologie spéciale (H/F/X)", True),
        ("Technologue de laboratoire - Anatomie Pathologique (H/F/X)", True),
        ("Coordinateur d'études cliniques - oncologie", True),
        ("Clinical Research Associate", True),
        ("PATO-9467 - Psychologue à l'unité de crise (H/F/X)", False),
        ("Radiologue sénologue", False),
        ("Pharmacien hospitalier titulaire", False),
        # le service est un labo mais le poste est des soins: le filtre general tranche
        ("Infirmier pour le service d'hématologie", False),
    ],
)
def test_hopital_uniquement_labo_ou_recherche_clinique(title, kept):
    assert (reason(title, "cliniques-universitaires-saint-luc") is None) is kept


def test_gsk_par_departement():
    keep = ["Manufacturing", "Medical and Clinical", "Quality", "Science and Technology",
            "Manufacturing Science and Technology"]
    for dep in keep:
        assert reason("Scientist", "gsk-wavre", department=dep) is None
    assert reason("Scientist", "gsk-wavre", department="Commercial") is not None
    # departement inconnu: on garde
    assert reason("Scientist", "gsk-rixensart") is None


def test_sgs_uniquement_laboratoire():
    assert reason("Analyste", "sgs-lab-simon", department="Laboratory & Testing") is None
    assert reason("Analyste", "sgs-lab-simon", department="Laboratory and Testing") is None
    assert reason("Inspecteur", "sgs-lab-simon",
                  department="Inspection and Field Testing") is not None


@pytest.mark.parametrize(
    "location, kept",
    [
        ("Rixensart, Wallonia, Belgium", True),
        ("Brussels, Brussels, Belgium", True),
        ("Bruxelles", True),
        ("Wavre, Wallonia, Belgium", True),
        ("Nazareth-De Pinte, Flanders, Belgium", False),
        (None, True),
    ],
)
def test_eurofins_par_lieu(location, kept):
    assert (reason("Scientist", "eurofins-belgium", location=location) is None) is kept


@pytest.mark.parametrize(
    "title, description, kept",
    [
        ("Associate Project Manager (Conduct) - Hybrid", "", True),
        ("Clinical Study Associate I", "Working Model: Flexible hybrid schedule (2 days onsite)", True),
        ("Program Manager", "with a 100% remote work arrangement", True),
        ("Study Manager", "Possibilite de 2 jours de teletravail par semaine", True),
        ("Study Manager", "Thuiswerk mogelijk", True),
        ("Associate Scientist", "Position type: Full time, 100% on-site", False),
        ("Associate Scientist", "This role is fully onsite in Wilrijk", False),
        # rien de dit: on garde
        ("Associate Biobank Specialist", "Join our team in Antwerp.", True),
    ],
)
def test_cellcarta_hybride_si_precise(title, description, kept):
    got = reason(title, "cellcarta", description=description)
    assert (got is None) is kept

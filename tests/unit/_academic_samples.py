"""Shared extracted-text sample and section spec for the verify_academic tests."""
from vitae.verify.academic import spec as va_spec

SECTIONS: list[va_spec.Section] = [
    {"heading": "EDUCATION", "count": 1, "undated_prefix": 0, "numbered": False},
    {"heading": "PUBLICATIONS: JOURNAL ARTICLES", "count": 2, "undated_prefix": 1, "numbered": False},
]
ACADEMIC = """\
Dupont
EDUCATION
2015-2019   Doctorat en mathématiques, Université de Montréal, dans le cadre d'une thèse sur les graphes et les
            algorithmes de coloration, sous la direction de la professeure Tremblay.
PUBLICATIONS: JOURNAL ARTICLES
Sous presse Dupont, J. Une borne pour la coloration des graphes, avec une démonstration pour les graphes planaires.
2021        Dupont, J. Sur les arbres, et sur les graphes de grande taille dans les réseaux de transport.
"""

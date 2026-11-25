"""pick_design: domain register and gutter-rail domain match word starts, not fragments."""
import pytest
import vitae.design.pick as pd
import vitae.design.tables as pd_tables


@pytest.mark.parametrize("field, want", [
    ("art director", "creative"), ("UX designer", "creative"), ("graphic design", "creative"),
    ("arts visuels", "creative"), ("marketing", "creative"),
    ("legal counsel", "conservative"), ("financial analyst", "conservative"), ("tax advisor", "conservative"),
    ("lawyer", "conservative"), ("insurance broker", "conservative"), ("public administration", "conservative"),
    ("Software engineer", None),
], ids=str)
def test_domain_register_of_a_field(field, want):
    assert pd.domain_register(field) == want


@pytest.mark.parametrize("field", ["Département de la santé", "html developer", "syntax tutor", "suite logicielle"])
def test_domain_register_ignores_a_keyword_found_only_inside_another_word(field):
    """Fragments: 'art' in Département, 'ux' in 'suite' neighbours, 'tax' in 'syntax'... none is a word start."""
    assert pd.domain_register(field) is None


def _gutter(field: str) -> bool:
    return any(pd._field_has(field, t) for t in pd_tables.GUTTER_RAIL_DOMAIN)


@pytest.mark.parametrize("field", ["ML engineer", "cybersecurity", "data scientist"])
def test_gutter_rail_domain_matches_a_word_start(field):
    assert _gutter(field)


@pytest.mark.parametrize("field", ["HTML templates", "Département de la santé", "fashion designer"])
def test_gutter_rail_domain_rejects_fragments_and_other_fields(field):
    assert not _gutter(field)

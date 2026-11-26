"""Every template against its fill target: 14 families x {resume, resume-pair-b} on 1 page, plus the 2-page variants.

The families come from vitae.design.tables.FAMILIES and templates/families (discovered in conftest, never listed here); the
fill range is FAMILIES[f]['page']['fill']. One test per template (run in parallel with `pytest -n auto`). --quick: the first 3 only.
"""
from __future__ import annotations

from collections.abc import Callable

import pytest
from harness import QUICK_TEMPLATES, ROOT, TWO_PAGE_FILL, CheckResult, Template, assert_passed, discover_templates


def test_every_family_has_its_templates() -> None:
    from vitae.design.tables import FAMILIES
    on_disk = {p.name for p in (ROOT / "templates" / "families").iterdir() if p.is_dir()}
    assert on_disk == set(FAMILIES), f"templates/families vs FAMILIES: {sorted(on_disk ^ set(FAMILIES))}"
    for fam in FAMILIES:
        for name in ("resume", "resume-pair-b"):
            assert (ROOT / "templates" / "families" / fam / f"{name}.typ").is_file(), f"{fam}/{name}.typ missing"
    two = {p.parent.name for p in (ROOT / "templates" / "families").glob("*/resume-2page.typ")}
    assert two == set(TWO_PAGE_FILL), f"resume-2page.typ without a declared fill target (or target without file): {sorted(two ^ set(TWO_PAGE_FILL))}"


def test_template(template: Template, run_template: Callable[[Template], CheckResult], quick: bool) -> None:
    if quick and discover_templates().index(template) >= QUICK_TEMPLATES:
        pytest.skip("--quick: first 3 templates only")
    assert_passed(run_template(template))

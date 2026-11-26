"""Every template against its fill target: 14 families x {resume, resume-pair-b} on 1 page, plus the 2-page variants.

The families come from vitae.design.tables.FAMILIES and templates/families (discovered in conftest, never listed here); the
fill range is FAMILIES[f]['page']['fill']. The checks run concurrently in the `template_results` fixture; each test asserts
on its own result. --quick: the first 3 only.
"""
from __future__ import annotations

import pytest
from harness import QUICK_TEMPLATES, ROOT, CheckResult, Template, assert_passed, discover_templates


def test_every_family_has_its_templates() -> None:
    from vitae.design.tables import FAMILIES
    on_disk = {p.name for p in (ROOT / "templates" / "families").iterdir() if p.is_dir()}
    assert on_disk == set(FAMILIES), f"templates/families vs FAMILIES: {sorted(on_disk ^ set(FAMILIES))}"
    for fam in FAMILIES:
        for name in ("resume", "resume-pair-b"):
            assert (ROOT / "templates" / "families" / fam / f"{name}.typ").is_file(), f"{fam}/{name}.typ missing"


def test_template(template: Template, template_results: dict[str, CheckResult], quick: bool) -> None:
    if quick and discover_templates().index(template) >= QUICK_TEMPLATES:
        pytest.skip("--quick: first 3 templates only")
    assert_passed(template_results[template.check_name])

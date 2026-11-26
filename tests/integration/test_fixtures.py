"""Spacing fixtures: render all, compare the two PDF text backends, run the gates on each. Skipped under --quick."""
from __future__ import annotations

import shutil

import pytest
from harness import ROOT, CheckResult, assert_passed

FIXTURES = sorted(p.stem for p in (ROOT / "tests" / "fixtures").glob("*.typ"))


@pytest.fixture(autouse=True)
def _not_quick(quick: bool) -> None:
    if quick:
        pytest.skip("--quick: no fixtures")


def test_fixtures_render(fixture_results: dict[str, CheckResult]) -> None:
    assert_passed(fixture_results["fixtures-render"])


def test_backends_lines(fixture_results: dict[str, CheckResult]) -> None:
    """poppler vs pypdfium2 line by line (compare_backends.py SKIPs itself, exit 0, unless both are installed)."""
    if not shutil.which("pdftotext"):
        pytest.skip("needs pdftotext")
    pytest.importorskip("pypdfium2")
    assert_passed(fixture_results["backends/lines"])


@pytest.mark.parametrize("name", FIXTURES)
def test_fixture_gates(name: str, fixture_results: dict[str, CheckResult]) -> None:
    assert_passed(fixture_results[f"gates/{name}"])

"""Spacing fixtures: render all, compare the two PDF text backends, run the gates on each. Skipped under --quick."""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from harness import ROOT, CheckResult, assert_passed, importable_isolated, run_check

FIXTURES = sorted(p.stem for p in (ROOT / "tests" / "fixtures").glob("*.typ"))


@pytest.fixture
def _not_quick(quick: bool) -> None:
    if quick:
        pytest.skip("--quick: no fixtures")


@pytest.mark.usefixtures("_not_quick")
def test_fixtures_render(fixtures_rendered: tuple[CheckResult, Path]) -> None:
    assert_passed(fixtures_rendered[0])


@pytest.mark.usefixtures("_not_quick")
def test_backends_lines(fixtures_rendered: tuple[CheckResult, Path], scratch: Path, log_dir: Path) -> None:
    """poppler vs pypdfium2 line by line (compare_backends.py SKIPs itself, exit 0, unless both are installed)."""
    if not shutil.which("pdftotext"):
        pytest.skip("needs pdftotext")
    if not importable_isolated("pypdfium2"):
        pytest.skip("needs pypdfium2 importable under python -I")
    pdfs = sorted(fixtures_rendered[1].glob("*.pdf"))
    assert pdfs, "no fixture rendered"
    assert_passed(run_check("backends/lines", [sys.executable, "-I", "tests/compare_backends.py", *pdfs], scratch, None, log_dir))


@pytest.mark.usefixtures("_not_quick")
@pytest.mark.parametrize("name", FIXTURES)
def test_fixture_gates(name: str, fixtures_rendered: tuple[CheckResult, Path], scratch: Path, log_dir: Path) -> None:
    pdf = fixtures_rendered[1] / f"{name}.pdf"
    assert pdf.is_file(), f"FAIL gates/{name} (no PDF rendered)"
    assert_passed(run_check(f"gates/{name}", [sys.executable, "-I", "scripts/verify.py", "--gates",
                                              f"tests/fixtures/{name}.typ", pdf, "--root", "."], scratch, None, log_dir))


def test_fixtures_are_generated(tmp_path: Path) -> None:
    """The committed tests/fixtures/*.typ are what gen.py produces from the current templates (byte for byte). Cheap: runs under --quick too."""
    gen = ROOT / "tests" / "fixtures" / "gen.py"
    p = subprocess.run([sys.executable, "-I", str(gen), "--out", str(tmp_path)], capture_output=True, text=True)
    assert p.returncode == 0, p.stderr
    made = sorted(f.name for f in tmp_path.glob("*.typ"))
    kept = sorted(f.name for f in (ROOT / "tests" / "fixtures").glob("*.typ"))
    assert made == kept, f"fixture set differs: only generated {sorted(set(made) - set(kept))}, only committed {sorted(set(kept) - set(made))}"
    stale = [n for n in made if (tmp_path / n).read_bytes() != (ROOT / "tests" / "fixtures" / n).read_bytes()]
    assert not stale, f"stale fixtures (run tests/fixtures/gen.py): {stale}"

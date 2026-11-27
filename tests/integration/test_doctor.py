"""`verify.py --doctor` degraded paths, simulated with a PATH of symlinks and shims.

Each case asserts the DEGRADED/BROKEN label AND at least one named skipped check. verify.py imports Pillow at load, so without
it the doctor cannot run: every test here is skipped. The grep patterns are those of the original shell checks.
"""
from __future__ import annotations

import importlib.util
import shutil
import sys
from collections.abc import Callable
from pathlib import Path

import pytest
from harness import CheckResult, doctor_env, grep, run_check, run_doctor, shim_typst, stub_typst

pytestmark = pytest.mark.skipif(importlib.util.find_spec("PIL") is None, reason="Pillow not installed")

Check = Callable[..., CheckResult]


def _have(mod: str) -> bool:
    return importlib.util.find_spec(mod) is not None


@pytest.fixture
def doc(scratch: Path, out_dir: Path, log_dir: Path) -> Callable[..., CheckResult]:
    """doc(name, tools=(), stub=None, shim=None, shim_version=...): build the simulated environment and run --doctor."""
    def _doc(name: str, tools: tuple[str, ...] = ("python3",), stub: str | None = None, stub_version: str | None = None,
             shim: list[str] | None = None, shim_version: str = "0.15.0") -> CheckResult:
        d = doctor_env(out_dir / name, tools)
        if stub:
            stub_typst(d, stub, stub_version)
        if shim is not None:
            shim_typst(d, shim, shim_version)
        return run_doctor(name, d, scratch, log_dir, stub=stub is not None)
    return _doc


def test_doctor_pip_broken(doc: Callable[..., CheckResult]) -> None:
    """The `typst` module imports but does not work: BROKEN (exit 1), not a silent "Python API available"."""
    r = doc("doctor-sim", stub="broken")
    assert r.rc == 1, f"doctor exit {r.rc}, expected 1\n{r.output}"
    assert grep(r.output, r"^BROKEN  typst"), f"no BROKEN typst line\n{r.output}"
    assert not grep(r.output, r"^OK    typst"), "typst reported OK"


def test_doctor_pip_too_old(scratch: Path, out_dir: Path, log_dir: Path) -> None:
    """Compiler without compile_with_warnings (typst-py 0.11.x): "too old", not "reinstall"."""
    d = doctor_env(out_dir / "doctor-sim-too-old", ["python3"])
    (d / "py" / "typst.py").write_text('class Compiler:\n    def __init__(self, *a, **k): pass\n'
                                       '    def compile(self, **k): return b"%PDF-1"\n__version__ = "0.11.1"\n')
    r = run_doctor("doctor-pip-too-old", d, scratch, log_dir, stub=True)
    assert r.rc == 1, f"doctor exit {r.rc}, expected 1\n{r.output}"
    assert grep(r.output, r"^BROKEN  typst.*too old"), f"no too-old line\n{r.output}"
    assert "pip install --upgrade typst==" in r.output, "no upgrade advice"
    assert "force-reinstall" not in r.output, "advises reinstall for an old wheel"


def test_doctor_pip_compile_only(doc: Callable[..., CheckResult]) -> None:
    """Compiles but has no query/eval/Fonts (old typst-py): DEGRADED, and names the skipped checks."""
    r = doc("doctor-sim-c", stub="compile-only")
    assert r.rc == 0, f"doctor exit {r.rc}, expected 0\n{r.output}"
    assert grep(r.output, r"^DEGRADED  typst"), f"no DEGRADED typst line\n{r.output}"
    assert "date adjacency" in r.output, "typst block names no skipped check"
    assert not grep(r.output, r"^OK    typst"), "typst reported OK"
    # pypdf may be absent on the host; with pypdfium2 present the backend is pdfium, not DEGRADED
    if _have("pypdf") and not _have("pypdfium2"):
        assert grep(r.output, r"^DEGRADED  pypdf"), "no DEGRADED pypdf line"
        assert "hidden-text gate" in r.output, "pypdf block names no skipped check"


def test_doctor_pip_query(doc: Callable[..., CheckResult]) -> None:
    """The stub works end to end (compile, query, eval, Fonts): typst is OK and names no skipped check."""
    r = doc("doctor-sim-q", stub="working")
    assert grep(r.output, r"^OK    typst 9\.9\.9 \(Python API: compile, query, fonts\)"), f"no OK typst Python API line\n{r.output}"
    assert not grep(r.output, r"^DEGRADED  typst"), "typst still DEGRADED"


def test_doctor_old_typst(scratch: Path, out_dir: Path, log_dir: Path) -> None:
    """typst older than 0.15 (CLI shim, then the Python stub): DEGRADED with the calibration reason."""
    d = doctor_env(out_dir / "doctor-sim-old", ["python3"])
    shim_typst(d, ["DejaVu Sans"], "0.14.0")
    r = run_doctor("doctor-old-typst", d, scratch, log_dir)
    assert grep(r.output, r"^DEGRADED  typst 0\.14\.0 \(CLI\): fill targets are calibrated on typst 0\.15"), \
        f"no DEGRADED old CLI line\n{r.output}"
    (d / "bin" / "typst").unlink()
    stub_typst(d, "working", "0.14.2")
    r = run_doctor("doctor-old-typst-py", d, scratch, log_dir, stub=True)
    assert grep(r.output, r"^DEGRADED  typst 0\.14\.2 \(Python API\): fill targets are calibrated on typst 0\.15"), \
        f"no DEGRADED old Python line\n{r.output}"
    assert "apt install typst" not in r.output, "advises apt install typst"
    assert not grep(r.output, r"^OK \(Python\)"), "OK (Python) with an old typst"


class TestPipOnly:
    """The real pip-only environment: typst-py + pypdfium2 + Pillow, no typst CLI, no poppler."""

    @pytest.fixture(autouse=True)
    def _needs(self) -> None:
        if not (_have("typst") and _have("pypdfium2")):
            pytest.skip(f"needs typst-py and pypdfium2 in {sys.executable}")

    def test_pip_full(self, doc: Callable[..., CheckResult]) -> None:
        r = doc("doctor-sim-full")
        assert r.rc == 0, f"doctor exit {r.rc}, expected 0\n{r.output}"
        assert grep(r.output, r"^OK    typst .* \(Python API: compile, query, fonts\)"), f"no OK typst Python API line\n{r.output}"
        assert grep(r.output, r"^OK    pdf: pypdfium2"), "no OK pypdfium2 line"
        assert grep(r.output, r"^OK \(Python\)"), "no OK (Python) line"
        assert not grep(r.output, r"^(DEGRADED|MISSING|BROKEN)"), f"unexpected DEGRADED/MISSING/BROKEN\n{r.output}"
        assert "--font-path" not in r.output, "advises --font-path with no CLI"

    def test_no_pypdf(self, scratch: Path, out_dir: Path, log_dir: Path) -> None:
        """Same environment without pypdf: OK (Python) must not hide the skipped tiny-text check."""
        if not _have("pypdf"):
            pytest.skip("needs pypdf to be importable (it is then hidden)")
        d = doctor_env(out_dir / "doctor-sim-nopypdf", ["python3"])
        code = ("import sys, runpy\nsys.modules['pypdf'] = None\nsys.argv = ['verify.py', '--doctor']\n"
                "runpy.run_path('scripts/verify.py', run_name='__main__')")
        r = run_check("doctor-no-pypdf", [sys.executable, "-c", code], scratch, {"PATH": str(d / "bin")}, log_dir)
        assert r.rc == 0, f"doctor exit {r.rc}, expected 0\n{r.output}"
        # the line names what the gate really skips on this backend (pdfium: tiny-text; poppler: off-page)
        want = "tiny-text" if grep(r.output, r"^OK    pdf: pypdfium2") else "off-page"
        assert grep(r.output, rf"^DEGRADED  pypdf: not installed.*{want}.*pip install 'pypdf>="), \
            f"no DEGRADED pypdf line naming {want}\n{r.output}"
        assert not grep(r.output, r"^OK \(Python\)"), "OK (Python) hides the missing pypdf"

    def test_degraded_no_ok(self, scratch: Path, out_dir: Path, log_dir: Path) -> None:
        """Any DEGRADED line (here: fonts) withholds the OK (Python) summary."""
        d = doctor_env(out_dir / "doctor-sim-degfonts", ["python3"])
        code = ("import sys; sys.path.insert(0, 'scripts')\nimport vitae.design.fonts as design_fonts\n"
                "from vitae.core.env import preflight\ndesign_fonts._fonts_available = lambda: {'DejaVu Sans'}\npreflight()")
        r = run_check("doctor-degraded-no-ok", [sys.executable, "-c", code], scratch, {"PATH": str(d / "bin")}, log_dir)
        assert grep(r.output, r"^DEGRADED  fonts"), f"no DEGRADED fonts line\n{r.output}"
        assert not grep(r.output, r"^OK \(Python\)"), "OK (Python) after a DEGRADED line"


def test_doctor_no_pdftoppm(doc: Callable[..., CheckResult]) -> None:
    """pdfinfo + pdftotext but no pdftoppm: the poppler line is DEGRADED."""
    if not all(shutil.which(t) for t in ("typst", "pdfinfo", "pdftotext")):
        pytest.skip("needs typst, pdfinfo, pdftotext on the host")
    r = doc("doctor-sim2", tools=("python3", "typst", "pdfinfo", "pdftotext"))
    assert r.rc == 0, f"doctor failed (exit {r.rc})\n{r.output}"
    assert grep(r.output, r"^DEGRADED  poppler-utils"), f"no DEGRADED poppler line\n{r.output}"
    assert "hidden-text ink check" in r.output, "no skipped check named"


def test_doctor_pdfium(doc: Callable[..., CheckResult]) -> None:
    """No poppler on PATH, pypdfium2 importable: every poppler check runs on pdfium; academic mode still needs poppler."""
    if not (shutil.which("typst") and _have("pypdfium2")):
        pytest.skip("needs typst and pypdfium2 on the host")
    r = doc("doctor-sim5", tools=("python3", "typst"))
    assert r.rc == 0, f"doctor failed (exit {r.rc})\n{r.output}"
    assert grep(r.output, r"^OK    pdf: pypdfium2 .* \(Python: text, word boxes, raster, metadata, attachments\)"), \
        f"no OK pypdfium2 line\n{r.output}"
    assert "academic mode still needs poppler" in r.output, "no academic-mode line"
    assert not grep(r.output, r"^(DEGRADED  pypdf|MISSING)"), "unexpected DEGRADED/MISSING"


def test_doctor_minimal_fonts(doc: Callable[..., CheckResult]) -> None:
    """A typst CLI whose font list has only DejaVu: the fonts line is DEGRADED and names its consequence."""
    r = doc("doctor-sim3", shim=["DejaVu Sans", "DejaVu Sans Mono"])
    assert grep(r.output, r"^DEGRADED  fonts"), f"no DEGRADED fonts line\n{r.output}"
    assert "pick_design" in r.output, "fonts block names no consequence"


def test_doctor_full_fonts(doc: Callable[..., CheckResult]) -> None:
    """A font list covering every font pick_design knows: no DEGRADED fonts line."""
    from vitae.design.tables import FONTS
    fams = sorted({f[0] for fp in FONTS.values() for f in [*fp["display"], *fp["body"], *fp.get("mono", [])]})
    r = doc("doctor-sim4", shim=fams)
    assert grep(r.output, r"^OK    fonts"), f"expected OK fonts line\n{r.output}"
    assert not grep(r.output, r"^DEGRADED  fonts"), "unexpected DEGRADED fonts"

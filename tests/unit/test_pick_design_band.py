"""--band: opt-in accent band. Text-free, so extraction is unchanged; excluded families ignore it."""
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "pick_design.py"


def init(folder, name, field, *extra):
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--name", name, "--field", field, "--market", "ca",
         "--no-font-check", "--init", str(folder), *extra], capture_output=True, text=True)


def family(name, field):
    out = subprocess.run([sys.executable, str(SCRIPT), "--name", name, "--field", field,
                          "--no-font-check"], capture_output=True, text=True).stdout
    return next(ln.split(":")[1].split()[0] for ln in out.splitlines()
                if ln.startswith("design family"))


def text(pdf, *flags):
    return subprocess.run(["pdftotext", *flags, str(pdf), "-"], capture_output=True, text=True).stdout


def build(folder):
    typst = shutil.which("typst")
    if not typst:
        pytest.skip("typst CLI not installed")
    pdf = folder / "cv.pdf"
    r = subprocess.run([typst, "compile", "--root", str(folder), str(folder / "cv.typ"), str(pdf)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return pdf


def report(*extra):
    return subprocess.run([sys.executable, str(SCRIPT), "--name", "Jane Roe", "--field", "accounting",
                           "--no-font-check", *extra], capture_output=True, text=True).stdout


def test_band_does_not_change_the_draw():
    # the report carries family, accent, fonts, marker, labels: all identical with --band
    base = report()
    assert "humanist-quiet" in base and base == report("--band")


def test_band_text_extraction_identical(tmp_path):
    if not shutil.which("pdftotext"):
        pytest.skip("pdftotext not installed")
    off, on = tmp_path / "off", tmp_path / "on"
    assert init(off, "Jane Roe", "accounting").returncode == 0
    assert init(on, "Jane Roe", "accounting", "--band").returncode == 0
    assert "#let band = true" in (on / "cv.typ").read_text(encoding="utf-8")
    assert "#let band = false" in (off / "cv.typ").read_text(encoding="utf-8")
    p_off, p_on = build(off), build(on)
    assert p_off.read_bytes() != p_on.read_bytes()          # the band is really drawn
    for flags in ((), ("-layout",)):
        assert text(p_off, *flags) == text(p_on, *flags)


def test_band_ignored_for_excluded_family(tmp_path):
    assert family("g", "software") == "color-band"
    r = init(tmp_path / "x", "g", "software", "--band")
    assert r.returncode == 0 and "--band ignored" in r.stderr and "color-band" in r.stderr
    assert "#let band = true" not in (tmp_path / "x" / "cv.typ").read_text(encoding="utf-8")

"""CLI-boundary limits (vitae.core.limits): out-of-range numeric options and oversize input files end as one error
line and exit 2 before any subprocess is spawned. Mutation-checked: an off-by-one in `int_in` fails the boundary tests,
and removing any one entry-point size check fails that entry's oversize test."""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import pytest
from vitae import fill
from vitae.core import limits
from vitae.verify import cli as verify_cli
from vitae.verify import letter
from vitae.verify.academic import cli as academic_cli


def _run(monkeypatch: pytest.MonkeyPatch, argv: list[str]) -> tuple[int, str | None]:
    monkeypatch.setattr(sys, "argv", ["verify.py", *argv])
    return verify_cli._dispatch(argv)


def _exit2(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], argv: list[str], needle: str) -> None:
    with pytest.raises(SystemExit) as e:
        _run(monkeypatch, argv)
    err = capsys.readouterr().err
    assert e.value.code == 2
    assert len(err.strip().splitlines()) == 1 and needle in err


@pytest.fixture(autouse=True)
def no_subprocess(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(*a: object, **k: object) -> subprocess.CompletedProcess[str]:
        raise AssertionError("a subprocess was spawned before the input was validated")
    monkeypatch.setattr("vitae.core.proc.subprocess.run", boom)


def _sparse(tmp_path: Path, name: str, size: int) -> str:
    p = tmp_path / name
    with open(p, "wb") as f:
        f.truncate(size)
    return str(p)


# ---- the validator factories ----------------------------------------------------------------------------------

@pytest.mark.parametrize("value, ok", [("4", False), ("5", True), ("9", True), ("10", True), ("11", False)])
def test_int_in_is_inclusive_at_both_ends(value: str, ok: bool) -> None:
    parse = limits.int_in(5, 10)
    if ok:
        assert parse(value) == int(value)
    else:
        with pytest.raises(argparse.ArgumentTypeError, match=r"5\.\.10"):
            parse(value)


def test_int_in_rejects_non_integers() -> None:
    for bad in ("abc", "", "1.5"):
        with pytest.raises(argparse.ArgumentTypeError):
            limits.int_in(0, 9)(bad)


@pytest.mark.parametrize("value, ok", [("0.09", False), ("0.1", True), ("5", True), ("5.01", False), ("nan", False), ("inf", False)])
def test_float_in_bounds_and_non_finite(value: str, ok: bool) -> None:
    parse = limits.float_in(0.1, 5.0)
    if ok:
        assert parse(value) == float(value)
    else:
        with pytest.raises(argparse.ArgumentTypeError):
            parse(value)


def test_digits_in_passes_non_digits_through_for_the_gates_own_message() -> None:
    parse = limits.digits_in(1, 100)
    assert parse("x1") == "x1" and parse("1") == "1" and parse("100") == "100"
    for bad in ("0", "101", "99999999999999999999"):
        with pytest.raises(argparse.ArgumentTypeError):
            parse(bad)


def test_check_size_boundary_and_message(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    at = _sparse(tmp_path, "at.typ", 100)
    over = _sparse(tmp_path, "over.typ", 101)
    limits.check_size(at, 100)                       # exactly the cap is accepted
    limits.check_size(str(tmp_path / "missing"), 100)   # missing: left to the caller's own error
    with pytest.raises(SystemExit) as e:
        limits.check_size(over, 100)
    err = capsys.readouterr().err
    assert e.value.code == 2 and over in err and "101" in err and "100" in err


# ---- verify.py --render --ppi ---------------------------------------------------------------------------------

@pytest.mark.parametrize("ppi", [limits.PPI_MIN, limits.PPI_MAX])
def test_ppi_bounds_are_accepted(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, ppi: int) -> None:
    # past the option parse the missing file is what stops it: exit 1 "cannot read", not the exit-2 range error
    with pytest.raises(SystemExit) as e:
        _run(monkeypatch, ["--render", str(tmp_path / "none.pdf"), "--ppi", str(ppi)])
    assert e.value.code is not None and "cannot read" in str(e.value.code)


@pytest.mark.parametrize("ppi", [limits.PPI_MIN - 1, limits.PPI_MAX + 1, "abc"])
def test_ppi_out_of_range_is_exit_2(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
                                    tmp_path: Path, ppi: int | str) -> None:
    _exit2(monkeypatch, capsys, ["--render", str(tmp_path / "none.pdf"), "--ppi", str(ppi)], "--ppi")


# ---- page and fill positionals --------------------------------------------------------------------------------

@pytest.fixture
def stub_gates(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(verify_cli, "check_cv", lambda *a, **k: (0, None))
    monkeypatch.setattr(verify_cli, "tune", lambda *a, **k: (0, None))


@pytest.mark.parametrize("pages", [limits.PAGES_MIN, limits.PAGES_MAX])
def test_pages_bounds_accepted(monkeypatch: pytest.MonkeyPatch, stub_gates: None, pages: int) -> None:
    assert _run(monkeypatch, ["cv.typ", str(pages)]) == (0, None)
    assert _run(monkeypatch, ["--tune", "cv.typ", str(pages), "90", "96"]) == (0, None)


@pytest.mark.parametrize("pages", [limits.PAGES_MIN - 1, limits.PAGES_MAX + 1])
def test_pages_out_of_range_is_exit_2(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
                                      stub_gates: None, pages: int) -> None:
    _exit2(monkeypatch, capsys, ["cv.typ", str(pages)], "expected")
    _exit2(monkeypatch, capsys, ["--tune", "cv.typ", str(pages), "90", "96"], "pages")


@pytest.mark.parametrize("fill", [limits.FILL_MIN_PCT, limits.FILL_MAX_PCT])
def test_fill_bounds_accepted(monkeypatch: pytest.MonkeyPatch, stub_gates: None, fill: int) -> None:
    assert _run(monkeypatch, ["cv.typ", "1", str(fill), str(fill)]) == (0, None)
    assert _run(monkeypatch, ["--tune", "cv.typ", "1", str(fill), str(fill)]) == (0, None)


def test_fill_above_100_is_exit_2(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
                                  stub_gates: None) -> None:
    _exit2(monkeypatch, capsys, ["cv.typ", "1", "90", "101"], "fill_max")
    _exit2(monkeypatch, capsys, ["--tune", "cv.typ", "1", "101", "102"], "fill_min")


def test_non_numeric_fill_keeps_the_gates_own_failure(monkeypatch: pytest.MonkeyPatch, stub_gates: None) -> None:
    with pytest.raises(SystemExit) as e:
        _run(monkeypatch, ["--tune", "cv.typ", "1", "x", "96"])
    assert e.value.code == 1


@pytest.mark.parametrize("lead", [limits.LEADING_MIN, limits.LEADING_MAX])
def test_leading_bounds_accepted(monkeypatch: pytest.MonkeyPatch, stub_gates: None, lead: float) -> None:
    assert _run(monkeypatch, ["--tune", "cv.typ", "1", "90", "96", str(lead), str(lead)]) == (0, None)


@pytest.mark.parametrize("lead", ["0.09", "5.01", "nan", "wide"])
def test_leading_out_of_range_is_exit_2(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
                                        stub_gates: None, lead: str) -> None:
    _exit2(monkeypatch, capsys, ["--tune", "cv.typ", "1", "90", "96", lead, "1"], "lo")


# ---- oversize inputs, rejected before any subprocess (the autouse fixture makes proc.run fail) ----------------

def test_verify_default_mode_rejects_oversize_typ(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
                                                  tmp_path: Path) -> None:
    typ = _sparse(tmp_path, "cv.typ", limits.MAX_TYP_BYTES + 1)
    _exit2(monkeypatch, capsys, [typ, "1"], typ)


def test_verify_default_mode_rejects_oversize_facts(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
                                                    tmp_path: Path) -> None:
    facts = _sparse(tmp_path, "facts.md", limits.MAX_FACTS_BYTES + 1)
    _exit2(monkeypatch, capsys, ["cv.typ", "1", "--facts", facts], facts)


def test_verify_tune_rejects_oversize_typ(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
                                          tmp_path: Path) -> None:
    typ = _sparse(tmp_path, "cv.typ", limits.MAX_TYP_BYTES + 1)
    _exit2(monkeypatch, capsys, ["--tune", typ, "1", "90", "96"], typ)


def test_verify_gates_rejects_oversize_typ_and_pdf(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
                                                   tmp_path: Path) -> None:
    big_typ = _sparse(tmp_path, "cv.typ", limits.MAX_TYP_BYTES + 1)
    big_pdf = _sparse(tmp_path, "cv.pdf", limits.MAX_PDF_BYTES + 1)
    _exit2(monkeypatch, capsys, ["--gates", big_typ, "cv.pdf"], big_typ)
    small_typ = _sparse(tmp_path, "ok.typ", 10)
    _exit2(monkeypatch, capsys, ["--gates", small_typ, big_pdf], big_pdf)


@pytest.mark.parametrize("mode", ["--render", "--text"])
def test_verify_pdf_modes_reject_oversize_pdf(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
                                              tmp_path: Path, mode: str) -> None:
    pdf = _sparse(tmp_path, "cv.pdf", limits.MAX_PDF_BYTES + 1)
    _exit2(monkeypatch, capsys, [mode, pdf], pdf)


def test_academic_rejects_oversize_typ_and_toml(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
                                                tmp_path: Path) -> None:
    typ = _sparse(tmp_path, "cv.typ", limits.MAX_TYP_BYTES + 1)
    toml = _sparse(tmp_path, "d.toml", limits.MAX_TOML_BYTES + 1)
    small = _sparse(tmp_path, "s.typ", 10)
    for args, bad in (([typ, "d.toml"], typ), ([small, toml], toml)):
        monkeypatch.setattr(sys, "argv", ["verify_academic.py", *args])
        with pytest.raises(SystemExit) as e:
            academic_cli.main()
        assert e.value.code == 2 and bad in capsys.readouterr().err


def test_letter_rejects_oversize_typ(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
                                     tmp_path: Path) -> None:
    typ = _sparse(tmp_path, "letter.typ", limits.MAX_TYP_BYTES + 1)
    monkeypatch.setattr(sys, "argv", ["verify_letter.py", typ, "Acme", "Engineer"])
    with pytest.raises(SystemExit) as e:
        letter.main()
    assert e.value.code == 2 and typ in capsys.readouterr().err


def test_measure_fill_rejects_oversize_png(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
                                           tmp_path: Path) -> None:
    png = _sparse(tmp_path, "p.png", limits.MAX_PNG_BYTES + 1)
    monkeypatch.setattr(sys, "argv", ["measure_fill.py", png])
    with pytest.raises(SystemExit) as e:
        fill.main()
    assert e.value.code == 2 and png in capsys.readouterr().err


def test_shipped_files_fit_well_inside_the_caps() -> None:
    """The caps keep the margin their comments claim (>= 50x the largest shipped file)."""
    root = Path(__file__).resolve().parents[2]
    for pattern, cap in (("*.typ", limits.MAX_TYP_BYTES), ("*.pdf", limits.MAX_PDF_BYTES), ("*.toml", limits.MAX_TOML_BYTES)):
        biggest = max(p.stat().st_size for p in (root / "templates").rglob(pattern))
        assert biggest * 50 <= cap

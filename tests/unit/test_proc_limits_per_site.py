"""Each call site passes the wall-clock limit its tool class is meant to get (vitae.core.proc constants).

`proc.run` is replaced by a recorder, every site is driven once, and the `limit` it was given is compared with the
intended constant: typst compile / query / eval -> TYPST_S; poppler tools -> POPPLER_S; `typst --version` and
`typst fonts` -> PROBE_S; the `verify.py` re-run of `--all` -> RERUN_S. Mutation-checked: RERUN_S -> PROBE_S at the
cv.py site, or POPPLER_S -> TYPST_S at one pdftoppm site, fails the matching case.
"""
from __future__ import annotations

import shutil
import subprocess
from collections.abc import Callable, Sequence
from pathlib import Path

import pytest
from vitae.core import env, proc
from vitae.verify import cv, pdf, text
from vitae.verify.academic import parse
from vitae.verify.groups import ink, query

Call = tuple[tuple[str, ...], float]
Driver = Callable[[Path], object]


def test_the_four_limits_are_distinct() -> None:
    """The per-site comparison below cannot see a swap between two equal constants."""
    assert len({proc.TYPST_S, proc.POPPLER_S, proc.PROBE_S, proc.RERUN_S}) == 4


@pytest.fixture
def calls(fake_typst: Callable[..., None], monkeypatch: pytest.MonkeyPatch) -> list[Call]:
    """The recorder, with the poppler routes and the typst CLI route forced on."""
    fake_typst(cli="0.15.2")
    recorded: list[Call] = []

    def fake_run(argv: Sequence[str], limit: float, *, name: str | None = None,
                 capture: bool = True) -> subprocess.CompletedProcess[str]:
        recorded.append((tuple(argv), limit))
        # Pages line for pdfinfo; a failing exit makes the typst query fall through to eval and the raster sites stop early
        out = "Pages: 1\n0 embedded files\n" if argv[0] in ("pdfinfo", "pdfdetach") else ""
        return subprocess.CompletedProcess(list(argv), 0 if argv[0] in ("pdfinfo", "pdfdetach") else 1, out, "")

    monkeypatch.setattr(proc, "run", fake_run)
    monkeypatch.setattr(shutil, "which", lambda name, *a, **k: f"/usr/bin/{name}")
    monkeypatch.setattr(pdf, "pdf_backend", lambda: "poppler")
    monkeypatch.setattr(pdf, "importable", lambda name: False)
    monkeypatch.setattr(text, "pdf_backend", lambda: "poppler")
    monkeypatch.setattr(ink, "pdf_backend", lambda: "poppler")
    return recorded


def _typ(tmp: Path) -> str:
    p = tmp / "cv.typ"
    p.write_text("#set page()\nhello\n", encoding="utf-8")
    return str(p)


def _pdf(tmp: Path) -> str:
    p = tmp / "cv.pdf"
    p.write_bytes(b"%PDF-1.7\n")
    return str(p)


def _check_all(tmp: Path) -> object:
    _typ(tmp)
    return cv.check_all(str(tmp))


# (id, driver, tool the site spawns: argv[0] and, when a tool has several options, the one that tells the site apart)
CASES: list[tuple[str, Driver, tuple[str, ...], float]] = [
    ("typst compile", lambda t: pdf.compile_pdf(_typ(t), str(t / "o.pdf")), ("typst", "compile"), proc.TYPST_S),
    ("typst query", lambda t: query.typst_values(_typ(t), "<x>"), ("typst", "query"), proc.TYPST_S),
    ("typst eval", lambda t: query.typst_values(_typ(t), "<x>"), ("typst", "eval"), proc.TYPST_S),
    ("pdfinfo", lambda t: pdf.pdfinfo_output(_pdf(t)), ("pdfinfo",), proc.POPPLER_S),
    ("pdftotext", lambda t: pdf.extract_text(_pdf(t), "poppler"), ("pdftotext", "plain"), proc.POPPLER_S),
    ("pdftotext -bbox", lambda t: pdf.bbox_pages(_pdf(t)), ("pdftotext", "-bbox"), proc.POPPLER_S),
    ("pdftotext -layout", lambda t: parse.extract_layout_text(_pdf(t)), ("pdftotext", "-layout"), proc.POPPLER_S),
    ("pdftoppm render_pages_png", lambda t: pdf.render_pages_png(_pdf(t), str(t)), ("pdftoppm",), proc.POPPLER_S),
    ("pdftoppm render_pages", lambda t: pdf.render_pages(_pdf(t), str(t / "out"), 50), ("pdftoppm",), proc.POPPLER_S),
    ("pdftoppm _page_rasters", lambda t: pdf._page_rasters(_pdf(t), 50), ("pdftoppm",), proc.POPPLER_S),
    ("pdftoppm ink", lambda t: ink._render_page(_pdf(t), 1), ("pdftoppm",), proc.POPPLER_S),
    ("pdfdetach", lambda t: text.check_pdf_metadata(_pdf(t)), ("pdfdetach",), proc.POPPLER_S),
    ("typst --version", lambda t: env._cli_version(), ("typst", "--version"), proc.PROBE_S),
    ("typst fonts", lambda t: env.typst_fonts(), ("typst", "fonts"), proc.PROBE_S),
    ("verify.py re-run", _check_all, ("verify.py",), proc.RERUN_S),
]


def _matches(argv: tuple[str, ...], want: tuple[str, ...]) -> bool:
    if want == ("verify.py",):
        return argv[1].endswith("verify.py")
    if want == ("pdftotext", "plain"):
        return argv[0] == "pdftotext" and argv[1] not in ("-bbox", "-layout")
    return argv[: len(want)] == want


@pytest.mark.parametrize("driver, want, limit", [c[1:] for c in CASES], ids=[c[0] for c in CASES])
def test_site_passes_its_intended_limit(calls: list[Call], tmp_path: Path, capsys: pytest.CaptureFixture[str],
                                        driver: Driver, want: tuple[str, ...], limit: float) -> None:
    driver(tmp_path)
    capsys.readouterr()
    seen = [(argv, lim) for argv, lim in calls if _matches(argv, want)]
    assert seen, f"the site never spawned {want}; recorded: {calls}"
    assert all(lim == limit for _, lim in seen), f"{want}: limits {[lim for _, lim in seen]}, intended {limit}"

"""Machine-independent bounds on what the gate costs: the processes it starts and the Python memory it holds.

Wall-clock tests flake on a loaded runner and pass on a fast one whatever the code does. Two counts do not move with the
machine: the child processes one gate run starts (counted by a Python audit hook, per tool and sub-command, so a second
`pdfinfo` of the same PDF shows up as a number) and the peak of Python-side allocations (`tracemalloc`; the children's
own memory and C buffers are outside it). The runs are the shipped swiss-grid résumé (1 page), its 2-page version and the
academic CV, each on its own copy of the templates; the verdict is not asserted (that is the job of test_templates).

An audit hook cannot be removed, so one is installed for the process and counts only inside `_measured()`.
`# current: N, target: M` marks a count above what the design needs: the bound is today's count, so it fails when a
change adds a spawn, and the day a fix lands it should be tightened to M. The probes of the Typst installation
(`typst --version`, `typst fonts`) are counted apart: they are made once per run at most.
"""
from __future__ import annotations

import contextlib
import io
import os
import shutil
import sys
import tracemalloc
from collections import Counter
from collections.abc import Generator
from dataclasses import dataclass
from pathlib import Path

import pytest
from harness import ROOT

TOOLS = ("typst", "pdftotext", "pdfinfo", "pdftoppm", "pdfdetach")
pytestmark = pytest.mark.skipif(
    not all(shutil.which(t) for t in TOOLS), reason=f"needs {', '.join(TOOLS)} on PATH (the gate's own tools)")

_EVENTS = {"subprocess.Popen", "os.posix_spawn", "os.exec"}
_SPAWNED: list[list[str]] = []     # argv of every process started while _ACTIVE
_ACTIVE: list[bool] = [False]


def _audit(event: str, args: tuple[object, ...]) -> None:
    if not _ACTIVE[0] or event not in _EVENTS:
        return
    argv = args[1]
    if isinstance(argv, (list, tuple)):
        _SPAWNED.append([str(a) for a in argv])
    else:
        _SPAWNED.append([str(args[0])])


sys.addaudithook(_audit)


def _kind(argv: list[str]) -> str:
    """`tool` or `tool sub-command` of one spawn: what the budget is counted by."""
    tool = os.path.basename(argv[0])
    if tool == "typst":
        return f"typst {argv[1]}"
    if tool == "pdftotext":
        return "pdftotext -bbox" if "-bbox" in argv else "pdftotext"
    return tool


@dataclass(frozen=True)
class Run:
    spawns: Counter[str]
    peak_kib: int


@contextlib.contextmanager
def _measured() -> Generator[None]:
    _SPAWNED.clear()
    tracemalloc.start()
    _ACTIVE[0] = True
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            yield
    finally:
        _ACTIVE[0] = False
        tracemalloc.stop()


def _gate(copy: Path, rel: str, pages: str, fill: tuple[str, str] | None) -> Run:
    from vitae.verify.cv import PageTarget, check_cv
    target = PageTarget(pages, *fill) if fill else PageTarget(pages)
    with _measured():
        check_cv(str(copy / rel), target, allow_placeholders=True)
        peak = tracemalloc.get_traced_memory()[1]
    return Run(Counter(_kind(a) for a in _SPAWNED), peak // 1024)


CASES = {
    "resume-1page": ("templates/families/swiss-grid/resume.typ", "1", ("94", "96")),
    "resume-2page": ("templates/families/swiss-grid/resume-2page.typ", "2", ("94", "96")),
    "academic": ("templates/academic/cv.typ", "2", None),
}


@pytest.fixture(scope="module")
def runs(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Run]:
    """Each case on a fresh copy, after a warm-up run on another copy, so the memory peak does not include the lazy
    imports of the first gate run in the process (which depend on what ran before) and no cache of a PDF is hit."""
    def copy(name: str) -> Path:
        d = tmp_path_factory.mktemp(name)
        shutil.copytree(ROOT / "templates", d / "templates", ignore=shutil.ignore_patterns("*.pdf", "*.png", "__pycache__"))
        return d

    rel, pages, fill = CASES["resume-1page"]
    _gate(copy("warmup"), rel, pages, fill)
    return {name: _gate(copy(name), *case) for name, case in CASES.items()}


# Budget per case: tool kind -> (target, current). Bound: target <= count <= current (the lower bound catches a gate
# that quietly stops running a check; the upper one a spawn added).
_COMMON = {
    "typst compile": (2, 2),        # the PDF, and the PNG raster of the layout check: once per deliverable and format
    "typst query": (1, 4),          # current: 4, target: 3 (`<vitae-sec>` is queried twice, query.py:98)
    "pdftotext": (1, 1),            # the reading text, once
    "pdftotext -bbox": (1, 5),      # current: 5, target: 1 (the word boxes of one PDF, pdf.py:356 called from 5 gates)
    "pdfinfo": (1, 2),              # current: 2, target: 1 (pdf.py:179 and text.py:315 ask the same question)
    "pdfdetach": (1, 1),
}
BUDGET = {
    "resume-1page": {**_COMMON, "pdftoppm": (2, 2)},           # one 150-ppi render, one 300-ppi ink page
    "resume-2page": {**_COMMON, "pdftoppm": (3, 3)},           # the ink page once per page
    "academic": {**_COMMON, "typst query": (1, 4), "pdftotext -bbox": (1, 3), "pdftoppm": (1, 1)},
}
# Peak of Python-side allocations in KiB, measured on the gate after a warm-up: bound = 2 x measured
# (1557 KiB 1 page, 2048 KiB 2 pages, 1587 KiB academic; the 2-page résumé is the largest).
PEAK_KIB = {"resume-1page": 3200, "resume-2page": 4100, "academic": 3200}


@pytest.mark.parametrize("case", CASES)
def test_spawn_count_per_tool(case: str, runs: dict[str, Run]) -> None:
    got = runs[case].spawns
    budget = BUDGET[case]
    probes = {k: v for k, v in got.items() if k in ("typst --version", "typst fonts")}
    counted = {k: v for k, v in got.items() if k not in probes}

    assert set(counted) <= set(budget), f"a tool the gate did not use before: {sorted(set(counted) - set(budget))} in {dict(got)}"
    for kind, (low, high) in budget.items():
        assert low <= counted.get(kind, 0) <= high, f"{kind}: {counted.get(kind, 0)} spawns, expected {low}..{high}; all: {dict(got)}"
    assert all(v <= 1 for v in probes.values()), f"the Typst probes run more than once: {probes}"


@pytest.mark.parametrize("case", CASES)
def test_python_memory_peak_is_bounded(case: str, runs: dict[str, Run]) -> None:
    assert runs[case].peak_kib <= PEAK_KIB[case], f"{case}: peak {runs[case].peak_kib} KiB over {PEAK_KIB[case]} KiB"


def _bullet_peak_kib(entries: int) -> float:
    """Peak of `located_bullets` on one page of `entries` entries (a head line, an org line, 3 bullets of a full line
    and a short wrapped one: the shape of tests/unit/_pages.cv_page)."""
    from vitae.core.base import HeadMark, Mark, WordBox
    from vitae.verify import runts
    marks: list[Mark] = []
    words: list[WordBox] = []
    y = 40.0
    for e in range(entries):
        marks.append(HeadMark(text=f"Role{e}", page=1, x=10.0, y=y, kind="entry", org=f"Org{e}"))
        words.append(((10.0, y, 40.0, y + 9.0), f"Role{e}"))
        y += 24.0
        for b in range(3):
            marks.append(Mark(text="•", page=1, x=18.0, y=y, kind="bullet"))
            words.extend(((30.0 + 34.0 * k, y, 60.0 + 34.0 * k, y + 9.0), f"w{e}x{b}x{k}") for k in range(12))
            words.append(((30.0, y + 12.0, 60.0, y + 21.0), f"end{e}x{b}"))
            y += 24.0
        y += 6.0
    tracemalloc.start()
    try:
        runts.located_bullets(marks, [words], [10000.0])
        return tracemalloc.get_traced_memory()[1] / 1024
    finally:
        tracemalloc.stop()


def test_bullet_layout_memory_grows_linearly() -> None:
    """Doubling a page of entries doubles the peak (measured 1.5 MiB at 100 entries, 2.9 MiB at 200: x1.9); a quadratic
    structure (a pair table of the lines) would give x4."""
    ratio = _bullet_peak_kib(200) / _bullet_peak_kib(100)

    assert ratio <= 2.5, f"peak x{ratio:.2f} when the page doubles"

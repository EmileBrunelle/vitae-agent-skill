"""The gate's output is deterministic: across processes (hash seed) and within one process (state kept between runs).

Across processes: `verify.py --json` on shipped templates under two PYTHONHASHSEED values must print byte-identical
stdout. Within a process: the same file gated twice, with another file in between (A, B, A), must report the same
thing both times, which catches an lru_cache keyed too loosely, a ContextVar left set, or a warn-once flag leaking into the report.
The output is compared raw: nothing in it varies (no timing, no temp path: the `fill:` message names the page file only).
"""
from __future__ import annotations

import io
import json
import os
import subprocess
import sys
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

import pytest
from vitae.core.env import preflight
from vitae.verify import registry
from vitae.verify.cli import _dispatch
from vitae.verify.jsonout import run_json
from vitae.verify.letter import check_letter
from vitae.verify.pdf import current_memo

pytestmark = pytest.mark.skipif(not preflight().ok, reason="needs typst and a PDF text backend")

SEEDS = ("0", "12345")
FAM = "templates/families/swiss-grid"
# (relative path, pages, fill min, fill max or None): a 1-page résumé, a 2-page résumé. (An academic CV has its own gate,
# verify_academic.py: the standard gate refuses it with exit 2.)
CVS: list[tuple[str, int, int | None, int | None]] = [
    (f"{FAM}/resume.typ", 1, 94, 96),
    (f"{FAM}/resume-2page.typ", 2, 94, 96),
]
IDS = ["resume-1page", "resume-2page"]
ACADEMIC = ["scripts/verify_academic.py", "templates/academic/cv.typ", "templates/academic/faits-academique.example.toml"]
LETTER = "templates/letter.typ"
LETTER_RUN = ("import json, sys; sys.path.insert(0, 'scripts')\n"
              "from vitae.verify.letter import check_letter\n"
              f"print(json.dumps(check_letter({LETTER!r}, 'Employer', 'Job Title', allow_placeholders=True)))\n")


def _argv(cv: tuple[str, int, int | None, int | None]) -> list[str]:
    typ, pages, lo, hi = cv
    return [typ, str(pages), *([str(lo), str(hi)] if lo is not None and hi is not None else []), "--allow-placeholders"]


def _seeded(scratch: Path, args: list[str], seed: str) -> str:
    """stdout of `python <args>` in the scratch copy under PYTHONHASHSEED=seed. Not `-I`: -I implies -E, which would ignore
    the seed; `-s` still hides the user site, so the interpreter is as isolated as the gates need."""
    env = {**os.environ, "PYTHONHASHSEED": seed}
    p = subprocess.run([sys.executable, "-s", *args], cwd=scratch, env=env, capture_output=True, text=True,
                       encoding="utf-8", stdin=subprocess.DEVNULL, check=False, timeout=600)
    assert p.returncode in (0, 1), p.stderr[-2000:]    # 0 PASS, 1 FAIL: both are a verdict; 2 is a crash
    return p.stdout


def test_seed_really_changes_hashing(scratch: Path) -> None:
    """Guard of the cross-process cases: the two seeds must give different str hashes, or they prove nothing."""
    hashes = {_seeded(scratch, ["-c", "print(hash('vitae'))"], s) for s in SEEDS}
    assert len(hashes) == len(SEEDS)


@pytest.mark.parametrize("cv", CVS, ids=IDS)
def test_json_is_identical_across_hash_seeds(scratch: Path, cv: tuple[str, int, int | None, int | None]) -> None:
    outs = [_seeded(scratch, ["scripts/verify.py", *_argv(cv), "--json"], s) for s in SEEDS]
    assert json.loads(outs[0])["verdict"] in ("PASS", "FAIL")     # a real verdict, not an ERROR object
    assert outs[0] == outs[1]


def test_academic_gate_is_identical_across_hash_seeds(scratch: Path) -> None:
    outs = [_seeded(scratch, ACADEMIC, s) for s in SEEDS]
    assert "mechanical gates: PASS" in outs[0]
    assert outs[0] == outs[1]


def test_letter_gate_is_identical_across_hash_seeds(scratch: Path) -> None:
    # the preflight prints its OK lines first (stdout): the result is the last line
    outs = [_seeded(scratch, ["-c", LETTER_RUN], s).splitlines()[-1] for s in SEEDS]
    assert json.loads(outs[0])[1]      # messages came back
    assert outs[0] == outs[1]


def _gate(argv: list[str]) -> tuple[int, str, str]:
    """One in-process `--json` gate run, as the CLI does it: (exit code, stdout, stderr)."""
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        rc, _ = run_json(argv, _dispatch)
    return rc, out.getvalue(), err.getvalue()


def test_gate_twice_in_one_process_same_report(scratch: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A, B, A: the second A must equal the first, with a different file gated in between (caches keyed on a Path)."""
    monkeypatch.chdir(scratch)
    a, b = _argv(CVS[0]), _argv(CVS[1])
    ra1 = _gate(a)
    rb = _gate(b)
    ra2 = _gate(a)
    assert json.loads(ra1[1])["verdict"] in ("PASS", "FAIL")
    assert json.loads(rb[1])["file"] != json.loads(ra1[1])["file"]
    assert ra1[0] == ra2[0]
    assert ra1[1] == ra2[1]      # the JSON report
    assert ra1[2] == ra2[2]      # and the diagnostics (stderr), so a warn-once shown only the first time would show here
    assert registry._recorder.get() is None     # the recorder ContextVar is reset after each run
    assert current_memo() is None     # the run memo is scoped to one gate run


def test_letter_gate_twice_in_one_process(scratch: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(scratch)
    first = check_letter(LETTER, "Employer", "Job Title", True)
    _gate(_argv(CVS[0]))
    assert first == check_letter(LETTER, "Employer", "Job Title", True)

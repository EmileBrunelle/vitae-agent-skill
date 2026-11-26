"""SKILL.md gates (the v0.7 context diet), ported from run_all.sh: size, orphaned steps files, dangling path citations."""
from __future__ import annotations

import re
from pathlib import Path

import pytest
from harness import ROOT

SKILL = ROOT / "SKILL.md"
LIMIT = 13000
pytestmark = pytest.mark.skipif(not SKILL.is_file(), reason="no SKILL.md in this checkout")

STEPS_DIR = ROOT / "references" / "steps"
CLEAN_END = re.compile(r"[.!?:;)\]`|*\"”»>]$")
CITATION = re.compile(r"(?:references|scripts|templates)/[A-Za-z0-9_./<>-]+")


def _steps() -> list[Path]:
    return sorted(STEPS_DIR.glob("**/*.md"))


def test_skill_size() -> None:
    n = SKILL.stat().st_size
    assert n <= LIMIT, f"SKILL.md is {n} bytes, limit is {LIMIT} ({n - LIMIT} over)"


def test_skill_steps() -> None:
    """Every steps file is cited by SKILL.md or another steps file, starts with "# ", ends like a sentence."""
    steps = _steps()
    texts = {f: f.read_text(encoding="utf-8") for f in [SKILL, *steps]}
    bad: list[str] = []
    for f in steps:
        b = f.relative_to(STEPS_DIR).as_posix()
        if not any(b in t for g, t in texts.items() if g != f):
            bad.append(f"orphan {b}: cited by neither SKILL.md nor another steps file")
        lines = [ln for ln in texts[f].split("\n") if ln.strip()]
        if not lines or not lines[0].startswith("# "):
            bad.append(f'{b}: does not start with an H1 ("# ")')
        elif not CLEAN_END.search(lines[-1].rstrip()):
            bad.append(f"{b}: last line does not end like a sentence: ...{lines[-1].rstrip()[-40:]!r}")
    assert not bad, "\n".join(bad)


def test_skill_links() -> None:
    """Every references|scripts|templates path cited in SKILL.md, the steps files, academic-mode and known-traps exists
    (paths with "<" or ">" are placeholders)."""
    srcs = [SKILL, *_steps(), *(ROOT / "references" / f for f in ("academic-mode.md", "known-traps.md"))]
    bad: set[str] = set()
    for f in srcs:
        if not f.is_file():
            continue
        for m in CITATION.finditer(f.read_text(encoding="utf-8")):
            p = m.group(0).rstrip(".,;:`')")
            if "<" in p or ">" in p:
                continue
            full = ROOT / p
            if not (full.is_dir() if p.endswith("/") else full.exists()):
                bad.add(f"missing {p} (cited in {f.relative_to(ROOT)})")
    assert not bad, "\n".join(sorted(bad))

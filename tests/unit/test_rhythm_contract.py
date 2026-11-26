"""Rhythm convention (references/design/core.md): each CV template and fixture carries one column-0
`#let rhythm = <number>`; an inter-block vertical gap is written `Npt * rhythm` (pt or em); a negative
value (a font-metric compensation) is never scaled. A static scan, so a new gap that forgets the factor
(the tuner then cannot stretch it) or a compensation that gets one (the header tightens as rhythm grows)
fails here instead of in a rendered PDF."""
import re
from pathlib import Path

import pytest
from _paths import ROOT

pytestmark = pytest.mark.lint

CV_FILES = sorted([*(ROOT / "templates/families").glob("*/*.typ"), ROOT / "templates/resume.typ",
                   ROOT / "templates/academic/cv.typ", *(ROOT / "tests/fixtures").glob("*.typ")])
RHYTHM_LINE = re.compile(r"^#let rhythm = \d+(\.\d+)?[ \t]*(//.*)?$")
NUM = re.compile(r"(?<![\w.])(\d+(?:\.\d+)?|\.\d+)(pt|em)\b")
# Calls whose positional arguments are scaled by `rhythm:` inside lib.typ (entry multiplies above/below itself).
SCALING_CALLS = ("entry", "wd-entry")
# (file name, slot, expression) -> reason. Keep it empty unless a gap truly cannot be scaled.
ALLOW: dict[tuple[str, str, str], str] = {}


def _strip_comments(text: str) -> str:
    return re.sub(r"(?m)(?<!:)//.*$", lambda m: " " * len(m.group()), text)


def _span(text: str, start: int) -> tuple[str, int]:
    """Expression starting at `start` up to the first top-level `,` or unmatched `)`."""
    depth = 0
    for i in range(start, len(text)):
        c = text[i]
        if c in "([{":
            depth += 1
        elif c in ")]}":
            if depth == 0:
                return text[start:i], i
            depth -= 1
        elif c == "," and depth == 0:
            return text[start:i], i
    return text[start:], len(text)


def _enclosing_call(text: str, pos: int) -> tuple[str, str]:
    """(name, full text) of the call whose argument list contains `pos`."""
    depth = 0
    for i in range(pos - 1, -1, -1):
        c = text[i]
        if c in ")]}":
            depth += 1
        elif c in "([{":
            if depth == 0:
                m = re.search(r"([\w-]+)$", text[:i])
                end = text.find(")", i)
                depth2 = 0
                for j in range(i, len(text)):
                    depth2 += text[j] in "([{"
                    depth2 -= text[j] in ")]}"
                    if depth2 == 0:
                        end = j
                        break
                return (m.group(1) if m and c == "(" else ""), text[i:end]
            depth -= 1
    return "", ""


SLOT = re.compile(r"\b(above|below|brk-gap|row-gutter|top|bottom)\s*:\s*|\bv\(")


def scan(text: str) -> list[tuple[str, str, str]]:
    """Violations as (slot, expression, problem)."""
    text = _strip_comments(text)
    found = []
    for m in SLOT.finditer(text):
        slot = m.group(1) or "v("
        call, call_text = _enclosing_call(text, m.start() if slot != "v(" else m.end())
        if slot in ("top", "bottom") and call != "pad":
            continue
        expr = _span(text, m.end())[0]
        if slot != "v(" and call in SCALING_CALLS and re.search(r"\brhythm:\s*rhythm\b", call_text):
            continue
        expr = " ".join(expr.split())
        lits = [(m2.start(), float(m2.group(1))) for m2 in NUM.finditer(expr)]
        if not any(v for _, v in lits):
            continue
        negative = expr.startswith("-")
        scaled = bool(re.search(r"\*\s*rhythm\b", expr))
        if negative and scaled:
            found.append((slot, expr, "negative compensation must not be scaled by rhythm"))
        elif not negative and not scaled:
            found.append((slot, expr, "inter-block gap must be multiplied by rhythm"))
    return found


@pytest.mark.parametrize("path", CV_FILES, ids=lambda p: str(p.relative_to(ROOT)))
def test_one_column_zero_rhythm_line(path: Path):
    lines = [ln for ln in path.read_text().splitlines() if re.match(r"#let rhythm\b", ln)]
    assert len(lines) == 1, f"{path.name}: expected exactly one column-0 `#let rhythm`, found {len(lines)}"
    assert RHYTHM_LINE.match(lines[0]), f"{path.name}: rhythm line must be `#let rhythm = <number>`: {lines[0]!r}"


@pytest.mark.parametrize("path", CV_FILES, ids=lambda p: str(p.relative_to(ROOT)))
def test_gaps_follow_the_rhythm_convention(path: Path):
    bad = [f"{slot}: {expr} -> {why}" for slot, expr, why in scan(path.read_text())
           if (path.name, slot, expr) not in ALLOW]
    assert not bad, f"{path.relative_to(ROOT)}:\n  " + "\n  ".join(bad)


def test_the_scan_catches_the_two_mistakes_and_spares_the_rest():
    assert scan("#v(4pt)")                                   # gap forgot the factor
    assert scan("#block(above: 0.86em)")                     # em gap too
    assert scan("#pad(bottom: 3pt, x)")                      # pad gap too
    assert scan("#v(-3pt * rhythm)")                         # compensation scaled
    assert not scan("#v(4pt * rhythm)")
    assert not scan("#v(-3pt)")
    assert not scan("#v(0pt)")
    assert not scan("#block(above: 0pt, below: 0pt, body)")
    assert not scan("#set block(above: auto)")
    assert not scan("// #v(4pt)")
    assert not scan("#block(inset: (bottom: 4pt), x)")       # an inset is not a gap
    assert not scan("#let job(r) = entry(r, above: 11pt, rhythm: rhythm)")   # entry scales it itself
    assert scan("#let job(r) = entry(r, above: 11pt)")        # without rhythm: rhythm it does not

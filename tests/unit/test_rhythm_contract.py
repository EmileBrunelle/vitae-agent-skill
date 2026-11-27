"""Rhythm convention (references/design/core.md): each CV template and fixture carries one column-0
`#let rhythm = <number>`; an inter-block vertical gap is written `Npt * rhythm` (pt or em); a negative
value (a font-metric compensation) is never scaled. A static scan, so a new gap that forgets the factor
(the tuner then cannot stretch it) or a compensation that gets one (the header tightens as rhythm grows)
fails here instead of in a rendered PDF."""
import re
from pathlib import Path

import pytest
from _paths import ROOT
from vitae.core.typst_source import strip_typst_comments

pytestmark = pytest.mark.lint

CV_FILES = sorted([*(ROOT / "templates/families").glob("*/*.typ"), ROOT / "templates/resume.typ",
                   ROOT / "templates/academic/cv.typ", *(ROOT / "tests/fixtures").glob("*.typ")])
RHYTHM_LINE = re.compile(r"^#let rhythm = \d+(\.\d+)?[ \t]*(//.*)?$")
NUM = re.compile(r"(?<![\w.])(\d+(?:\.\d+)?|\.\d+)(pt|em|mm|cm|in)\b")
# `rhythm` as a whole identifier: Typst identifiers allow `-`, so `rhythm-x` is another name.
RHY = r"(?<![\w-])rhythm(?![\w-])"
SCALED = re.compile(r"\*\s*" + RHY + "|" + RHY + r"\s*\*")
ENTRY_CALL = re.compile(r"(?<![\w-])(?:entry|wd-entry)\(")
PASSES_RHYTHM = re.compile(r"(?<![\w-])rhythm:\s*rhythm(?![\w-])")
# Calls whose positional arguments are scaled by `rhythm:` inside lib.typ (entry multiplies above/below itself).
SCALING_CALLS = ("entry", "wd-entry")
# (file name, slot, expression) -> reason. Keep it empty unless a gap truly cannot be scaled.
ALLOW: dict[tuple[str, str, str], str] = {}


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


def _split_top(expr: str, seps: str) -> list[tuple[str, str]]:
    """(separator before, piece) pairs of `expr` cut at top-level characters of `seps` (the first piece has
    separator ""); a `+`/`-` right after an operator, `(` or the start is a sign, not a cut."""
    out: list[tuple[str, str]] = []
    depth, last, sep = 0, 0, ""
    for i, c in enumerate(expr):
        if c in "([{":
            depth += 1
        elif c in ")]}":
            depth -= 1
        elif depth == 0 and c in seps:
            if c == "-" and expr[i - 1:i].isalnum() and expr[i + 1:i + 2].isalpha():
                continue          # `rhythm-x`: a Typst identifier, not a subtraction
            if c in "+-" and not expr[last:i].strip():
                continue          # unary sign: nothing before it in this piece
            if c in "+-" and expr[last:i].rstrip()[-1:] in "*/":
                continue          # `2pt * -1`: the sign of a factor
            out.append((sep, expr[last:i]))
            sep, last = c, i + 1
    out.append((sep, expr[last:]))
    return out


def _paren_inner(term: str) -> str | None:
    """The inside of `( ... )` when the parentheses wrap the whole term, else None."""
    if not (term.startswith("(") and term.endswith(")")):
        return None
    depth = 0
    for i, c in enumerate(term):
        depth += c in "([{"
        depth -= c in ")]}"
        if depth == 0 and i < len(term) - 1:
            return None
    return term[1:-1]


def _check_terms(expr: str, positive: bool, slot: str, whole: str, found: list[tuple[str, str, str]]) -> None:
    """Classify each additive term of `expr` by its own sign: a positive length must carry the rhythm
    factor (or sit in parentheses multiplied by it), a negative one (a font-metric compensation) must not."""
    for sep, piece in _split_top(expr, "+-"):
        term = piece.strip()
        sign = positive if sep != "-" else not positive
        while term[:1] in ("+", "-"):                       # unary signs
            sign = sign if term[0] == "+" else not sign
            term = term[1:].strip()
        inner = _paren_inner(term)
        if inner is not None:                               # a group not multiplied by rhythm: look inside
            _check_terms(inner, sign, slot, whole, found)
            continue
        if not any(float(m.group(1)) for m in NUM.finditer(term)):
            continue
        scaled = bool(SCALED.search(term))
        if not sign and scaled:
            found.append((slot, whole, "negative compensation must not be scaled by rhythm"))
        elif sign and not scaled:
            found.append((slot, whole, "inter-block gap must be multiplied by rhythm"))


def _call_args(text: str, start: int) -> list[str]:
    """Top-level arguments of the call whose `(` ends just before `start`."""
    end = _span_to_close(text, start)
    return [a for _, a in _split_top(text[start:end], ",") if a.strip()]


def _span_to_close(text: str, start: int) -> int:
    depth = 0
    for i in range(start, len(text)):
        if text[i] in "([{":
            depth += 1
        elif text[i] in ")]}":
            if depth == 0:
                return i
            depth -= 1
    return len(text)


def scan(text: str) -> list[tuple[str, str, str]]:
    """Violations as (slot, expression, problem)."""
    text = strip_typst_comments(text)
    found: list[tuple[str, str, str]] = []
    for m in SLOT.finditer(text):
        slot = m.group(1) or "v("
        call, call_text = _enclosing_call(text, m.start() if slot != "v(" else m.end())
        if slot in ("top", "bottom") and call != "pad":
            continue
        if slot in ("above", "below") and call in SCALING_CALLS and PASSES_RHYTHM.search(call_text):
            continue                    # entry multiplies its own above/below (the other slots are scanned)
        if slot == "v(":                # every positional / named length in the call: `#v(weak: true, 4pt)`
            exprs = [a.split(":", 1)[-1] if re.match(r"\s*[\w-]+\s*:", a) else a for a in _call_args(text, m.end())]
        else:
            exprs = [_span(text, m.end())[0]]
        for expr in exprs:
            expr = " ".join(expr.split())
            _check_terms(expr, True, slot, expr, found)
    for m in ENTRY_CALL.finditer(text):
        if text[:m.start()].rstrip().endswith("#let") or re.search(r"#let\s+$", text[:m.start()]):
            continue                    # the definition, not a call
        end = _span_to_close(text, m.end())
        if not PASSES_RHYTHM.search(text[m.end():end]):
            found.append(("entry(", " ".join(text[m.end():end].split())[:60], "entry call must pass `rhythm: rhythm`"))
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


@pytest.mark.parametrize("src", [
    "#v(weak: true, 4pt)",                                    # the length is not the first argument
    "#v(4pt * rhythm, weak: true)" + "#v(1pt)",               # one good call does not excuse the next
    "#v(2pt * rhythm + 1pt)",                                 # a sum: every positive term is scaled
    "#v(-3pt + 10pt)",                                        # classified by term, not by the first sign
    "#v(4mm)", "#v(1cm)", "#v(0.1in)",                        # other length units
    "#v(4pt * rhythm-x)", "#v(4pt) // x\n#block(above: 4pt, below: 4pt * rhythm-x)",   # rhythm-x is not rhythm
    "#entry(a, b, rhythm: rhythm-x)",                         # nor is it the pass-through
    "#let job(r) = entry(r, above: 11pt, rhythm: rhythm-x)",
    "#entry(a, b)",                                           # an entry call must pass rhythm: rhythm
    "#wd-entry(a, below: 0pt)",
    "#entry(a, above: 3pt * rhythm, rhythm: rhythm, body: block(above: 5pt))",   # other slots stay scanned
    "#v((2pt * rhythm + 1pt))",                               # parentheses do not hide a bare term
])
def test_scan_catches_the_holes(src):
    assert scan(src), src


@pytest.mark.parametrize("src", [
    "#v(weak: true, 4pt * rhythm)", "#v(2pt * rhythm + 1pt * rhythm)", "#v((2pt + 1pt) * rhythm)",
    "#v(rhythm * 4mm)", "#v(-3pt - 1pt)", "#v(-3pt + 3pt * rhythm)", "#v(1cm * rhythm - 3pt)",
    "#v(0pt + 0.5in * rhythm)", "#entry(a, b, rhythm: rhythm)", "#wd-entry(a, rhythm: rhythm)",
    "#let entry(a) = block(a)",
])
def test_scan_spares_the_correct_forms(src):
    assert not scan(src), (src, scan(src))


@pytest.mark.parametrize("path", CV_FILES, ids=lambda p: str(p.relative_to(ROOT)))
def test_every_entry_call_passes_the_rhythm(path: Path):
    bad = [e for slot, e, _ in scan(path.read_text()) if slot == "entry("]
    assert not bad, f"{path.name}: {bad}"

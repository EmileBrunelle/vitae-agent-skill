"""Font handling, separated from the checks that use it: which families a CV asks for and
which face a PDF character was drawn in.

Pure text in, values out: `requested_families` reads Typst source and returns family keys;
`classify_font_fallback` compares (character, PDF font) pairs against those keys and returns
the findings. Nothing here opens a PDF, compiles or prints; verify.py owns the gate that
feeds the PDF's characters in, and imports these names explicitly. This module never imports
verify, and keeps no module state beyond compiled regular expressions and constants.
"""
from __future__ import annotations

import os
import re
import unicodedata
from collections import Counter
from collections.abc import Sequence

from verify_level import Level

# Finding repeats verify.py's definition of the same name, written out structurally, because verify.py cannot
# be imported here: it runs as __main__, so `import verify` would execute that script a second time under the
# name `verify`. Level lives in verify_level.py (no verify import) and is shared. Keep the (level, message)
# tuple in sync by hand.
Finding = tuple[Level, str]


# A family that EXISTS but lacks the glyphs (fontsource's `*-latin-ext-*` files carry the
# family name and no basic Latin and shadow the `*-latin-*` ones) draws the text in whatever
# face Typst finds next, usually its bundled Libertinus Serif, WITHOUT a warning. The PDF is
# the only witness: pdfium reports the font of every character.
# A character is "fallen back" when the PDF font's family is named by no `font:` expression
# of the CV sources (cv.typ and the local files it imports). FAIL when an ASCII letter or digit
# fell back, or when more than FONT_FALLBACK_SHARE of the Latin letters and digits did. WARN for
# accented letters and punctuation, other scripts, and Latin text in a later bundled member of
# the font tuple; INFO for symbols and emoji (see classify_font_fallback).
# Calibration of the gate (CHANGELOG, font-fallback entry): zero FAIL and zero WARN on all shipped
# templates and on the 57 past run outputs that compile.
FONT_FALLBACK_SHARE = 0.05
# What Typst draws with when the sources name no font; used as the request in that case.
TYPST_DEFAULT_FAMILIES = ("Libertinus Serif", "New Computer Modern", "DejaVu Sans Mono")   # PDF: LibertinusSerif, NewCM10, DejaVuSansMono
# Words that may follow a family name in a PDF base-font name without making it another family: weights, slants,
# widths, "Pro"/"Std", and optical sizes ("96pt"). "mono" is absent on purpose: NotoSansMono is not Noto Sans.
# A face whose style word is missing from this list reads as another family, so add the word rather than the family.
_FONT_STYLE_RE = re.compile(r"^(?:\d+|pt|variable|regular|roman|book|medium|semibold|bold|extrabold|black|heavy|"
                            r"thin|light|extralight|italic|oblique|condensed|semicondensed|cond|narrow|display|text|"
                            r"psmt|mt|vf|upright|pro|std|semi|demi|ultra|extra)*$")
# Typst's bundled faces, as the _fam_key form of the start of their PDF base-font names
BUNDLED_KEYS = ("libertinus", "newcm", "dejavusansmono")


def _fam_key(name: str) -> str:
    """Lowercase letters and digits only: the form in which family names and PDF font names are compared."""
    return re.sub(r"[^a-z0-9]", "", name.lower())


def _family_requested(psname: str, requested: set[str]) -> bool:
    """Loose match of a PDF base-font name (`ABCDEF+NotoSans-Medium`, `Adwaita-Mono-Bold`)
    against the requested family keys: the name with its hyphens dropped starts with the
    family and only style words follow (`notosansmedium`), or the family is the name's first
    segment plus an optical size (`bricolagegrotesque96pt` asked, `BricolageGrotesque-Regular`
    drawn). `NotoSansMono` is not `Noto Sans`: `mono` is not a style word."""
    name = re.sub(r"^[A-Z]{6}\+", "", psname)
    full = _fam_key(name)
    first = _fam_key(name.split("-")[0])
    for r in requested:
        if full.startswith(r) and _FONT_STYLE_RE.match(full[len(r):]):
            return True
        if r.startswith(first) and _FONT_STYLE_RE.match(r[len(first):]):
            return True
    return False


def _font_sources(typ: str, root: str | None = None, seen: set[str] | None = None) -> str:
    """The text of the CV source and of every local .typ it imports or includes ("" for a file that cannot be read).
    `@preview/...` packages are not followed. A path starting with "/" is resolved from `root`, Typst's project root,
    when one is given; `seen` breaks import cycles."""
    seen = set() if seen is None else seen
    path = os.path.realpath(typ)
    if path in seen or len(seen) > 20:
        return ""
    seen.add(path)
    try:
        text = open(path, encoding="utf-8").read()
    except OSError:
        return ""
    out = [text]
    for m in re.finditer(r'#(?:import|include)\s+"([^"@]+\.typ)"', text):
        rel = m.group(1)
        base = os.path.realpath(root) if rel.startswith("/") and root else os.path.dirname(path)
        out.append(_font_sources(os.path.join(base, rel.lstrip("/")), root, seen))
    return "\n".join(out)


def _font_value(src: str, pos: int) -> str:
    """The expression at `pos`: a quoted string, a balanced (...) tuple, or an identifier."""
    m = re.compile(r"\s*").match(src, pos)
    pos = m.end() if m else pos
    if src.startswith("(", pos):
        depth = 0
        for k in range(pos, min(len(src), pos + 600)):
            depth += src[k] == "("
            depth -= src[k] == ")"
            if depth == 0:
                return src[pos:k + 1]
        return src[pos:pos + 600]
    m = re.compile(r'"[^"\n]*"|[A-Za-z_][\w-]*').match(src, pos)
    return m.group(0) if m else ""


def requested_families(src: str, firsts: set[str] | None = None) -> set[str]:
    """Family keys the sources ask for: the value of every `font:` argument (a string, a tuple
    of strings and variables, or a variable, resolved through `#let name = value` chains), plus
    every `#let ...font.../...f` variable holding strings (lib helpers take them as arguments).
    Comments are skipped. `firsts` (optional, filled in) gets the keys that are the FIRST member
    of a tuple, or asked alone. With math in the source (`$`) the math faces count as asked;
    "New Computer Modern" also covers the PDF name `NewCM10`."""
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    src = "\n".join(re.sub(r"(?:^|\s)//.*$", "", ln) for ln in src.splitlines())
    lets = {m.group(1): _font_value(src, m.end()) for m in re.finditer(r"#let\s+([A-Za-z_][\w-]*)\s*=", src)}
    names: set[str] = set()
    first: set[str] = set()
    seen: set[str] = set()

    def take(value: str, is_first: bool = True) -> None:
        for n, (lit, ident) in enumerate(re.findall(r'"([^"\\]{2,60})"|([A-Za-z_][\w-]*)', value)):
            lead = is_first and n == 0
            if lit:
                names.add(_fam_key(lit))
                if lead:
                    first.add(_fam_key(lit))
            elif ident in lets and ident not in seen:
                seen.add(ident)
                take(lets[ident], lead)
    for m in re.finditer(r"\bfont\s*:", src):
        take(_font_value(src, m.end()))
    for k, v in lets.items():
        if re.search(r"font|face|\wf$", k) and v.startswith(("(", '"')) and k not in seen:
            take(v)
    names.discard("")
    if not names:                       # nothing asked for: Typst's own defaults are the request
        names.update(_fam_key(x) for x in TYPST_DEFAULT_FAMILIES)
        first.update(names)
    # Raw text (backticks, #raw) is set in Typst's monospace default.
    if re.search(r"`|#raw\b|\braw\(", src):
        names.add(_fam_key("DejaVu Sans Mono"))
        first.add(_fam_key("DejaVu Sans Mono"))
    if "newcomputermodern" in names:
        names.add("newcm")
        if "newcomputermodern" in first:
            first.add("newcm")
    # Math is typeset in a math face that Typst picks itself, so these are legitimate without being asked for.
    if "$" in src:
        names.update(("newcmmath", "libertinusmath", "stixtwomath", "notosansmath"))
    if firsts is not None:
        firsts.update(first)
    return names


def _char_kind(c: str) -> str:
    """`skip` (marks, controls, separators), `sym` (symbols and emoji), `latin` (Latin-script
    letters and digits), `other` (any other script, punctuation)."""
    cat = unicodedata.category(c)
    if cat[0] in "MCZ":
        return "skip"
    if cat[0] == "S":
        return "sym"
    if c.isascii() and c.isalnum():
        return "latin"
    if cat[0] == "L" and unicodedata.name(c, "").startswith("LATIN"):
        return "latin"
    return "other"


def classify_font_fallback(chars: Sequence[tuple[str, str]], req: set[str],
                           firsts: set[str] | None = None) -> list[Finding]:
    """Findings for [(character, PDF font name)] against the requested family keys.
    FAIL: a Latin-script letter or digit left the requested families and it is an ASCII one, or
    over FONT_FALLBACK_SHARE of the Latin letters did (other scripts and symbols never count).
    WARN: accented Latin letters or punctuation fell back; letters of another script (CJK,
    Cyrillic, Greek...) fell back (add a face for that script to the font tuple); Latin letters
    sit in a Typst bundled face that is not the FIRST member of the requested tuple (the first
    face was not used, `firsts` given). INFO: symbols and emoji only (unicode category S*)."""
    pretty = ", ".join(sorted(req))
    kinds = [(c, f, _char_kind(c)) for c, f in chars]
    latin_total = sum(1 for _, f, k in kinds if f and k == "latin")
    bad = [(c, f, k) for c, f, k in kinds if f and k != "skip" and not _family_requested(f, req)]

    def fam_of(rows: Sequence[tuple[str, str, str]]) -> str:
        fams = Counter(re.sub(r"^[A-Z]{6}\+", "", f).split("-")[0] for _, f, _ in rows)
        return ", ".join(f"{n} ({k})" for n, k in fams.most_common(3))

    def sample(rows: Sequence[tuple[str, str, str]]) -> str:
        return "".join(dict.fromkeys(c for c, _, _ in rows))[:20]
    out: list[Finding] = []
    latin = [r for r in bad if r[2] == "latin"]
    ascii_n = sum(1 for c, _, _ in latin if c.isascii())
    share = len(latin) / max(1, latin_total)
    if ascii_n or share > FONT_FALLBACK_SHARE:
        out.append((Level.FAIL, f"font fallback: {len(latin)} of {latin_total} Latin letters/digits ({ascii_n} ASCII, "
                            f"{share:.0%}) are drawn in {fam_of(latin)}, not in the requested families ({pretty}); "
                            f"sample \"{sample(latin)}\". Typst falls back SILENTLY when a family exists without the "
                            "glyphs: a font file missing the basic Latin range, or subset files shadowing the real ones "
                            "(fontsource `*-latin-ext-*`); see references/fonts.md"))
    elif latin:
        out.append((Level.WARN, f"font fallback: {len(latin)} accented letter(s) \"{sample(latin)}\" drawn in {fam_of(latin)}, "
                            f"not in the requested families ({pretty}); the face lacks them: swap the face "
                            "or the character, see references/fonts.md"))
    other = [r for r in bad if r[2] == "other"]
    if other:
        out.append((Level.WARN, f"font fallback: {len(other)} character(s) \"{sample(other)}\" (another script or punctuation) "
                            f"drawn in {fam_of(other)}, not in the requested families ({pretty}); add a face for that "
                            "script to the font tuple (e.g. Noto Sans CJK JP for Japanese, a Cyrillic-capable face "
                            "for Russian) so the choice is yours, not Typst's"))
    if firsts and not latin:
        late = [(c, f, k) for c, f, k in kinds if f and k == "latin" and _family_requested(f, req)
                and _fam_key(re.sub(r"^[A-Z]{6}\+", "", f)).startswith(BUNDLED_KEYS)
                and "math" not in f.lower() and not _family_requested(f, firsts)]
        if late:
            out.append((Level.WARN, f"font fallback: {len(late)} Latin letter(s) drawn in {fam_of(late)}, a member of the font "
                                f"tuple but not its first; the first face ({', '.join(sorted(firsts))}) was not used. "
                                "Missing or without Latin glyphs? see references/fonts.md"))
    syms = [r for r in bad if r[2] == "sym"]
    if syms:
        out.append((Level.INFO, f"font fallback: {len(syms)} symbol(s) \"{sample(syms)}\" drawn in {fam_of(syms)}, outside the "
                            "requested families; the body face lacks the glyph, harmless"))
    return out

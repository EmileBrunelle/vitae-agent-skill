"""Script helpers of verify.py, kept apart from its logic: `_is_latin`, `_strip_latin_marks` (they read a script, not a
language).
The scripts know no language: no month name, degree word, section title, place word, stop word or name suffix lives in
this package, and none is to be added.

Boundary: this module never imports verify and never prints, and holds no state. Parsing of cv.typ lives in
verify_typst.py.
"""
from __future__ import annotations

import unicodedata


def _script_name(ch: str) -> str:
    """First word of the Unicode name of a letter: LATIN, CYRILLIC, GREEK, ARABIC, CJK, THAI ..."""
    try:
        return unicodedata.name(ch).split()[0]
    except ValueError:
        return ""


def _is_latin(c: str) -> bool:
    return ord(c) < 0x250 or 0x1E00 <= ord(c) < 0x1F00 or _script_name(c) == "LATIN"


def _strip_latin_marks(s: str) -> str:
    """NFKD, then drop the combining marks that sit on a LATIN base letter (é -> e). Marks on any other script stay:
    they are the vowels and tones of Devanagari, Thai, Hebrew and Arabic, and part of the letter in й or ё."""
    out: list[str] = []
    latin = True
    for c in unicodedata.normalize("NFKD", s):
        if unicodedata.combining(c):
            if latin:
                continue
        else:
            latin = _is_latin(c)
        out.append(c)
    return "".join(out)

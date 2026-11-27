"""rhythm.py `_separated` as it was before the LOG320 worst-case sweep, kept verbatim as the oracle of the equivalence
test (tests/unit/test_rhythm_complexity.py): every mark filtered again for every pair of bullets. Not imported by the
product."""
from vitae.core.base import HeadMark, Mark, Pos, is_placed
from vitae.verify.rhythm import _MARK_REACH


def separated_filtering(marks: list[Mark], a: Pos, b: Pos, lo: float, hi: float) -> bool:
    heads: list[HeadMark] = [m for m in marks if is_placed(m) and m.get("kind") != "bullet"]
    return any(m["page"] == a.page and a.y < m["y"] < b.y and lo - _MARK_REACH <= m["x"] <= hi for m in heads)

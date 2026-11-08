"""verify.py --selftest: First word, comment stripping, forced line break, duplicate names, bullet characters"""

from __future__ import annotations

from vitae.core.base import Mark
from vitae.verify.groups import (
    _first_word,
    check_date_adjacency,
    check_duplicate_names,
)
from vitae.verify.source import check_forced_linebreak, check_literal_tilde
from vitae.verify.text import check_bullet_chars
from vitae.verify.typst import _strip_typst_comments


def source_gates() -> None:
    """First word, comment stripping, forced line break, duplicate names, bullet characters."""
    # _first_word honours the column bound: a word right of x_end (the next
    # entry's date cell, a sidebar) is never taken for a head / org line
    _fw = [((300.0, 10.0, 330.0, 20.0), "2019"), ((50.0, 12.0, 90.0, 22.0), "Beta")]
    assert _first_word(_fw, 50.0, 10.0, 40.0) == 1
    assert _first_word(_fw[:1], 50.0, 10.0, 40.0) == 0
    assert _first_word(_fw[:1], 50.0, 10.0, 40.0, x_end=299.0) is None
    # date adjacency without word boxes / markers never crashes
    assert not check_date_adjacency("", "", marks=[])
    _ww: list[str] = []
    assert not check_date_adjacency("", "", marks=[{"kind": "entry", "text": "A", "page": 1, "x": 0, "y": 0, "dated": True}],
                                    warns=_ww, words=[[]]) and _ww
    # comment stripping: nested blocks, stray quote, raw span
    assert "lib.typ" not in _strip_typst_comments('/* a /* b */ #import "lib.typ" */\n')
    assert "lib.typ" in _strip_typst_comments('a 6" pipe\n#import "lib.typ"\n')
    assert "lib.typ" not in _strip_typst_comments('`#import "lib.typ"`\n')
    assert "lib.typ" in _strip_typst_comments('#let u = "a//b"\n#import "lib.typ"\n')

    # forced line break inside a bullet: a hard break mid-bullet FAILs,
    # the same text wrapped by itself, or a break outside any bullet, does not.
    assert check_forced_linebreak("- Led the migration \\ to the new stack\n")
    assert check_forced_linebreak("- Led the migration #linebreak() to the new stack\n")
    assert check_forced_linebreak("- Led the migration,\n  continued \\\n  here\n")
    assert not check_forced_linebreak("- Led the migration to the new stack\n  and shipped it\n")
    assert not check_forced_linebreak("Name \\ Title\n\n- Bullet one\n")
    assert check_literal_tilde("- Served ~25 users\n")
    assert check_literal_tilde("#skill([Scale], [~25 users])\n")
    assert not check_literal_tilde("- Served \\~25 users\n")
    assert check_literal_tilde("- *~25 users* served\n") and check_literal_tilde("- _~25_ users\n")
    assert not check_literal_tilde("```\nx ~25\ny ~z\n```\n- fine\n")
    assert not check_literal_tilde("/* a\n ~25 b\n*/\n- fine\n") and not check_literal_tilde("/* ~25 */ ok\n")
    assert not check_literal_tilde("- Let $x ~y$ be\n")
    assert not check_literal_tilde("[see https://x.com/~user] #link(\"https://x.com/~user\")[a]\n")
    assert [m.split(":")[0] for m in check_literal_tilde("/* c\n*/\n```\na\n```\n- ~25 users\n")] == ["line 6"]
    assert not check_literal_tilde('#skill("Scale", "~25")  // ~25 note\n')
    assert not check_literal_tilde("[#cat~:] and [~#sc] and `~25`\n")
    assert not check_forced_linebreak("- see https://example.com/a // and path C:\\\\dir\n")

    # duplicate name: a section title reused as a row label (any case) FAILs
    # two things with one name read as one list to a human and to an ATS (check_duplicate_names' docstring);
    # a longer label ("Programming languages") or an entry row is a different name
    _sec: list[Mark] = [{"text": "LANGUAGES", "page": 1, "y": 10.0}, {"text": "Skills", "page": 1, "y": 80.0}]
    assert check_duplicate_names(_sec, [{"kind": "skill", "text": "Languages"}])
    assert check_duplicate_names(_sec, [{"kind": "skill", "text": "languages:"}])
    assert not check_duplicate_names(_sec, [{"kind": "skill", "text": "Programming languages"}])
    assert not check_duplicate_names(_sec, [{"kind": "entry", "text": "Languages"}])

    for t in ("\u25c6 Built the API", "  \u2022", "\u25aa item", "\uf0b7 item"):
        assert check_bullet_chars(t), t
    for t in ("Built the API", "City \u2022 phone", "\u2013 prose dash",
              "Bilingual English / French"):
        assert not check_bullet_chars(t), t

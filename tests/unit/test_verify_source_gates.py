"""Source-level gates: forced line break, literal tilde, comment stripping, bullet characters."""
import pytest
from vitae.verify.source import check_forced_linebreak, check_literal_tilde
from vitae.verify.text import check_bullet_chars
from vitae.verify.typst import _strip_typst_comments


@pytest.mark.parametrize("src, fires", [
    ("- Led the migration \\ to the new stack\n", True),
    ("- Led the migration #linebreak() to the new stack\n", True),
    ("- Led the migration,\n  continued \\\n  here\n", True),
    ("- Led the migration to the new stack\n  and shipped it\n", False),     # wrapped by itself
    ("Name \\ Title\n\n- Bullet one\n", False),                               # outside any bullet
    ("- see https://example.com/a // and path C:\\\\dir\n", False),
])
def test_forced_linebreak_inside_a_bullet(src, fires):
    assert bool(check_forced_linebreak(src)) == fires


@pytest.mark.parametrize("src, fires", [
    ("- Served ~25 users\n", True),
    ("#skill([Scale], [~25 users])\n", True),
    ("- *~25 users* served\n", True),
    ("- _~25_ users\n", True),
    ("- Served \\~25 users\n", False),                                       # escaped
    ("```\nx ~25\ny ~z\n```\n- fine\n", False),                              # raw block
    ("/* a\n ~25 b\n*/\n- fine\n", False), ("/* ~25 */ ok\n", False),        # comments
    ('#skill("Scale", "~25")  // ~25 note\n', False),
    ("- Let $x ~y$ be\n", False),                                            # math
    ('[see https://x.com/~user] #link("https://x.com/~user")[a]\n', False),  # URLs
    ("[#cat~:] and [~#sc] and `~25`\n", False),
])
def test_literal_tilde(src, fires):
    assert bool(check_literal_tilde(src)) == fires


def test_literal_tilde_reports_the_line_after_comments_and_raw_blocks():
    assert [m.split(":")[0] for m in check_literal_tilde("/* c\n*/\n```\na\n```\n- ~25 users\n")] == ["line 6"]


@pytest.mark.parametrize("src, kept", [
    ('/* a /* b */ #import "lib.typ" */\n', False),      # nested block comment
    ('a 6" pipe\n#import "lib.typ"\n', True),            # a stray quote opens no string
    ('`#import "lib.typ"`\n', False),                    # raw span
    ('#let u = "a//b"\n#import "lib.typ"\n', True),      # // inside a string is no comment
])
def test_strip_typst_comments(src, kept):
    assert ("lib.typ" in _strip_typst_comments(src)) == kept


@pytest.mark.parametrize("text, fires", [
    ("\u25c6 Built the API", True), ("  \u2022", True), ("\u25aa item", True), ("\uf0b7 item", True),
    ("Built the API", False), ("City \u2022 phone", False), ("\u2013 prose dash", False),
    ("Bilingual English / French", False),
])
def test_bullet_characters_only_when_leading(text, fires):
    assert bool(check_bullet_chars(text)) == fires

"""verify.typst: parsing of Typst source (`spacing:` argument, document body size)."""
import pytest
from vitae.verify.typst import _doc_body_size, _spacing_arg


@pytest.mark.parametrize("args, found, groups", [
    ("spacing: 0.5em", True, ("0.5", "em")),
    ("leading: 1em, spacing: 2pt", True, ("2", "pt")),
    ("spacing:\n 3em", True, ("3", "em")),
    ("spacing: auto", True, None),          # found but non-numeric
    ("box(spacing: 1pt)", False, None),     # nested call's own argument
    ("leading: 1em", False, None),
    ("", False, None),
])
def test_spacing_arg(args, found, groups):
    ok, m = _spacing_arg(args)
    assert ok is found
    assert (m.groups() if m else None) == groups


@pytest.mark.parametrize("text, expected", [
    ("#set text(size: 10pt)\n#set par(leading: 0.5em)\nBody", 10.0),
    ("#set text(size: 9.5pt)\n#set text(size: 12pt)\nx", 12.0),     # the last one wins
    ("Just body", None),
    ("", None),
])
def test_doc_body_size(text, expected):
    assert _doc_body_size(text) == expected

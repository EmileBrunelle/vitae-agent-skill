"""Pinned behaviour of verify.py's pure parsing helpers (development only, not shipped logic).

Each test records what the function does TODAY. Former defects (unclosed `#section` bracket) are now fixed and tested plainly.
"""
import pytest
import verify as v
import vitae.verify.typst as verify_typst

# --- _fold -----------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("s, expected", [
    ("Éléphant — Ça’va", "elephant - ca'va"),
    ("  A\n\tB ", " a b "),
    ("", ""),
    ("a–b‒c−d", "a-b-c-d"),
])
def test_fold(s, expected):
    assert v._fold(s) == expected


# --- _num_values -----------------------------------------------------------------------------------------------

@pytest.mark.parametrize("text, expected", [
    ("1,200", {1200.0}),
    ("1 200", {1200.0}),
    ("1.5k", {1500.0}),
    ("2M", {2_000_000.0}),
    ("3,5", {3.5}),                         # decimal comma
    ("10 000 000", {10_000_000.0}),
    ("", set()),
    ("abc", set()),
    ("1,2,3", set()),                       # malformed: "1.2.3" is not a float and is skipped, not raised
])
def test_num_values(text, expected):
    assert v._num_values(text) == expected


# --- _norm_heading ---------------------------------------------------------------------------------------------

@pytest.mark.parametrize("s, expected", [
    ("Work Experience!", "work experience"),
    ("  A  B ", "a b"),
    ("A/B", "a b"),
    ("", ""),
    ("!!!", ""),
])
def test_norm_heading(s, expected):
    assert v._norm_heading(s) == expected


def test_norm_heading_drops_accents_on_latin_letters():
    # "Expérience" and "EXPÉRIENCE" meet on "experience"; both sides of a real comparison go through it.
    assert v._norm_heading("EXPÉRIENCE") == "experience"
    assert v._norm_heading("Expérience") == v._norm_heading("EXPERIENCE")


# --- _spacing_arg ----------------------------------------------------------------------------------------------

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
    ok, m = verify_typst._spacing_arg(args)
    assert ok is found
    assert (m.groups() if m else None) == groups


# --- _doc_body_size --------------------------------------------------------------------------------------------

@pytest.mark.parametrize("text, expected", [
    ("#set text(size: 10pt)\n#set par(leading: 0.5em)\nBody", 10.0),
    ("#set text(size: 9.5pt)\n#set text(size: 12pt)\nx", 12.0),     # the last one wins
    ("Just body", None),
    ("", None),
])
def test_doc_body_size(text, expected):
    assert v._doc_body_size(text) == expected


def test_typst_newer_than_calibration_note(monkeypatch, capsys):
    monkeypatch.setattr(v.shutil, "which", lambda n: "/x/typst" if n == "typst" else None)
    class R:
        stdout = "typst 0.16.0 (abc)"
    monkeypatch.setattr(v.subprocess, "run", lambda *a, **k: R())
    assert v.check_typst() == (True, True)
    out = capsys.readouterr().out
    assert out.startswith("OK    typst 0.16.0") and "newer versions may measure differently" in out
    R.stdout = "typst 0.15.1 (abc)"
    assert v.check_typst() == (True, True)
    assert "newer versions" not in capsys.readouterr().out

"""vitae.verify.placeholders: a template sample left in a compiled CV is a FAIL, other bracketed text a WARN.

The CVs are tiny Typst documents compiled with the `typst` package, read back through the pdfium extractor."""
import dataclasses
import shutil
import subprocess
import sys

import pytest
import typst
from _paths import ROOT, SCRIPTS
from vitae.core.level import Level
from vitae.verify import cv, pdf, placeholders
from vitae.verify.gates import EXTRACTION_GATES, _placeholders, make_context

TEMPLATES = ROOT / "templates"


def _ctx(tmp_path, body, name="cv"):
    typ = tmp_path / f"{name}.typ"
    src = "#set page(width: 400pt, height: 200pt)\n" + body
    typ.write_text(src, encoding="utf-8")
    out = tmp_path / f"{name}.pdf"
    typst.compile(str(typ), output=str(out))
    return make_context(str(typ), str(out), pdf.extract_text(str(out), "pdfium"), src, "pdfium", can_query=False)


def _levels(ctx):
    return [lvl for lvl, _ in placeholders.check_placeholders(ctx)]


def test_clean_cv_has_no_finding(tmp_path):
    assert _levels(_ctx(tmp_path, "Alix Bernard, engineer since 2019 (see ref. \\[1\\] and \\[23\\]).")) == []


@pytest.mark.parametrize("text", [
    "Engineer, \\[Role\\] - present",
    "Contact: me\\@example.com",
    "Call (555) 555-0100",
    "Firstname Lastname",
])
def test_template_sample_is_a_fail(tmp_path, text):
    out = placeholders.check_placeholders(_ctx(tmp_path, text))
    assert out[0][0] == Level.FAIL
    assert "placeholder" in out[0][1]


def test_placeholder_wrapped_over_two_lines_still_fails(tmp_path):
    assert Level.FAIL in _levels(_ctx(tmp_path, "\\[Action\nverb\\]"))


def test_other_bracketed_text_is_a_warn_not_a_fail(tmp_path):
    out = placeholders.check_placeholders(_ctx(tmp_path, "Led the team \\[some note\\] in 2020."))
    assert [lvl for lvl, _ in out] == [Level.WARN]
    assert "[some note]" in out[0][1]


@pytest.mark.parametrize("text", ["Cited \\[1\\].", "Items \\[12, 14\\].", "Short \\[ab\\] span.", "Plain text."])
def test_numeric_or_tiny_brackets_are_silent(tmp_path, text):
    assert _levels(_ctx(tmp_path, text)) == []


def test_any_derived_bracketed_entry_fails_when_rendered(tmp_path):
    entry = next(p for p in placeholders.placeholders_from(TEMPLATES) if p.startswith("["))
    assert Level.FAIL in _levels(_ctx(tmp_path, entry.replace("[", "\\[").replace("]", "\\]")))


def _fixture_templates(tmp_path):
    d = tmp_path / "tpl"
    d.mkdir()
    (d / "t.typ").write_text("#let x = [[One sentence, with the field's key terms in *bold*.]]\n"
                             "#section([Target-field])\n", encoding="utf-8")
    return d


def test_markup_and_typographic_quotes_are_normalised(tmp_path):
    ctx = _ctx(tmp_path, "One sentence, with the field\u2019s key terms in bold. \\[One sentence, with the field\u2019s "
                         "key terms in bold.\\]")
    out = placeholders.check_placeholders(ctx, _fixture_templates(tmp_path))
    assert out[0][0] == Level.FAIL and "placeholder left" in out[0][1]


def test_uppercased_placeholder_fails(tmp_path):
    out = placeholders.check_placeholders(_ctx(tmp_path, "\\[TARGET-FIELD\\] EXPERIENCE"), _fixture_templates(tmp_path))
    assert out[0][0] == Level.FAIL


def test_missing_template_list_warns_and_keeps_sample_shapes(tmp_path):
    empty = tmp_path / "nope"
    out = placeholders.check_placeholders(_ctx(tmp_path, "Plain CV text."), empty)
    assert [lvl for lvl, _ in out] == [Level.WARN] and "sample contact shapes" in out[0][1]
    out = placeholders.check_placeholders(_ctx(tmp_path, "Mail me\\@example.com"), empty)
    assert [lvl for lvl, _ in out] == [Level.WARN, Level.FAIL]


def test_gate_is_registered():
    assert "placeholders" in [g.name for g in EXTRACTION_GATES]


# ---------------------------------------------------------------- the list follows the templates

def test_list_is_read_off_the_templates():
    found = placeholders.placeholders_from(TEMPLATES)
    for expected in ("[Role]", "[YYYY]", "[, outcome, if stated]", "Firstname Lastname", "me@example.com",
                     "(555) 555-0100", "linkedin.com/in/handle", "github.com/handle"):
        assert expected in found, expected


def test_list_ignores_comments_and_code(tmp_path):
    (tmp_path / "t.typ").write_text(
        "// [Commented placeholder]\n/* [Block comment] */\n#link(\"https://x.org\")[[Real span]] [#code-span] [\\p{L}]\n",
        encoding="utf-8")
    assert placeholders.placeholders_from(tmp_path) == ("[Real span]",)


def test_academic_template_content_is_not_flagged():
    """The academic CV's data is fictional but real-looking: only its own bracketed placeholders may match."""
    toml = (TEMPLATES / "academic" / "faits-academique.example.toml").read_text(encoding="utf-8")
    flat = placeholders._squash(toml)
    for p in placeholders.placeholders_from(TEMPLATES):
        assert placeholders._squash(p) not in flat, p


# ---------------------------------------------------------------- shipped templates, compiled as-is

TEMPLATE_CVS = sorted(p for p in (TEMPLATES / "families").rglob("resume*.typ")) + [TEMPLATES / "resume.typ"]


@pytest.mark.parametrize("typ", TEMPLATE_CVS, ids=lambda p: str(p.relative_to(TEMPLATES)))
def test_every_shipped_template_trips_the_fail(typ, tmp_path):
    out = tmp_path / "t.pdf"
    typst.compile(str(typ), output=str(out), root=str(TEMPLATES.parent))
    txt = pdf.extract_text(str(out), "pdfium")
    ctx = make_context(str(typ), str(out), txt, typ.read_text(encoding="utf-8"), "pdfium", can_query=False)
    assert placeholders.check_placeholders(ctx)[0][0] == Level.FAIL


@pytest.mark.parametrize("text", [
    "github.com/handlebars-lang/handlebars.js",
    "linkedin.com/in/handley-j",
    "Contact: dame\\@example.com",
    "Firstname Lastnameson",
])
def test_longer_real_value_is_not_a_placeholder(tmp_path, text):
    assert Level.FAIL not in _levels(_ctx(tmp_path, text))


@pytest.mark.parametrize("text", ["github.com/handle", "linkedin.com/in/handle", "Firstname Lastname\nEngineer",
                                   "see https://github.com/handle."])
def test_bare_sample_is_a_fail(tmp_path, text):
    assert Level.FAIL in _levels(_ctx(tmp_path, text))


def test_bracketed_and_bare_sample_reported_once(tmp_path):
    out = placeholders.check_placeholders(_ctx(tmp_path, "\\[linkedin.com/in/handle\\] linkedin.com/in/handle"))
    fails = [m for lvl, m in out if lvl == Level.FAIL]
    assert len(fails) == 1 and fails[0].count("linkedin.com/in/handle") == 1


# ---------------------------------------------------------------- every placeholder renders with its brackets

def test_escaped_and_bare_content_block_spans_are_derived():
    """Both are collected: the escaped one renders with its brackets, the bare one is what the sync test flags."""
    src = '#nb(mk.pin)[\\[City, Region\\]] #text(size: 9pt)[Plain content block] [Marked span]'
    assert placeholders.placeholders_in(src) == {"[City, Region]", "[Plain content block]", "[Marked span]"}


def test_span_that_is_only_a_bare_sample_is_not_collected_twice():
    assert placeholders.placeholders_in('#text()[Firstname Lastname] #link("x")[github.com/handle]') == {
        "Firstname Lastname", "github.com/handle"}


def test_span_wrapped_over_lines_is_derived_whole():
    assert placeholders.placeholders_in("[Strongest fact from the\nfacts, with its number.]") == {
        "[Strongest fact from the facts, with its number.]"}


SYNC_FILES = TEMPLATE_CVS + [TEMPLATES / "letter.typ"]


@pytest.mark.parametrize("typ", SYNC_FILES, ids=lambda p: str(p.relative_to(TEMPLATES)))
def test_every_placeholder_derived_from_a_template_renders_in_its_text(typ, tmp_path):
    """A placeholder written as a content-block argument renders WITHOUT brackets and the gate could never see it;
    a derived entry that never renders is dead weight. Both fail here."""
    out = tmp_path / "t.pdf"
    typst.compile(str(typ), output=str(out), root=str(TEMPLATES.parent))
    flat = placeholders._fold(pdf.extract_text(str(out), "pdfium"))
    derived = placeholders.placeholders_in(typ.read_text(encoding="utf-8"))
    assert derived
    missing = sorted(p for p in derived if not placeholders._matcher(p).search(flat))
    assert not missing, missing


def test_sync_check_catches_a_placeholder_rendered_without_brackets(tmp_path):
    """The shape the sync test guards against: the same text as a plain content block."""
    typ = tmp_path / "t.typ"
    typ.write_text("#let nb(b) = b\n#nb[[City, Region]]\n", encoding="utf-8")
    assert "[City, Region]" in placeholders.placeholders_in('[City, Region] (not a block)')
    out = tmp_path / "t.pdf"
    typst.compile(str(typ), output=str(out))
    flat = placeholders._fold(pdf.extract_text(str(out), "pdfium"))
    assert placeholders._matcher("[City, Region]").search(flat)  # sanity: brackets present here
    typ.write_text("#let nb(b) = b\n#nb[City, Region]\n", encoding="utf-8")
    typst.compile(str(typ), output=str(out))
    flat = placeholders._fold(pdf.extract_text(str(out), "pdfium"))
    assert not placeholders._matcher("[City, Region]").search(flat)


# ---------------------------------------------------------------- the handle's own underscores

@pytest.mark.parametrize("text", ["github.com/handle\\_", "github.com/\\_handle", "linkedin.com/in/\\_handle\\_"])
def test_underscore_in_a_real_handle_is_not_folded_away(tmp_path, text):
    assert Level.FAIL not in _levels(_ctx(tmp_path, text))


# ---------------------------------------------------------------- pypdf fallback

def test_pypdf_downgrades_the_fail_to_a_warn(tmp_path):
    ctx = _ctx(tmp_path, "Contact: me\\@example.com")
    assert [lvl for lvl, _ in _placeholders(ctx)][0] == Level.FAIL
    out = _placeholders(dataclasses.replace(ctx, backend="pypdf"))
    assert out[0][0] == Level.WARN and "pypdf extraction is indicative" in out[0][1]


# ---------------------------------------------------------------- --allow-placeholders only for the shipped templates

def test_allow_placeholders_scope(tmp_path, monkeypatch):
    assert cv.placeholders_allowed(str(TEMPLATES / "families" / "swiss-grid" / "resume.typ"))
    assert not cv.placeholders_allowed(str(tmp_path / "templates" / "x" / "_raw.typ"))   # a folder of that name elsewhere
    assert not cv.placeholders_allowed(str(tmp_path / "cv.typ"))
    monkeypatch.setattr(placeholders, "TEMPLATES", tmp_path / "skill" / "templates")
    assert cv.placeholders_allowed(str(tmp_path / "skill" / "templates" / "x" / "_raw.typ"))


def _verify(*args, script=None):
    return subprocess.run([sys.executable, "-I", str(script or SCRIPTS / "verify.py"), *args], capture_output=True,
                          text=True, timeout=300, stdin=subprocess.DEVNULL).stdout


def _lorem_cv(path, words):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"#set page(width: 400pt, height: 300pt, margin: 20pt)\n#set text(size: 11pt)\n"
                    f"#set par(leading: 0.65em, spacing: 0.65em)\n#lorem({words})\n", encoding="utf-8")
    return str(path)


@pytest.fixture
def skill_copy(tmp_path):
    """A scratch skill: its own scripts/ and an empty templates/, so that templates/ is the copy's own."""
    root = tmp_path / "skill"
    shutil.copytree(SCRIPTS, root / "scripts", ignore=shutil.ignore_patterns("__pycache__"))
    (root / "templates").mkdir()
    return root


def test_allow_placeholders_refused_outside_the_skill_templates(tmp_path):
    for typ in (tmp_path / "cv.typ", tmp_path / "templates" / "cv.typ"):     # a folder named templates elsewhere too
        out = _verify(_lorem_cv(typ, 130), "1", "60", "100", "--allow-placeholders")
        assert "FAIL  --allow-placeholders is only for the shipped templates" in out
        assert "placeholder gate skipped" not in out and "no-split" in out  # the gate ran


def test_allow_placeholders_honoured_under_the_skill_templates(skill_copy):
    typ = _lorem_cv(skill_copy / "templates" / "cv.typ", 130)
    out = _verify(typ, "1", "60", "100", "--allow-placeholders", script=skill_copy / "scripts" / "verify.py")
    assert "--allow-placeholders is only for" not in out
    assert "WARN  placeholder gate skipped (--allow-placeholders)" in out


def test_printed_follow_ups_keep_the_flag(skill_copy):
    script = skill_copy / "scripts" / "verify.py"
    typ = _lorem_cv(skill_copy / "templates" / "cv.typ", 130)
    out = _verify(typ, "1", "99", "100", "--allow-placeholders", script=script)
    assert "--tune " + typ + " 1 99 100 --allow-placeholders`" in out
    assert "scripts/verify.py " + typ + " 1 63 100 --allow-placeholders`" in out     # NEXT lowered target
    assert "FILL_MIN FILL_MAX --allow-placeholders; " in _verify(typ, "1", "--allow-placeholders", script=script)
    plain = _verify(typ, "1", "99", "100", script=script)
    assert "--allow-placeholders" not in plain.split("──── extraction")[0].replace("placeholder gate", "")


def test_flag_before_facts_is_stripped_first(skill_copy):
    facts = skill_copy / "facts.md"
    facts.write_text("Lorem 2020", encoding="utf-8")
    typ = _lorem_cv(skill_copy / "templates" / "cv.typ", 130)
    out = _verify(typ, "1", "60", "100", "--allow-placeholders", "--facts", str(facts), script=skill_copy / "scripts" / "verify.py")
    assert "placeholder gate skipped" in out and "usage" not in out.lower()


def test_tune_hints_keep_the_flag(skill_copy):
    typ = _lorem_cv(skill_copy / "templates" / "cv.typ", 130)
    out = _verify("--tune", typ, "1", "99", "100", "--allow-placeholders", script=skill_copy / "scripts" / "verify.py")
    assert "UNDER-FILLED" in out and "FILL_MIN 100 --allow-placeholders`" in out.replace("\n", " ")


def test_all_forwards_the_flag_to_each_child(tmp_path, monkeypatch):
    seen = []
    monkeypatch.setattr(cv.subprocess, "run", lambda cmd, *a, **k: seen.append(cmd) or subprocess.CompletedProcess(cmd, 0))
    d = tmp_path / "templates"
    _lorem_cv(d / "a.typ", 20), _lorem_cv(d / "b" / "c.typ", 20)
    assert cv.check_all(str(d), allow_placeholders=True) == 0
    assert len(seen) == 2 and all(c[-1] == "--allow-placeholders" for c in seen)
    seen.clear()
    cv.check_all(str(d))
    assert len(seen) == 2 and all("--allow-placeholders" not in c for c in seen)


# ---------------------------------------------------------------- review pass 3

def test_same_placeholder_in_two_cases_is_still_a_fail(tmp_path):
    for text in ("Skills: \\[item\\], Python", "Skills: \\[ITEM\\], Python", "\\[item\\] and \\[ITEM\\]"):
        out = placeholders.check_placeholders(_ctx(tmp_path, text), _item_templates(tmp_path))
        assert out[0][0] == Level.FAIL, text


def _item_templates(tmp_path):
    d = tmp_path / "items"
    d.mkdir(exist_ok=True)
    (d / "t.typ").write_text('#skill("[Category]", "[item], [ITEM]")\n', encoding="utf-8")
    return d


@pytest.mark.parametrize("text", ["www.linkedin.com/in/handle", "https://www.github.com/handle", "see https://github.com/handle",
                                   "WWW.GitHub.com/handle"])
def test_url_sample_after_www_or_scheme_is_a_fail(tmp_path, text):
    assert Level.FAIL in _levels(_ctx(tmp_path, text))


@pytest.mark.parametrize("text", ["mywww.github.com/handle", "xgithub.com/handle", "https://www.github.com/handlex",
                                   "www.me\\@example.com"])
def test_url_sample_lookalikes_stay_clean(tmp_path, text):
    assert Level.FAIL not in _levels(_ctx(tmp_path, text))


def test_stray_bracket_does_not_make_a_huge_warn(tmp_path):
    text = "Opening \\[ " + "word " * 60 + " closing \\] here and a real \\[note here\\]."
    out = placeholders.check_placeholders(_ctx(tmp_path, text))
    assert [lvl for lvl, _ in out] == [Level.WARN] and "[note here]" in out[0][1] and len(out[0][1]) < 200

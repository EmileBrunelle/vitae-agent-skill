"""vitae.verify.contact: a contact block that takes more rows than its layout declares is a FAIL.

Tiny CVs importing the real lib.typ `contact`; rows are counted from item y only, so scripts, right-to-left
text and unspaced text are treated like any other."""
import shutil

import pytest
import typst
from _paths import ROOT
from vitae.core.level import Level
from vitae.verify.contact import check_contact_line, count_rows
from vitae.verify.gates import make_context

TEMPLATES = ROOT / "templates"


def _check(tmp_path, body, lang="en", font="Libertinus Serif", rows=None, rtl=False):
    for name in ("lib.typ", "icons.typ"):
        shutil.copy(TEMPLATES / name, tmp_path / name)
    typ = tmp_path / "cv.typ"
    decl = f"#contact-rows({rows})\n" if rows else ""
    typ.write_text(f'#import "lib.typ": nb, contact, contact-rows\n#set page(width: 300pt, height: 120pt)\n'
                   f'#set text(font: "{font}", lang: "{lang}", size: 10pt{", dir: rtl" if rtl else ""})\n{decl}{body}\n',
                   encoding="utf-8")
    typst.compile(str(typ), output=str(tmp_path / "cv.pdf"))
    ctx = make_context(str(typ), str(tmp_path / 'cv.pdf'), '', '', None, root=str(tmp_path))
    return check_contact_line(ctx.contact_items, ctx.contact_rows)


def _items(words):
    return " ".join("#contact(none)[" + w.replace("@", "\\@") + "]" for w in words)


def test_one_row_passes(tmp_path):
    assert _check(tmp_path, _items(["Montreal", "555-0100", "me@x.org"]))[0][0] == Level.OK


def test_wrapped_single_row_fails(tmp_path):
    out = _check(tmp_path, _items(["Montreal", "514-555-0100", "maya@example.com", "linkedin.com/in/maya", "github.com/maya"]))
    assert out[0][0] == Level.FAIL
    assert "wraps" in out[0][1]


def test_wrapped_fail_hints_contact_rows_declaration(tmp_path):
    out = _check(tmp_path, _items(["Montreal", "514-555-0100", "maya@example.com", "linkedin.com/in/maya", "github.com/maya"]))
    rows = int(out[0][1].split(" items take ")[1].split(" rows")[0])
    assert f"#contact-rows({rows})" in out[0][1]


def test_designed_multi_row_passes_and_extra_wrap_fails(tmp_path):
    col = "#contact(none)[a] \\ #contact(none)[b] \\ #contact(none)[c]"
    assert _check(tmp_path, col, rows=3)[0][0] == Level.OK
    assert _check(tmp_path, col, rows=2)[0][0] == Level.FAIL


def test_no_contact_item_is_not_measured(tmp_path):
    assert _check(tmp_path, "plain contact text")[0][0] == Level.INFO


ARABIC = ["مونتريال", "٥١٤-٥٥٥-٠١٤٢", "maya@example.com", "linkedin.com/in/maya", "github.com/maya-okafor"]


def test_rtl_arabic_one_row_passes(tmp_path):
    assert _check(tmp_path, _items(ARABIC[:3]), lang="ar", font="Noto Sans Arabic", rtl=True)[0][0] == Level.OK


def test_rtl_arabic_wrapped_fails(tmp_path):
    assert _check(tmp_path, _items(ARABIC), lang="ar", font="Noto Sans Arabic", rtl=True)[0][0] == Level.FAIL


def test_cjk_unspaced_one_row_passes_and_wrapped_fails(tmp_path):
    one = _check(tmp_path, _items(["モントリオール", "５１４－５５５", "maya"]), lang="ja", font="Noto Serif CJK JP")
    assert one[0][0] == Level.OK
    many = _check(tmp_path, _items(["モントリオール市在住", "電話５１４－５５５－０１４２", "メールmaya@example.com",
                                     "リンクトイン", "ギットハブ公開リポジトリ"]), lang="ja", font="Noto Serif CJK JP")
    assert many[0][0] == Level.FAIL


@pytest.mark.parametrize(("ys", "n"), [([], 0), ([10.0], 1), ([10.0, 11.4, 10.2], 1), ([10.0, 22.0], 2)])
def test_count_rows(ys, n):
    assert count_rows(ys) == n


def _query_count(tmp_path, body, label="<vitae-contact>"):
    from vitae.verify.groups.query import _typst_values
    for name in ("lib.typ", "icons.typ"):
        shutil.copy(TEMPLATES / name, tmp_path / name)
    typ = tmp_path / "q.typ"
    typ.write_text('#import "lib.typ": nb, contact, contact-rows, drawn-marker\n#set page(width: 300pt, height: 120pt)\n'
                   f"{body}\n", encoding="utf-8")
    vals = _typst_values(str(typ), label, str(tmp_path))
    assert vals is not None
    return len(vals)


def test_nb_is_not_a_contact_item(tmp_path):
    """nb is the general mark+value primitive (Languages, skills): it must not be counted as contact."""
    assert _query_count(tmp_path, "#nb(none)[French] #nb(none)[English]") == 0
    assert _query_count(tmp_path, "#contact(none)[a] #contact(none)[b]") == 2
    out = _check(tmp_path, "#nb(none)[French] #nb(none)[English] #nb(none)[German] #nb(none)[Spanish] #nb(none)[Portuguese] #nb(none)[Italian]")
    assert out[0][0] == Level.INFO


def test_mixed_mark_heights_stay_one_row(tmp_path):
    """Marks of 14pt and 16pt beside plain text differ in box top by >4pt but share one baseline."""
    body = ("#contact(none)[Montreal] #contact(box(width: 8pt, height: 14pt, baseline: 3pt))[555-0100] "
            "#contact(box(width: 8pt, height: 16pt, baseline: 3pt))[me\\@x.org]")
    assert _check(tmp_path, body)[0][0] == Level.OK


def test_unreadable_row_declaration_is_warn_not_fail():
    out = check_contact_line([{"page": 1, "x": 1.0, "y": 10.0}], None)
    assert out[0][0] == Level.WARN
    assert "not measured" in out[0][1]


def test_unavailable_query_is_warn():
    assert check_contact_line(None, None)[0][0] == Level.WARN


def test_a_verify_runs_one_typst_query_for_all_labels(tmp_path, monkeypatch):
    """The marks, the bullets and both contact labels come from ONE query (one compile), not three."""
    from vitae.verify.groups import query
    calls = []
    real = query._typst_values
    monkeypatch.setattr(query, "_typst_values", lambda typ, sel, root=None: calls.append(sel) or real(typ, sel, root))
    out = _check(tmp_path, _items(["Montreal", "555-0100", "me@x.org"]))
    assert out[0][0] == Level.OK
    assert len(calls) == 1
    assert all(lbl in calls[0] for lbl in ("<vitae-contact>", "<vitae-contact-rows>", "<vitae-bullet>", "<vitae-head>"))


@pytest.mark.parametrize("rel", ["resume.typ", "families/engraved-card/resume.typ"])
def test_every_header_contact_item_is_tagged(tmp_path, rel):
    """City, phone, mail, LinkedIn, GitHub: five tagged items, so a wrap of any of them is seen."""
    from vitae.verify.groups.query import _typst_values
    vals = _typst_values(str(TEMPLATES / rel), "<vitae-contact>", str(ROOT))
    assert vals is not None and len(vals) == 5


def test_contact_is_recognised_by_its_explicit_kind_only(tmp_path, monkeypatch):
    """A value shaped like a contact item but without `kind` is a (malformed) mark, never a contact item."""
    from vitae.verify.groups import query
    shaped = {"text": "", "page": 1, "x": 5.0, "y": 10.0}
    tagged = {"kind": "contact", "text": "", "page": 1, "x": 5.0, "y": 10.0}
    decl = {"kind": "contact-rows", "rows": 2}
    monkeypatch.setattr(query, "_typst_values", lambda *a, **k: [shaped, tagged, decl, {"page": 1, "y": 3.0}])
    marks, note, contact = query._typst_marks_and_contact("x.typ", "sel")
    assert contact is not None
    assert contact.items == [tagged]
    assert contact.rows == [decl]
    assert marks == [shaped]
    assert note is not None and "malformed" in note


def test_contact_rows_accepts_a_whole_number_float(tmp_path):
    body = "#contact(none)[a] \\\\ #contact(none)[b]"
    assert _check(tmp_path, body, rows="2.0")[0][0] == Level.OK


def test_contact_rows_declaration_unreadable_is_warn():
    items = [{"kind": "contact", "page": 1, "y": 10.0}]
    for bad in (2.5, 0, "2", None):
        out = check_contact_line(items, [{"kind": "contact-rows", "rows": bad}])
        assert out[0][0] == Level.WARN and "contact-rows" in out[0][1]

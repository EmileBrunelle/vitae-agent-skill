"""vitae.verify.rhythm: a bullet's wrapped line must sit closer than the next bullet (bullet pitch above wrapped
pitch by 0.5pt). Inverted and flat lists FAIL; a healthy list passes; no wrapped bullet is INFO, never a FAIL.

Tiny Typst documents drawing their list through lib.typ's marker, compiled with the `typst` package."""
import shutil

import pytest
import typst
from _paths import ROOT
from vitae.core.level import Level
from vitae.verify import pdf
from vitae.verify.gates import LAYOUT_GATES, _spacing_rhythm, make_context
from vitae.verify.pdf import _bbox_pages
from vitae.verify.rhythm import check_rhythm, measure_columns

LATIN = ("Reduced the nightly billing report time after profiling slow queries and adding indexes so the "
         "whole report now finishes well inside the maintenance window each night.")
ARABIC = ("قمت بتقليل زمن تقرير الفوترة الليلي بعد تحليل الاستعلامات البطيئة وإضافة الفهارس بحيث ينتهي "
          "التقرير كاملا داخل نافذة الصيانة كل ليلة دون أي تأخير يذكر.")
PAGE = "width: 300pt, height: 400pt, margin: 20pt"


def _list(leading, spacing, text=LATIN, n=4):
    return (f"#set par(leading: {leading}em)\n"
            f'#set list(marker: list-marker("dot", black), indent: 0pt, spacing: {spacing}em, body-indent: 6pt)\n'
            + "".join(f"- {text}\n" for _ in range(n)))


def _ctx(tmp_path, body, font="Libertinus Serif", rtl=False, name="r", page=PAGE):
    for f in ("lib.typ", "icons.typ"):
        shutil.copy(ROOT / "templates" / f, tmp_path / f)
    src = (f'#import "lib.typ": list-marker\n#set page({page})\n'
           f'#set text(font: "{font}", size: 10pt{", dir: rtl" if rtl else ""})\n#set par(justify: false)\n{body}\n')
    typ = tmp_path / f"{name}.typ"
    typ.write_text(src, encoding="utf-8")
    out = tmp_path / f"{name}.pdf"
    typst.compile(str(typ), output=str(out))
    return make_context(str(typ), str(out), pdf.extract_text(str(out), "pdfium"), src, "pdfium", can_query=True)


def _columns(ctx):
    sized = _bbox_pages(ctx.pdf)
    assert sized is not None and ctx.marks is not None
    return measure_columns(ctx.marks, [i for _, _, i in sized], [h for _, h, _ in sized])


def test_inverted_list_fails_with_both_pitches(tmp_path):
    """Leading above the list spacing: the wrapped line sits farther from its bullet than the next bullet does."""
    out = _spacing_rhythm(_ctx(tmp_path, _list(1.0, 0.4)))
    assert [lvl for lvl, _ in out] == [Level.FAIL], out
    msg = out[0][1]
    assert "inverted" in msg and "list(spacing:)" in msg and "--tune" in msg
    c = _columns(_ctx(tmp_path, _list(1.0, 0.4), name="r2"))[0]
    assert c.wrapped is not None and c.bullet is not None and c.bullet < c.wrapped
    assert f"{c.wrapped:.1f}pt" in msg and f"{c.bullet:.1f}pt" in msg


def test_flat_list_fails(tmp_path):
    out = _spacing_rhythm(_ctx(tmp_path, _list(0.65, 0.65)))
    assert [lvl for lvl, _ in out] == [Level.FAIL], out
    assert "flat" in out[0][1]


def test_healthy_list_passes(tmp_path):
    ctx = _ctx(tmp_path, _list(0.5, 1.0))
    assert _spacing_rhythm(ctx) == []
    c = _columns(ctx)[0]
    assert c.wrapped is not None and c.bullet is not None and c.bullet - c.wrapped >= 4


def test_threshold_is_half_a_point(tmp_path):
    """Just above the step passes, just below fails: the limit sits at 0.5pt, not at zero."""
    ctx = _ctx(tmp_path, _list(0.65, 0.65), name="t")
    c = _columns(ctx)[0]
    assert c.wrapped is not None and c.bullet is not None
    sized = _bbox_pages(ctx.pdf)
    assert sized is not None
    def fail(m: str):
        return Level.FAIL, m

    assert check_rhythm(ctx.marks, ctx.pdf, fail=fail, min_step=c.bullet - c.wrapped + 0.1)[0][0] == Level.FAIL
    assert check_rhythm(ctx.marks, ctx.pdf, fail=fail, min_step=c.bullet - c.wrapped - 0.1) == []


def test_no_wrapped_bullet_is_info_not_a_fail(tmp_path):
    out = _spacing_rhythm(_ctx(tmp_path, _list(1.0, 0.4, text="One short line.")))
    assert [lvl for lvl, _ in out] == [Level.INFO], out
    assert "not measured" in out[0][1]


def test_single_bullet_pair_is_not_enough(tmp_path):
    out = _spacing_rhythm(_ctx(tmp_path, _list(1.0, 0.4, n=2)))
    assert [lvl for lvl, _ in out] == [Level.INFO], out


def test_two_columns_are_judged_apart(tmp_path):
    """One healthy list beside one inverted list: only the inverted column fails, and it is named by its x."""
    good = "[\n" + _list(0.5, 1.0) + "]"
    bad = "[\n" + _list(1.0, 0.4) + "]"
    ctx = _ctx(tmp_path, f"#grid(columns: (1fr, 1fr), column-gutter: 20pt, {good}, {bad})", page="width: 420pt, height: 400pt, margin: 20pt")
    cols = _columns(ctx)
    assert len(cols) == 2
    left = min(cols, key=lambda c: c.x)
    assert left.bullet is not None and left.wrapped is not None and left.bullet - left.wrapped > 3
    out = _spacing_rhythm(ctx)
    assert [lvl for lvl, _ in out] == [Level.FAIL], out
    assert f"x={max(c.x for c in cols):.0f}pt" in out[0][1]


@pytest.mark.skipif("noto naskh arabic" not in {f.lower() for f in typst.Fonts().families()}, reason="Arabic font missing")
def test_right_to_left_lists(tmp_path):
    bad = _spacing_rhythm(_ctx(tmp_path, _list(1.0, 0.4, text=ARABIC), font="Noto Naskh Arabic", rtl=True, name="a1"))
    assert [lvl for lvl, _ in bad] == [Level.FAIL], bad
    good = _spacing_rhythm(_ctx(tmp_path, _list(0.5, 1.0, text=ARABIC), font="Noto Naskh Arabic", rtl=True, name="a2"))
    assert good == []


def test_an_entry_head_between_bullets_separates_them(tmp_path):
    """The gap from an entry's last bullet to the next entry, past its head, is not a bullet pitch."""
    mark = ('#context [#metadata((text: "Next", kind: "entry", page: here().position().page, '
            'x: here().position().x.pt(), y: here().position().y.pt())) <vitae-head>]\n')
    split = _list(0.5, 1.0, n=3) + mark + _list(0.5, 1.0, n=3)
    whole = _list(0.5, 1.0, n=6)
    assert _columns(_ctx(tmp_path, split, name="s1"))[0].pairs == 4
    assert _columns(_ctx(tmp_path, whole, name="s2"))[0].pairs == 5


def test_no_lib_marker_is_not_measured_never_a_fail(tmp_path):
    src = "#set page(width: 330pt, height: 200pt)\n- Plain list item that wraps onto the next line because it is long \\ ms.\n"
    typ = tmp_path / "plain.typ"
    typ.write_text(src, encoding="utf-8")
    out_pdf = tmp_path / "plain.pdf"
    typst.compile(str(typ), output=str(out_pdf))
    ctx = make_context(str(typ), str(out_pdf), pdf.extract_text(str(out_pdf), "pdfium"), src, "pdfium")
    out = _spacing_rhythm(ctx)
    assert [lvl for lvl, _ in out] == [Level.WARN]
    assert "not measured" in out[0][1]


def test_without_query_warns():
    out = check_rhythm(None, "x.pdf", fail=lambda m: (Level.FAIL, m))
    assert [lvl for lvl, _ in out] == [Level.WARN]


def test_pypdf_fallback_downgrades_to_warn(tmp_path):
    ctx = _ctx(tmp_path, _list(1.0, 0.4), name="pp")
    ctx = type(ctx)(**{**ctx.__dict__, "backend": "pypdf"})
    assert [lvl for lvl, _ in _spacing_rhythm(ctx)] == [Level.WARN]


def test_gate_is_registered_and_needs_the_query():
    gate = next(g for g in LAYOUT_GATES if g.name == "spacing-rhythm")
    assert gate is not None


def test_far_apart_bullets_are_not_a_bullet_pitch(tmp_path):
    """Bullets more than three line heights apart have something between them: no pair, so INFO."""
    out = _spacing_rhythm(_ctx(tmp_path, _list(0.5, 5.0), name="far"))
    assert [lvl for lvl, _ in out] == [Level.INFO], out


def test_the_next_entry_head_line_is_not_a_bullet_line(tmp_path):
    """A role line right under the last bullet shares its left edge and sits close; it is the next entry, not the
    bullet's wrapped line, so it must not enter the wrapped pitch."""
    from vitae.verify.runts import located_bullets

    def lines(name, body):
        ctx = _ctx(tmp_path, body, name=name)
        sized = _bbox_pages(ctx.pdf)
        assert sized is not None and ctx.marks is not None
        return located_bullets(ctx.marks, [i for _, _, i in sized], [h for _, h, _ in sized])

    lists = _list(0.5, 1.0, n=3)
    edge = lines("h0", lists)[0][1][0].extent.x0 - 20    # the bullet text's offset from the margin
    head = (f'#set par(spacing: 0.3em)\n#pad(left: {edge}pt)[#context [#metadata((text: "R", kind: "entry", '
            'page: here().position().page, x: here().position().x.pt(), y: here().position().y.pt())) '
            '<vitae-head>]Role Title - Jan 2020 - Feb 2021]\n')
    with_head = lines("h1", lists + head)
    assert [len(ls) for _, ls in with_head] == [len(ls) for _, ls in lines("h0", lists)]
    assert min(len(ls) for _, ls in with_head) >= 2


def test_a_section_heading_under_the_last_bullet_is_not_a_wrapped_line(tmp_path):
    """A heading right under a list shares its edge but sits two line heights below: not part of the bullet.
    The wrapped bullet is the last one, so a heading taken for its second line would be the only wrapped pitch."""
    from vitae.verify.runts import located_bullets
    lst = _list(0.5, 1.0, text="Short one.", n=3) + "- " + LATIN[:100] + "\n"
    ctx0 = _ctx(tmp_path, lst, name="sh0")
    sized = _bbox_pages(ctx0.pdf)
    assert sized is not None and ctx0.marks is not None
    edge = located_bullets(ctx0.marks, [i for _, _, i in sized], [h for _, h, _ in sized])[0][1][0].extent.x0 - 20
    ctx = _ctx(tmp_path, lst + f"#pad(left: {edge}pt)[#text(size: 14pt)[Other Experience]]\n", name="sh")
    c = _columns(ctx)[0]
    assert c.wrapped is not None and c.wrapped < 14
    assert _spacing_rhythm(ctx) == []


def test_bullets_on_different_pages_are_not_paired(monkeypatch):
    """Synthetic positions: the second bullet sits lower on page 2 than the first on page 1, so the y gap alone
    is positive (and within reach); only the page check keeps the pair out of the bullet pitch."""
    from vitae.verify import rhythm
    from vitae.verify.runts import BulletLine, Extent, Pos

    def line(page, y1):
        return BulletLine(page, Extent(0.0, 100.0), 10.0, "x", y1)

    placed = [(Pos(1, 10.0, 100.0), [line(1, 110.0)]), (Pos(2, 10.0, 120.0), [line(2, 130.0)])]
    monkeypatch.setattr(rhythm, "located_bullets", lambda *_a, **_k: placed)
    (col,) = measure_columns([], [])
    assert col.pairs == 0
    assert col.bullet is None

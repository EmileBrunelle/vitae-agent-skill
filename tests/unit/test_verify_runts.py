"""vitae.verify.runts: a wrapped bullet whose last line is a few glyphs alone is a FAIL; everything else passes.

The CVs are tiny Typst documents that draw their list through lib.typ's marker, compiled with the `typst` package."""
import shutil

import pytest
import typst
from _paths import ROOT
from vitae.core.level import Level
from vitae.verify import pdf
from vitae.verify.gates import LAYOUT_GATES, _bullet_runts, make_context
from vitae.verify.runts import BulletLine, Extent, check_runts, is_runt

# (script, font, full filler line, long closing text, runt, rtl)
SCRIPTS = {
    "latin": ("Libertinus Serif", "Reduced the nightly billing report time after profiling slow queries and",
              "adding indexes so the whole report now finishes well inside the maintenance window each night.",
              "ms.", False),
    "arabic": ("Noto Naskh Arabic", "قمت بتقليل زمن تقرير الفوترة الليلي بعد تحليل الاستعلامات البطيئة وإضافة",
               "الفهارس بحيث ينتهي التقرير كاملا داخل نافذة الصيانة كل ليلة دون أي تأخير يذكر.", "ثانية.", True),
    "cjk": ("Noto Sans CJK JP", "遅いクエリを分析してインデックスを追加し、夜間の請求レポートの処理時間を大幅に短縮しました。" * 2,
            "その結果、レポート全体が毎晩のメンテナンス時間内に余裕をもって完了するようになりました。" * 2, "分。", False),
    "thai": ("Droid Sans Thai", "ลดเวลาการสร้างรายงานการเรียกเก็บเงินประจำคืนหลังจากวิเคราะห์คิวรีที่ช้าและเพิ่มดัชนี",
             "ทำให้รายงานทั้งหมดเสร็จสิ้นภายในช่วงเวลาบำรุงรักษาทุกคืนโดยไม่มีความล่าช้าใดๆ ที่น่ากังวล", "วินาที", False),
}


def _compile(tmp_path, name, font, bullet, rtl):
    for f in ("lib.typ", "icons.typ"):
        shutil.copy(ROOT / "templates" / f, tmp_path / f)
    src = ('#import "lib.typ": drawn-marker\n#set page(width: 330pt, height: 200pt, margin: 20pt)\n'
           f'#set text(font: "{font}", size: 10pt{", dir: rtl" if rtl else ""})\n'
           '#set par(justify: false)\n'
           '#set list(marker: drawn-marker("dot", black), indent: 0pt, spacing: 1em, body-indent: 6pt)\n'
           f"{bullet}\n")
    typ = tmp_path / f"{name}.typ"
    typ.write_text(src, encoding="utf-8")
    out = tmp_path / f"{name}.pdf"
    typst.compile(str(typ), output=str(out))
    return make_context(str(typ), str(out), pdf.extract_text(str(out), "pdfium"), src, "pdfium", can_query=True)


def _fonts():
    return {f.lower() for f in typst.Fonts().families()} if hasattr(typst, "Fonts") else set()


def _bullets(first, rest):
    return f"- {first}{rest}\n- Second bullet, one line.\n"


@pytest.mark.parametrize("script", sorted(SCRIPTS))
def test_runt_fails_full_last_line_and_one_line_pass(tmp_path, script):
    font, first, closing, runt, rtl = SCRIPTS[script]
    runt_cv = _compile(tmp_path, "runt", font, _bullets(first, f" \\ {runt}"), rtl)
    out = _bullet_runts(runt_cv)
    assert [lvl for lvl, _ in out] == [Level.FAIL], out
    assert rtl or runt in out[0][1]   # the Arabic extraction reorders glyphs: only its verdict is asserted
    full = _compile(tmp_path, "full", font, _bullets(first, f" \\ {closing}"), rtl)
    assert _bullet_runts(full) == []
    one = _compile(tmp_path, "one", font, _bullets(runt, ""), rtl)
    assert _bullet_runts(one) == []


def test_runt_after_natural_wrap_fails(tmp_path):
    """No forced break: the text itself wraps and leaves one short word on the second line."""
    font, first, _, _, _ = SCRIPTS["latin"]
    for n in range(1, 60):   # widen the body one letter at a time until the wrap leaves a lone word
        ctx = _compile(tmp_path, "nat", font, f"- {first} {'x' * n} ms.\n", False)
        out = _bullet_runts(ctx)
        if out:
            assert out[0][0] == Level.FAIL
            assert "ms." in out[0][1]
            return
    pytest.fail("no width produced a lone last word")


def test_no_lib_marker_is_not_measured_never_a_fail(tmp_path):
    src = "#set page(width: 330pt, height: 200pt)\n- Plain list item that wraps onto the next line because it is long \\ ms.\n"
    typ = tmp_path / "plain.typ"
    typ.write_text(src, encoding="utf-8")
    out_pdf = tmp_path / "plain.pdf"
    typst.compile(str(typ), output=str(out_pdf))
    ctx = make_context(str(typ), str(out_pdf), pdf.extract_text(str(out_pdf), "pdfium"), src, "pdfium")
    out = _bullet_runts(ctx)
    assert [lvl for lvl, _ in out] == [Level.WARN]
    assert "not measured" in out[0][1]


def test_gate_is_registered_and_needs_the_query():
    assert "bullet-runts" in [g.name for g in LAYOUT_GATES]


def test_pypdf_fallback_downgrades_to_warn(tmp_path):
    font, first, _, runt, rtl = SCRIPTS["latin"]
    ctx = _compile(tmp_path, "pp", font, _bullets(first, f" \\ {runt}"), rtl)
    ctx = type(ctx)(**{**ctx.__dict__, "backend": "pypdf"})
    assert [lvl for lvl, _ in _bullet_runts(ctx)] == [Level.WARN]


# ---- the threshold, on synthetic lines (width in line heights of 10pt; widest line 400pt)
def _lines(last_w):
    full = BulletLine(1, Extent(0, 400), 10, "x")
    return [full, BulletLine(1, Extent(0, last_w), 10, "y")]


@pytest.mark.parametrize(("width", "expected"), [(15, True), (25, True), (26, False), (60, False), (200, False)])
def test_threshold_edge(width, expected):
    assert is_runt(_lines(width)) is expected


def test_wide_type_is_judged_against_the_bullet_too():
    """A last line short in line heights but not against a narrow column's widest line is not a runt."""
    narrow = [BulletLine(1, Extent(0, 100), 40, "x"), BulletLine(1, Extent(0, 50), 40, "y")]
    assert is_runt(narrow) is False


def test_single_line_is_never_a_runt():
    assert is_runt([BulletLine(1, Extent(0, 5), 10, "ms.")]) is False


def test_check_runts_without_query_warns():
    assert check_runts(None, "x.pdf", fail=lambda m: (Level.FAIL, m))[0][0] == Level.WARN

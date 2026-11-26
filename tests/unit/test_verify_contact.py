"""vitae.verify.contact: a contact block that takes more rows than its layout declares is a FAIL.

Tiny CVs importing the real lib.typ `nb`; rows are counted from item y only, so scripts, right-to-left
text and unspaced text are treated like any other."""
import shutil

import pytest
import typst
from _paths import ROOT
from vitae.core.level import Level
from vitae.verify.contact import check_contact_line, count_rows

TEMPLATES = ROOT / "templates"


def _check(tmp_path, body, lang="en", font="Libertinus Serif", rows=None, rtl=False):
    for name in ("lib.typ", "icons.typ"):
        shutil.copy(TEMPLATES / name, tmp_path / name)
    typ = tmp_path / "cv.typ"
    decl = f"#contact-rows({rows})\n" if rows else ""
    typ.write_text(f'#import "lib.typ": nb, contact-rows\n#set page(width: 300pt, height: 120pt)\n'
                   f'#set text(font: "{font}", lang: "{lang}", size: 10pt{", dir: rtl" if rtl else ""})\n{decl}{body}\n',
                   encoding="utf-8")
    typst.compile(str(typ), output=str(tmp_path / "cv.pdf"))
    return check_contact_line(str(typ), str(tmp_path))


def _items(words):
    return " ".join("#nb(none)[" + w.replace("@", "\\@") + "]" for w in words)


def test_one_row_passes(tmp_path):
    assert _check(tmp_path, _items(["Montreal", "555-0100", "me@x.org"]))[0][0] == Level.OK


def test_wrapped_single_row_fails(tmp_path):
    out = _check(tmp_path, _items(["Montreal", "514-555-0100", "maya@example.com", "linkedin.com/in/maya", "github.com/maya"]))
    assert out[0][0] == Level.FAIL and "wraps" in out[0][1]


def test_designed_multi_row_passes_and_extra_wrap_fails(tmp_path):
    col = "#nb(none)[a] \\ #nb(none)[b] \\ #nb(none)[c]"
    assert _check(tmp_path, col, rows=3)[0][0] == Level.OK
    assert _check(tmp_path, col, rows=2)[0][0] == Level.FAIL


def test_no_nb_item_is_not_measured(tmp_path):
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


@pytest.mark.parametrize("ys,n", [([], 0), ([10.0], 1), ([10.0, 11.4, 10.2], 1), ([10.0, 22.0], 2)])
def test_count_rows(ys, n):
    assert count_rows(ys) == n

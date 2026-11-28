"""No-split on real Typst layouts for CVs that are not built from the lib's section(): native `= Heading`
sections (split and unsplit), a CV with no section at all, and a lib CV next to a hand-written heading.
One compile and one query per document, on both toolchains."""
from __future__ import annotations

import shutil
from pathlib import Path

from harness import ROOT
from vitae.core.env import pdf_backend
from vitae.core.level import Level
from vitae.verify.gates import _native_headings, _no_split, make_context
from vitae.verify.pdf import extract_text, typst_compile

PAGE = '#set page(width: 12cm, height: 5cm, margin: 1cm)\n#set text(size: 10pt)\n'
LINES = "\n".join(f"- line {i} of the section" for i in range(7))
LIB = ('#import "lib.typ": *\n#let section = wd-section((t, body, airy: false) => block[#strong(t) \\ #body])\n')


def levels(tmp_path: Path, src: str, with_lib: bool = False) -> tuple[list[tuple[Level, str]], list[tuple[Level, str]]]:
    if with_lib:
        for f in ("lib.typ", "icons.typ"):
            shutil.copy(ROOT / "templates" / f, tmp_path)
    typ = tmp_path / "cv.typ"
    typ.write_text(src, encoding="utf-8")
    pdf = tmp_path / "cv.pdf"
    ok, err = typst_compile(str(typ), str(pdf))
    assert ok, err
    backend = pdf_backend()
    ctx = make_context(str(typ), str(pdf), extract_text(str(pdf), backend), src, backend, root=str(tmp_path))
    return _no_split(ctx), _native_headings(ctx)


def test_heading_only_cv_with_a_section_split_across_pages_fails(toolchain: str, tmp_path: Path) -> None:
    got, _ = levels(tmp_path, PAGE + f"= Profile\nShort.\n= Experience\n{LINES}\n")
    assert any(lvl == Level.FAIL and "SPLIT" in m for lvl, m in got), got


def test_heading_only_cv_with_sections_on_whole_pages_is_ok(toolchain: str, tmp_path: Path) -> None:
    got, warn = levels(tmp_path, PAGE + "= Profile\nShort.\n#pagebreak()\n= Experience\nShort.\n")
    assert got == [(Level.OK, 'no-split: page 2 opens on "Experience"')] and warn == [], got


def test_cv_with_no_marks_and_no_headings_fails(toolchain: str, tmp_path: Path) -> None:
    got, _ = levels(tmp_path, PAGE + "#strong[PROFILE]\nShort.\n#pagebreak()\n#strong[WORK]\nShort.\n")
    assert [lvl for lvl, _ in got] == [Level.FAIL] and "no section boundary" in got[0][1], got


def test_lib_cv_is_unchanged_and_has_no_native_warning(toolchain: str, tmp_path: Path) -> None:
    got, warn = levels(tmp_path, PAGE.replace("5cm", "3cm") + LIB + '#section("Profile")[Short.]\n#pagebreak()\n'
                       '#section("Work")[Short.]\n', with_lib=True)
    assert got == [(Level.OK, 'no-split: page 2 opens on "Work"')] and warn == [], got


def test_lib_cv_with_a_hand_written_heading_warns_by_position(toolchain: str, tmp_path: Path) -> None:
    _got, warn = levels(tmp_path, PAGE + LIB + '#section("Profile")[Short.]\n= Projects\nShort.\n', with_lib=True)
    assert len(warn) == 1 and warn[0][0] == Level.WARN and "heading #1 (page 1)" in warn[0][1], warn
    assert "Projects" not in warn[0][1]


def test_heading_with_inline_markup_keeps_its_spaces(toolchain: str, tmp_path: Path) -> None:
    got, _ = levels(tmp_path, PAGE + "= Profile\nShort.\n#pagebreak()\n== Edu *bold* x\nShort.\n")
    assert got == [(Level.OK, 'no-split: page 2 opens on "Edu bold x"')], got


def test_a_header_heading_on_every_page_does_not_hide_a_real_split(toolchain: str, tmp_path: Path) -> None:
    src = PAGE.replace("margin: 1cm", "margin: (x: 1cm, top: 1.6cm, bottom: 1cm), header: [= Running Title]") + \
        f"= Profile\nShort.\n= Experience\n{LINES}\n"
    got, _ = levels(tmp_path, src)
    assert any(lvl == Level.FAIL and "SPLIT" in m for lvl, m in got), got


def test_a_lib_cv_with_a_name_heading_has_no_hand_built_warning(toolchain: str, tmp_path: Path) -> None:
    _got, warn = levels(tmp_path, PAGE + LIB + '= Maya Okafor\n#section("Profile")[Short.]\n', with_lib=True)
    assert warn == [], warn

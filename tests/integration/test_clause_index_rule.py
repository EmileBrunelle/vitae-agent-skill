"""clause-index `section-rule`: every value compiles to one page with the same extracted text (the rule is a vector
line, never text), and a value outside the list is a compile error that names the valid ones."""
from __future__ import annotations

from pathlib import Path

import pytest
from vitae.core.env import pdf_backend
from vitae.verify.pdf import count_pages, extract_text, typst_compile

VALUES = ("inline", "under", "under-short", "none")
DEFAULT = '#let section-rule = "inline"'


def variant(scratch: Path, name: str, value: str) -> Path:
    fam = scratch / "templates" / "families" / "clause-index"
    src = (fam / f"{name}.typ").read_text(encoding="utf-8")
    assert src.count(DEFAULT) == 1, f"{name}.typ: the section-rule declaration moved"
    out = fam / f"_rule-{name}-{value}.typ"
    # no /CreationDate: Typst stamps it at 1 s resolution, which would make two compiles of one source differ
    out.write_text("#set document(date: none)\n" + src.replace(DEFAULT, f'#let section-rule = "{value}"'),
                   encoding="utf-8")
    return out


def build(typ: Path) -> tuple[bool, str, Path]:
    pdf = typ.with_suffix(".pdf")
    ok, err = typst_compile(str(typ), str(pdf))
    return ok, err, pdf


@pytest.mark.parametrize("name", ["resume", "resume-pair-b"])
def test_every_section_rule_is_one_page_and_text_neutral(scratch: Path, name: str) -> None:
    backend = pdf_backend()
    tokens: dict[str, list[str]] = {}
    for value in VALUES:
        ok, err, pdf = build(variant(scratch, name, value))
        assert ok, f"{name} section-rule={value}: {err}"
        assert count_pages(str(pdf), backend) == "1", f"{name} section-rule={value} is not one page"
        tokens[value] = sorted(extract_text(str(pdf), backend).split())
    for value in VALUES:
        assert tokens[value] == tokens["none"], f"section-rule={value} changed the extracted words"


@pytest.mark.parametrize("name", ["resume", "resume-pair-b"])
def test_each_value_draws_something_different(scratch: Path, name: str) -> None:
    # guards a value that silently falls through to another branch (e.g. to "none")
    ok, err, pdf = build(variant(scratch, name, "inline"))
    assert ok, err
    again = build(variant(scratch, name, "inline"))[2]
    assert pdf.read_bytes() == again.read_bytes(), "same source must compile to identical bytes"
    pdfs = {}
    for value in VALUES:
        ok, err, pdf = build(variant(scratch, name, value))
        assert ok, err
        pdfs[value] = pdf.read_bytes()
    assert len(set(pdfs.values())) == len(VALUES)


def test_unknown_section_rule_is_a_compile_error(scratch: Path) -> None:
    ok, err, _ = build(variant(scratch, "resume", "double"))
    assert not ok
    assert "section-rule must be one of" in err and "under-short" in err

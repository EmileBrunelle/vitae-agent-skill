"""PDF/UA-1 + PDF/A-2a: the PDF a compile writes is accessible and archival by declaration, and the pikepdf rewrite
(hex strings) that runs after Typst keeps every part of that declaration.

The documents are tiny generated Typst sources; no template and no font beyond Typst's own is needed."""
import importlib
import re
import shutil
from pathlib import Path

import pytest
from _paths import ROOT
from pypdf import PdfReader
from pypdf.generic import StreamObject
from vitae.verify import hexstrings, pdf

# 52 distinct glyphs: the 40th and 41st get the codes 0x28/0x29, so the raw content stream has nested parentheses and
# the hex rewrite really changes bytes (the positive control of the preservation test).
LETTERS = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
DOC = (f'#set document(title: "Jane Roe", author: "Jane Roe")\n#set text(lang: "fr", font: "Libertinus Serif")\n'
       f'#set page(width: 800pt, height: 80pt)\n= Experience\n{LETTERS}\n')


@pytest.fixture(params=[pytest.param("cli", marks=pytest.mark.skipif(not shutil.which("typst"), reason="typst CLI missing")),
                        "typst-py"])
def via(request, fake_typst):
    """The compile route under test: the CLI on PATH as the process sees it, or typst-py alone."""
    if request.param == "typst-py":
        fake_typst(api=pytest.importorskip("typst"))
needs_pikepdf = pytest.mark.skipif(hexstrings._pikepdf() is None, reason="pikepdf not installed (optional)")


def _write(tmp_path: Path, src: str, name: str = "a") -> Path:
    typ = tmp_path / f"{name}.typ"
    typ.write_text(src, encoding="utf-8")
    return typ


def declaration(path: Path) -> dict[str, object]:
    """What a PDF declares about being accessible/archival: structure tree, marked content, language, title, XMP parts."""
    root = PdfReader(str(path)).root_object
    metadata = root["/Metadata"].get_object()
    assert isinstance(metadata, StreamObject)
    xmp = metadata.get_data().decode("utf-8")
    mark = root.get("/MarkInfo")
    return {
        "struct": "/StructTreeRoot" in root,
        "marked": bool(mark and mark.get_object().get("/Marked")),
        "lang": str(root.get("/Lang")),
        "ua": re.findall(r"pdfuaid:part>(\d+)<", xmp) or re.findall(r'pdfuaid:part="(\d+)"', xmp),
        "pdfa": re.findall(r"pdfaid:part>(\d+)<", xmp) + re.findall(r"pdfaid:conformance>(\w+)<", xmp),
    }


EXPECTED: dict[str, object] = {"struct": True, "marked": True, "lang": "fr", "ua": ["1"], "pdfa": ["2", "A"]}


@pytest.mark.usefixtures("via")
def test_compiled_pdf_declares_pdf_ua_1_and_pdf_a_2a(tmp_path: Path) -> None:
    typ = _write(tmp_path, DOC)
    ok, err = pdf.compile_pdf(str(typ), str(tmp_path / "a.pdf"))
    assert ok, err
    assert declaration(tmp_path / "a.pdf") == EXPECTED


@pytest.mark.usefixtures("typst_api_only")
def test_a_document_without_a_title_does_not_compile(tmp_path: Path) -> None:
    """The control of the test above: it is the standard that makes Typst refuse, and the reason comes back."""
    typ = _write(tmp_path, DOC.replace('#set document(title: "Jane Roe", author: "Jane Roe")\n', ""))
    ok, err = pdf.compile_pdf(str(typ), str(tmp_path / "a.pdf"))
    assert not ok and "title" in err
    assert not (tmp_path / "a.pdf").exists()


@needs_pikepdf
def test_the_hex_rewrite_keeps_the_whole_declaration(tmp_path: Path) -> None:
    typ = _write(tmp_path, DOC)
    raw, final = tmp_path / "raw.pdf", tmp_path / "final.pdf"
    ok, err = pdf.typst_compile(str(typ), str(raw), standards=True)
    assert ok, err
    shutil.copy(raw, final)
    assert hexstrings.hexify_pdf(str(final))                # control: the rewrite did change the file
    pikepdf = importlib.import_module("pikepdf")

    def marked_content(path: Path) -> int:
        with pikepdf.open(path) as doc:
            return sum(1 for pg in doc.pages for op in pikepdf.parse_content_stream(pg) if str(op.operator) == "BDC")

    assert raw.read_bytes() != final.read_bytes()
    assert declaration(final) == declaration(raw) == EXPECTED
    assert marked_content(final) == marked_content(raw) > 0   # every MCID the structure tree points at is still there
    with pikepdf.open(raw) as a, pikepdf.open(final) as b:
        assert bytes(a.Root.Metadata.read_bytes()) == bytes(b.Root.Metadata.read_bytes())
        assert str(a.docinfo["/Title"]) == str(b.docinfo["/Title"]) == "Jane Roe"


# ---- lib.typ: decorative images are artifacts, so PDF/UA-1 does not ask for a description

ICON = '#import "lib.typ": *\n#set document(title: "T")\n#set text(lang: "en")\nName #pmark("<rect width=\\"10\\" height=\\"10\\" fill=\\"currentColor\\"/>", "0 0 10 10", red)\n'


def _lib_dir(tmp_path: Path) -> Path:
    for f in ("lib.typ", "icons.typ"):
        shutil.copy(ROOT / "templates" / f, tmp_path / f)
    return tmp_path


@pytest.mark.usefixtures("typst_api_only")
def test_a_contact_mark_compiles_under_the_standard(tmp_path: Path) -> None:
    ok, err = pdf.compile_pdf(str(_write(_lib_dir(tmp_path), ICON)), str(tmp_path / "a.pdf"))
    assert ok, err


@pytest.mark.usefixtures("typst_api_only")
def test_an_image_nobody_described_is_refused(tmp_path: Path) -> None:
    """Control for the mark above: the same image, not marked decorative, breaks PDF/UA-1."""
    bare = ('#set document(title: "T")\n#set text(lang: "en")\n'
            'Name #image(bytes("<svg xmlns=\'http://www.w3.org/2000/svg\' viewBox=\'0 0 1 1\'/>"), format: "svg")\n')
    ok, err = pdf.compile_pdf(str(_write(_lib_dir(tmp_path), bare)), str(tmp_path / "a.pdf"))
    assert not ok and "alt" in err


# ---------- the refusal says what to add (title / alt), same text from both backends ----------

PNG = bytes.fromhex("89504e470d0a1a0a0000000d49484452000000010000000108020000009077"
                    "53de0000000c4944415408d763f8cfc000000301010018dd8db00000000049454e44ae426082")
TITLE = '#set document(title: "Jane Roe")\n'


def _compile(tmp_path: Path, src: str) -> tuple[bool, str]:
    (tmp_path / "a.png").write_bytes(PNG)
    return pdf.compile_pdf(str(_write(tmp_path, src)), str(tmp_path / "a.pdf"))


@pytest.mark.usefixtures("via")
def test_a_missing_title_fails_with_the_line_to_add(tmp_path: Path) -> None:
    ok, err = _compile(tmp_path, "Hello\n")
    assert not ok
    assert err.startswith("FAIL  vitae:")
    assert '#set document(title: "<name>")' in err and "doc-name" in err
    assert "alt:" not in err                      # the cause is the title: no unrelated advice
    assert "missing document title" in err        # Typst's own error follows


@pytest.mark.usefixtures("via")
def test_an_image_without_alt_fails_with_the_fix(tmp_path: Path) -> None:
    ok, err = _compile(tmp_path, TITLE + '#image("a.png")\n')
    assert not ok
    assert err.startswith("FAIL  vitae:")
    assert 'alt: "' in err and "pdf.artifact(image(" in err
    assert "document(title" not in err.split("Typst's own error follows.")[0]
    assert "missing alt text" in err


@pytest.mark.usefixtures("via")
def test_a_conformant_cv_shows_no_fail(tmp_path: Path) -> None:
    """Positive control of the two tests above: title + described image + artifact image compile with no message."""
    src = TITLE + '#image("a.png", alt: "Logo")\n#pdf.artifact(image("a.png"))\n'
    assert _compile(tmp_path, src) == (True, "")


@pytest.mark.usefixtures("typst_api_only")
def test_an_error_that_is_not_the_standards_gets_no_vitae_advice(tmp_path: Path) -> None:
    ok, err = _compile(tmp_path, TITLE + '#image("missing.png", alt: "x")\n')
    assert not ok and "FAIL  vitae" not in err


NEUTRAL = "Typst refused the PDF/UA-1 + PDF/A-2a output; its hint below says what to change"


def test_a_pdf_a_2a_only_refusal_is_recognised() -> None:
    """The standard name has a lower-case letter (`PDF/A-2a`): the refusal is still a standard's, with the right fix."""
    advice = pdf.standard_failure_advice("error: PDF/A-2a error: missing document title\n")
    assert advice.startswith("FAIL  vitae:") and "doc-name" in advice and "alt:" not in advice


def test_a_mixed_refusal_is_recognised() -> None:
    advice = pdf.standard_failure_advice("error: PDF/UA-1, PDF/A-2a error: missing alt text for image\n")
    assert advice.startswith("FAIL  vitae:") and "pdf.artifact(image(" in advice and "doc-name" not in advice


@pytest.mark.parametrize("what", ["something new", "an alt-ernative cause", "the title of nothing"],
                         ids=["unknown", "bare-alt-substring", "bare-title-substring"])
def test_an_unrecognised_refusal_gets_the_neutral_line_and_no_fix(what: str) -> None:
    advice = pdf.standard_failure_advice(f"error: PDF/UA-1 error: {what}")
    assert NEUTRAL in advice and what in advice
    assert "document(title" not in advice and "alt:" not in advice and "To fix" not in advice


@pytest.mark.usefixtures("via")
def test_a_skipped_heading_level_gets_the_neutral_line(tmp_path: Path) -> None:
    ok, err = _compile(tmp_path, TITLE + "= A\n=== B\n")
    assert not ok and err.startswith("FAIL  vitae:") and NEUTRAL in err
    assert "skipped from heading level 1 to 3" in err and "To fix" not in err


@pytest.mark.usefixtures("via")
def test_a_private_use_codepoint_gets_the_neutral_line(tmp_path: Path) -> None:
    ok, err = _compile(tmp_path, TITLE + '#set text(font: "Libertinus Serif")\n= A\n\uE000 x\n')
    assert not ok and err.startswith("FAIL  vitae:") and NEUTRAL in err
    assert "To fix" not in err

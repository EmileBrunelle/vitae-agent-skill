"""vitae.verify.hexstrings: Typst's TJ literal strings can hold balanced unescaped parentheses (2-byte glyph codes
0x28 and 0x29 side by side), which PHP's smalot/pdfparser truncates; the optional pikepdf step rewrites them as hex.

The PDF is generated: the 40th and 41st distinct glyphs of a Typst document get the codes 0x28 and 0x29."""
import builtins
import importlib

import pytest
import typst
from vitae.verify import hexstrings, pdf

LETTERS = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"     # 52 distinct glyphs, codes 1..52
SRC = f'#set document(title: "T", author: "A")\n#set text(lang: "fr", font: "Libertinus Serif")\n#set page(width: 800pt, height: 60pt)\n{LETTERS}\n'

needs_pikepdf = pytest.mark.skipif(not hexstrings.available(), reason="pikepdf not installed (optional)")


def nested_parens(raw: bytes) -> bool:
    """True when a literal string of the content stream contains an unescaped `(`: the shape smalot cuts at."""
    depth, i = 0, 0
    while i < len(raw):
        c = raw[i:i + 1]
        if c == b"\\" and depth:
            i += 1
        elif c == b"(":
            depth += 1
            if depth > 1:
                return True
        elif c == b")" and depth:
            depth -= 1
        i += 1
    return False


def page_content(path: str) -> bytes:
    pikepdf = importlib.import_module("pikepdf")
    with pikepdf.open(path) as doc:
        return bytes(doc.pages[0].Contents.read_bytes())


def keep_bytes(path: str) -> tuple[bytes, bytes]:
    """The catalog /Lang and the XMP packet, byte for byte."""
    pikepdf = importlib.import_module("pikepdf")
    with pikepdf.open(path) as doc:
        return str(doc.Root.Lang).encode(), bytes(doc.Root.Metadata.read_bytes())


def pdfium_text(path: str) -> str:
    doc = importlib.import_module("pypdfium2").PdfDocument(path)
    return "\n".join(p.get_textpage().get_text_range() for p in doc)


@pytest.fixture
def paren_pdf(tmp_path):
    typ = tmp_path / "a.typ"
    typ.write_text(SRC, encoding="utf-8")
    out = tmp_path / "a.pdf"
    typst.compile(str(typ), output=str(out))
    return out


def test_the_fixture_really_has_the_smalot_shape(paren_pdf):
    """Without this the other tests would pass on any PDF."""
    pytest.importorskip("pikepdf")
    assert nested_parens(page_content(str(paren_pdf)))


@needs_pikepdf
class TestWithPikepdf:
    def test_no_literal_string_with_parens_remains_and_text_is_unchanged(self, paren_pdf):
        before = pdfium_text(str(paren_pdf))
        assert hexstrings.hexify_pdf(str(paren_pdf)) is True
        assert not nested_parens(page_content(str(paren_pdf)))
        assert pdfium_text(str(paren_pdf)) == before
        assert LETTERS in before.replace("\r", "").replace("\n", "")

    def test_lang_and_xmp_bytes_are_unchanged(self, paren_pdf):
        before = keep_bytes(str(paren_pdf))
        hexstrings.hexify_pdf(str(paren_pdf))
        assert keep_bytes(str(paren_pdf)) == before

    def test_second_run_is_a_byte_identical_no_op(self, paren_pdf):
        hexstrings.hexify_pdf(str(paren_pdf))
        first = paren_pdf.read_bytes()
        assert hexstrings.hexify_pdf(str(paren_pdf)) is False
        assert paren_pdf.read_bytes() == first

    def test_mutation_without_the_rewrite_the_parens_stay(self, paren_pdf, monkeypatch):
        """The content test is only worth something if disabling the rewrite makes it fail."""
        monkeypatch.setattr(hexstrings, "_rewrite", lambda pk, doc: False)
        assert hexstrings.hexify_pdf(str(paren_pdf)) is False
        assert nested_parens(page_content(str(paren_pdf)))

    def test_a_file_that_is_not_a_pdf_is_left_alone(self, tmp_path):
        bad = tmp_path / "x.pdf"
        bad.write_bytes(b"not a pdf")
        assert hexstrings.hexify_pdf(str(bad)) is False
        assert bad.read_bytes() == b"not a pdf"
        assert list(tmp_path.iterdir()) == [bad]       # no temp file left behind

    def test_compile_pdf_delivers_the_hexified_file(self, tmp_path):
        typ = tmp_path / "a.typ"
        typ.write_text(SRC, encoding="utf-8")
        ok, _ = pdf.compile_pdf(str(typ), str(tmp_path / "a.pdf"), use_cli=False)
        assert ok and not nested_parens(page_content(str(tmp_path / "a.pdf")))


def test_without_pikepdf_the_file_is_byte_identical(paren_pdf, monkeypatch):
    real_import = builtins.__import__
    real_import_module = importlib.import_module

    def no_pikepdf(name, *a, **k):
        if name == "pikepdf":
            raise ImportError(name)
        return real_import(name, *a, **k)

    def no_pikepdf_module(name, *a, **k):
        if name == "pikepdf":
            raise ImportError(name)
        return real_import_module(name, *a, **k)

    before = paren_pdf.read_bytes()
    monkeypatch.setattr(builtins, "__import__", no_pikepdf)
    monkeypatch.setattr(importlib, "import_module", no_pikepdf_module)
    assert hexstrings.available() is False
    assert hexstrings.hexify_pdf(str(paren_pdf)) is False
    monkeypatch.undo()
    assert paren_pdf.read_bytes() == before

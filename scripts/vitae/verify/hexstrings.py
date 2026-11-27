"""Optional post-step on a compiled PDF: rewrite the text strings of its content streams as hex.

Typst writes each TJ string as a PDF literal string whose 2-byte glyph codes can contain balanced, unescaped
`(` `)` bytes. That is legal PDF, but smalot/pdfparser (PHP, issue #860) stops reading the string there and
loses whole headings. pikepdf's content-stream serializer writes strings as `<hex>`, which every parser reads
the same way. Text, rendering, links, outline, /Lang and XMP are unchanged (measured on 51 PDFs).

pikepdf is optional: without it, or when the file cannot be rewritten, the PDF is left untouched. Running the
step twice changes nothing the second time (the rewritten bytes are a fixed point of the serializer).
Floor: pikepdf 10.8.0 (python3-pikepdf on Fedora); only `open`, `parse_content_stream`, `unparse_content_stream`,
`make_stream`, `Stream.write` and the `save` keywords used below are needed.
"""
from __future__ import annotations

import importlib
import os
from types import ModuleType


def _pikepdf() -> ModuleType | None:
    try:
        return importlib.import_module("pikepdf")
    except ImportError:
        return None


def available() -> bool:
    return _pikepdf() is not None


def _rewrite(pk: ModuleType, pdf: ModuleType) -> bool:
    """Re-serialise every page's /Contents and every Form XObject stream; True when a byte changed.
    `pdf` is a pikepdf.Pdf (typed as a module: pikepdf is imported by name, so its objects are untyped here)."""
    changed = False
    for page in pdf.pages:
        contents = page.obj.get("/Contents")
        if contents is None:
            continue
        old = b"\n".join(s.read_bytes() for s in contents) if isinstance(contents, pk.Array) else contents.read_bytes()
        new = pk.unparse_content_stream(pk.parse_content_stream(page))
        if new != old:
            page.Contents = pdf.make_stream(new)
            changed = True
    for obj in pdf.objects:
        if isinstance(obj, pk.Stream) and obj.get("/Subtype") == "/Form":
            old = obj.read_bytes()
            new = pk.unparse_content_stream(pk.parse_content_stream(obj))
            if new != old:
                obj.write(new)
                changed = True
    return changed


def hexify_pdf(path: str) -> bool:
    """Rewrite `path` in place with hex strings. True when the file was rewritten; False when it was left as
    it was: pikepdf absent, nothing to change, or any failure (this step never turns a good compile into an error)."""
    pk = _pikepdf()
    if pk is None:
        return False
    tmp = path + ".hex.tmp"
    try:
        with pk.open(path) as pdf:
            if not _rewrite(pk, pdf):
                return False
            pdf.save(tmp, compress_streams=True, recompress_flate=True,
                     object_stream_mode=pk.ObjectStreamMode.preserve, fix_metadata_version=False)
        os.replace(tmp, path)
        return True
    except Exception:   # kept broad: pikepdf raises its own PdfError family, OSError, ValueError; the original PDF stays as compiled
        return False
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)

"""Optional post-step on a compiled PDF: re-serialise the text strings of its content streams.

Typst writes each TJ string as a PDF literal string whose 2-byte glyph codes can contain balanced, unescaped
`(` `)` bytes. That is legal PDF, but smalot/pdfparser (PHP, issue #860) stops reading the string there and
loses whole headings. pikepdf's content-stream serializer re-serialises every string so that each parenthesis is
escaped (`(a\\(b\\)c)`) or the string is hex (`<...>`, for non-printable bytes), which every parser reads the same way. Text, rendering, links, outline, /Lang and XMP are unchanged (measured on 51 PDFs).

pikepdf is optional (`uv run` installs it from the scripts' PEP 723 blocks; else `pip install "pikepdf>=10.8.0"`): without it, or when the file cannot be rewritten, the PDF is left untouched. Running the
step twice changes nothing the second time (the rewritten bytes are a fixed point of the serializer).
Streams rewritten: page /Contents, Form XObjects and tiling patterns (/PatternType 1). Type3 CharProcs are not
(Typst does not emit text there). Floor: pikepdf 10.8.0 (python3-pikepdf on Fedora; older versions are skipped); only `open`, `parse_content_stream`, `unparse_content_stream`,
`make_stream`, `Stream.write` and the `save` keywords used below are needed.
"""
from __future__ import annotations

import importlib
import os
import sys
from types import ModuleType

MIN_VERSION = (10, 8, 0)
_warned = False


def version_tuple(v: str) -> tuple[int, ...]:
    """The leading numeric components of a version string ("10.8.0rc1" gives (10, 8, 0)); () when none."""
    out: list[int] = []
    for part in v.split(".")[:3]:
        digits = ""
        for ch in part:
            if not ch.isdigit():
                break
            digits += ch
        if not digits:
            break
        out.append(int(digits))
    return tuple(out)


def _pikepdf() -> ModuleType | None:
    """pikepdf when importable and at least MIN_VERSION, else None."""
    try:
        mod = importlib.import_module("pikepdf")
    except ImportError:
        return None
    if version_tuple(str(getattr(mod, "__version__", ""))) < MIN_VERSION:
        return None
    return mod


def _warn_once(exc: Exception) -> None:
    global _warned
    if not _warned:
        _warned = True
        print(f"WARN  hexstrings: PDF left as compiled ({type(exc).__name__})", file=sys.stderr)


def _rewrite(pk: ModuleType, pdf: ModuleType) -> bool:
    """Re-serialise every page's /Contents and every Form XObject and tiling-pattern stream; True when a byte changed.
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
        if isinstance(obj, pk.Stream) and (obj.get("/Subtype") == "/Form" or obj.get("/PatternType") == 1):
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
    except Exception as e:   # kept broad: pikepdf raises its own PdfError family, OSError, ValueError; the original PDF stays as compiled
        _warn_once(e)
        return False
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)

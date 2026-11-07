"""Typst compile, page count and PNG render, native CLI or typst-py (a leaf under verify_env: no `import verify`).

Only the helpers verify_tune needs live here so far; the rest of the compile / extract / render code follows.
Moved out of verify.py unchanged, re-exported there under the same names.
"""
from __future__ import annotations

import glob
import importlib
import os
import re
import subprocess
from typing import Any

from verify_env import PdfBackend, typst_font_kw
from verify_typst import _strip_typst_comments

# ---------- compile / page-count / extraction, native or fallback ----------

def auto_root(typ: str) -> str | None:
    """Typst project root a file needs, or None for the default (its own folder).

    The reference family files import the shared mechanics by relative path
    (`#import "../../lib.typ"`), which Typst refuses unless `--root` is an ancestor
    holding both. Climb as many levels as the deepest leading `../` of a
    non-comment import; a CV folder (`#import "lib.typ"`) needs nothing."""
    try:
        with open(typ, encoding="utf-8-sig", errors="replace") as fh:
            src = _strip_typst_comments(fh.read())
    except OSError:
        return None
    ups = max((len(m.group(1)) // 3 for m in re.finditer(r'\bimport\s*\(?\s*"((?:\.\./)+)[^"]*\.typ"', src)), default=0)
    root = os.path.dirname(os.path.abspath(typ))
    for _ in range(ups):
        root = os.path.dirname(root)
    return root if ups else None


# auto_root as a typst-py keyword and as CLI flags; empty when the default root (the file's own folder) is right.
def _root_kw(typ: str) -> dict[str, str]:
    r = auto_root(typ)
    return {"root": r} if r else {}


def _root_cli(typ: str) -> list[str]:
    r = auto_root(typ)
    return ["--root", r] if r else []


def compile_pdf(typ: str, pdf: str, use_cli: bool) -> tuple[bool, str]:
    """Returns (ok, stderr_text)."""
    if use_cli:
        r = subprocess.run(["typst", "compile", os.path.abspath(typ), os.path.abspath(pdf)] + _root_cli(typ), capture_output=True, text=True)
        return r.returncode == 0, (r.stdout + r.stderr)
    try:
        typst: Any = importlib.import_module("typst")
        typst.compile(typ, output=pdf, **_root_kw(typ), **typst_font_kw())
        return True, ""
    except Exception as e:
        return False, str(e)


def render_pngs(typ: str, tmp_dir: str, use_cli: bool) -> list[str]:
    """One 90 ppi PNG per page, the raster the fill scan reads (the hidden-text gate renders its own, at HIDDEN_PPI).
    The second typst-py call is for a version whose compile() does not take `ppi`."""
    pattern = os.path.join(tmp_dir, "p{p}.png")
    if use_cli:
        subprocess.run(["typst", "compile", os.path.abspath(typ), os.path.abspath(pattern), "--format", "png", "--ppi", "90"] + _root_cli(typ),
                        capture_output=True, text=True)
    else:
        typst: Any = importlib.import_module("typst")
        try:
            typst.compile(typ, output=pattern, format="png", ppi=90, **_root_kw(typ), **typst_font_kw())
        except TypeError:
            typst.compile(typ, output=pattern, format="png", **_root_kw(typ), **typst_font_kw())
    return sorted(glob.glob(os.path.join(tmp_dir, "p*.png")))


def _pdfium_doc(pdf: str) -> Any:
    return importlib.import_module("pypdfium2").PdfDocument(pdf)


def count_pages(pdf: str, backend: PdfBackend) -> str | None:
    """The page count as text, compared with EXPECTED_PAGES as text; None when pdfinfo prints no Pages line."""
    if backend == "pdfium":
        return str(len(_pdfium_doc(pdf)))
    if backend == "poppler":
        out = subprocess.run(["pdfinfo", pdf], capture_output=True, text=True).stdout
        for line in out.splitlines():
            if line.startswith("Pages:"):
                return line.split()[1]
        return None
    pypdf: Any = importlib.import_module("pypdf")
    return str(len(pypdf.PdfReader(pdf).pages))

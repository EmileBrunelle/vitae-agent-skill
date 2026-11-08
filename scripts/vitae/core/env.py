"""Dependency preflight ("doctor") and the typst-py / typst CLI probes (a leaf under verify_base: no `import verify`).

Tests that patch `subprocess.run` / `shutil.which` for it target this module's own `shutil` / `subprocess`.
"""
from __future__ import annotations

import contextlib
import functools
import importlib
import importlib.metadata
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import sysconfig
import tempfile
from types import ModuleType
from typing import Literal, TextIO, cast

# ---------- dependency preflight ("doctor") ----------

def check_pillow() -> bool:
    """Doctor line for Pillow, which the fill, text-clip, hidden-text and crop measurements read rasters through:
    without it the doctor fails."""
    try:
        import PIL  # noqa: F401
        print(f"OK    Pillow {PIL.__version__}")
        return True
    except ImportError:
        print("MISSING  Pillow -- needed for the page-fill measurement:")
        print("  sudo dnf install python3-pillow | sudo apt install python3-pil   # distro Python: official repos first (PEP 668)")
        print("  uv pip install Pillow | pip3 install --user Pillow               # venvs / pip-only environments")
        return False


# Oldest typst the fill targets were calibrated on; an older one still works and is reported DEGRADED, not refused.
TYPST_MIN = (0, 15)
_NEW_TYPST = ("fill targets are calibrated on typst 0.15; newer versions may measure differently "
              "-- pin with pip install typst==0.15.0 if fills drift")
_OLD_TYPST = ("fill targets are calibrated on typst 0.15; older versions measure lower "
              "(0.13/0.14 miss 2 templates at 91% against 93-96%)")


def _wheel_platform_tag() -> str:
    """The running interpreter's most specific wheel platform tag (e.g. manylinux_2_28_x86_64,
    macosx_14_0_arm64, win_amd64): from packaging/pip's tag list when importable, else sysconfig."""
    for mod in ("packaging.tags", "pip._vendor.packaging.tags"):
        try:
            tags = importlib.import_module(mod)
            return str(next(iter(tags.sys_tags())).platform)
        except Exception:
            continue
    return re.sub(r"[-.]", "_", sysconfig.get_platform())


def check_typst() -> tuple[bool, bool]:
    """Doctor lines for typst; returns (available, use_cli). The CLI is preferred, the Python API is the fallback and
    is judged by running it, not by its attributes. Older than TYPST_MIN, or a Python API without query/fonts, is
    DEGRADED (still available); a broken or missing install is not."""
    if shutil.which("typst"):
        try:
            ver = subprocess.run(["typst", "--version"], capture_output=True, text=True).stdout.split()[1]
        except Exception:
            ver = "?"
        if ver != "?" and _ver_tuple(ver) < TYPST_MIN:
            print(f"DEGRADED  typst {ver} (CLI): {_OLD_TYPST}.")
            print("  Upgrade with ONE of:")
            print("  pip install typst==0.15.0   # no root: add --user, or use a venv; pip picks the CPU architecture")
            print("  brew upgrade typst | cargo install typst-cli --force | winget upgrade Typst.Typst")
            print("  distro packages (dnf, apt, pacman) may be older: check `typst --version` after")
            return True, True
        print(f"OK    typst {ver} (CLI)")
        if ver != "?" and _ver_tuple(ver) > TYPST_MIN:
            print(f"  NOTE: {_NEW_TYPST}.")
        return True, True
    mod, ver, why, full = _typst_py_probe()
    if mod is None and why.startswith("TOOLOLD"):
        print(f"BROKEN  typst: the Python package `typst` is too old ({why[len('TOOLOLD '):]}).")
        print("  Upgrade it: pip install typst==0.15.0   # or install the CLI (brew install typst | cargo install typst-cli)")
        return False, False
    if mod is None and why:
        print(f"BROKEN  typst: the Python package `typst` is installed but does not work ({why}).")
        print("  Reinstall it: pip install --force-reinstall typst   # or install the CLI (brew install typst | cargo install typst-cli)")
        return False, False
    if mod is not None and not full:
        print("DEGRADED  typst: Python API only, no typst CLI. Compiling and fill measurement work, but these checks are SKIPPED (WARN):")
        print("  - date adjacency (needs `typst query`, and pdftotext)")
        print("  - group proximity (needs `typst query` and pdftotext)")
        print("  - the design font-availability check of pick_design.py (needs `typst fonts`)")
        print("  Install the CLI with ONE of (the pip package `typst` is the Python API only, it ships no CLI):")
        print("  brew install typst | cargo install typst-cli")
        print("  winget install --id Typst.Typst | choco install typst | scoop install typst   # Windows")
        return True, False
    if mod is not None:
        if _ver_tuple(ver) < TYPST_MIN:
            print(f"DEGRADED  typst {ver} (Python API): {_OLD_TYPST}.")
            print("  pip install typst==0.15.0")
            return True, False
        print(f"OK    typst {ver} (Python API: compile, query, fonts)")
        if _ver_tuple(ver) > TYPST_MIN:
            print(f"  NOTE: {_NEW_TYPST}.")
        return True, False
    print("MISSING  typst -- install with ONE of:")
    print("  pip install typst==0.15.0                    # no root (--user or a venv); no CLI needed: compiles, queries and lists fonts via the Python API")
    print("  brew install typst                          # macOS")
    print("  winget install --id Typst.Typst             # Windows")
    print("  choco install typst | scoop install typst   # Windows, if you already use them")
    print("  cargo install typst-cli                      # any, via Rust")
    print("  (distro packages — dnf, apt, pacman — may be older than 0.15, the version the fill targets are calibrated on)")
    print("  OFFLINE sandbox (no DNS / pip index)? On the user's own machine run:")
    plat, pyver = _wheel_platform_tag(), f"{sys.version_info.major}.{sys.version_info.minor}"
    print(f"    pip download typst==0.15.0 --no-deps --only-binary=:all: --platform {plat} --python-version {pyver}")
    print("    (if that platform has no wheel, `python3 -m pip debug --verbose` lists every compatible tag; never install a wheel built for another platform)")
    print("    (or pick the matching wheel from https://pypi.org/project/typst/#files), upload the .whl, then:")
    print("    pip install --no-index <path-to-wheel>")
    return False, False


PdfBackend = Literal["poppler", "pdfium", "pypdf"] | None


@functools.lru_cache(maxsize=None)
def _importable(name: str) -> bool:
    """True when `name` really imports (find_spec says only that a file exists: a broken
    wheel or a missing shared library passes it and then fails on first use)."""
    try:
        importlib.import_module(name)
        return True
    except Exception:
        return False


def pdf_backend() -> PdfBackend:
    """The PDF reader every check uses: poppler when pdfinfo and pdftotext are on PATH
    (the reference), else pypdfium2 (text, word boxes, raster, metadata and attachments in
    Python: close to poppler, not identical, see the CHANGELOG for where it differs), else
    pypdf (page count and indicative text only: it splits words), else None. A module that
    does not import is not selected, the doctor tests it the same way."""
    if shutil.which("pdfinfo") and shutil.which("pdftotext"):
        return "poppler"
    for name, backend in (("pypdfium2", "pdfium"), ("pypdf", "pypdf")):
        if _importable(name):
            return cast(PdfBackend, backend)
    return None


def pdf_tool(name: str) -> bool:
    """True when `name` (pdftotext, pdftoppm, pdfdetach) can be served: on PATH, or by pypdfium2."""
    return bool(shutil.which(name)) or pdf_backend() == "pdfium"


def check_pdf_tools() -> tuple[bool, PdfBackend]:
    """Doctor lines for the PDF reader; returns (available, backend), the backend being the one pdf_backend() would
    pick. A missing pdftoppm, or pypdf standing in for poppler, only degrades: the checks it cannot serve are named
    in the output."""
    if shutil.which("pdfinfo") and shutil.which("pdftotext"):
        if not shutil.which("pdftoppm"):
            print("DEGRADED  poppler-utils: pdftotext and pdfinfo found, pdftoppm missing. SKIPPED (WARN):")
            print("  - hidden-text ink check (also used by verify_letter.py / verify_academic.py)")
            print("  Weaker without a WARN: group proximity falls back to the pdftotext box gap instead of the ink gap")
            print("  poppler (academic mode only): install `poppler-utils` (or `poppler`) with the system package manager")
            return True, "poppler"
        print("OK    poppler-utils (pdftotext, pdfinfo, pdftoppm)")
        return True, "poppler"
    if _importable("pypdfium2"):
        try:
            ver = importlib.metadata.version("pypdfium2")
        except importlib.metadata.PackageNotFoundError:
            ver = "?"
        print(f"OK    pdf: pypdfium2 {ver} (Python: text, word boxes, raster, metadata, attachments)")
        print("  - academic mode still needs poppler (verify_academic.py reads `pdftotext -layout`)")
        return True, "pdfium"
    if _importable("pypdf"):
        print("DEGRADED  pypdf: Python fallback, no poppler. Page count is exact, but:")
        print("  - ATS text extraction is indicative only (spurious spaces, e.g. \"FORMA TION\")")
        print("  - SKIPPED (WARN): hidden-text gate and text-clip gate (need pdftotext and pdftoppm)")
        print("  - SKIPPED (WARN): group proximity and date adjacency (need pdftotext)")
        print("  - academic mode cannot run (verify_academic.py requires pdftotext)")
        print("  - `pip install pypdfium2`: text, word boxes, raster and metadata then run in Python close to poppler's (see the CHANGELOG)")
        print("  poppler (academic mode only): install `poppler-utils` (or `poppler`) with the system package manager")
        return True, "pypdf"
    else:
        print("MISSING  poppler-utils -- needed for page-count and ATS extraction checks:")
        print("  brew install poppler | sudo dnf install poppler-utils | sudo apt install poppler-utils")
        print("  choco install poppler | scoop install poppler          # Windows")
        print("  pip install pypdfium2                                  # fallback: text, boxes, raster and metadata in Python, close to poppler's (used automatically if present)")
        print("  pip install pypdf                                      # last resort: exact page count, indicative extraction only (used automatically if present)")
        return False, None


def check_fonts() -> None:
    """Doctor line for fonts (typst CLI or typst-py; local, no network, 20 s cap).

    Reuses pick_design's own logic: a design family is usable when every role of
    its pool has at least one installed member (`_installed`). pick_design
    draws from at least MIN_POOL families, so fewer usable ones means it will
    substitute."""
    import vitae.design.fonts as design_fonts
    from vitae.design.tables import FONTS, MIN_POOL
    have = design_fonts._fonts_available()
    if have is None:
        print("WARN  fonts not checked (`typst fonts` failed or timed out)")
        return
    pools = FONTS
    usable = sum(1 for f in pools if design_fonts._family_usable(f, have))
    if usable < MIN_POOL:
        print(f"DEGRADED  fonts: only {usable} of {len(pools)} design families have their fonts installed "
              f"(pick_design draws from at least {MIN_POOL}), so it will substitute.")
        print("  Fetch only the fonts the draw asks for (references/fonts.md, \"Downloading from Google Fonts\"):")
        r2 = ("typst --font-path <dir> (no install)" if shutil.which("typst")
              else "export TYPST_FONT_PATHS=<dir> (no install; the Python API reads it here)")
        print(f"  Route 1: install into ~/.local/share/fonts/vitae (persistent, recommended); Route 2: {r2}")
    else:
        print(f"OK    fonts ({usable} of {len(pools)} design families have an installed face for every role; a drawn face may still be substituted, {len(have)} families)")


class _CountDegraded:
    """stdout wrapper: counts the doctor lines that start with DEGRADED, so no path can print one and still end on an
    OK summary, whichever check wrote it."""
    def __init__(self, inner: TextIO) -> None:
        self.inner, self.n, self._bol = inner, 0, True

    def write(self, text: str) -> int:
        for part in text.splitlines(keepends=True):
            if self._bol and part.startswith("DEGRADED"):
                self.n += 1
            self._bol = part.endswith("\n")
        return int(self.inner.write(text))

    def flush(self) -> None:
        self.inner.flush()

    def __getattr__(self, name: str) -> object:
        return getattr(self.inner, name)


def preflight() -> tuple[bool, bool, PdfBackend]:
    """Print the doctor output; returns (all_ok, use_cli_typst, pdf_backend). all_ok is False only when something
    has no fallback (Pillow, typst, a PDF reader); DEGRADED lines leave it True."""
    counter = _CountDegraded(sys.stdout)
    with contextlib.redirect_stdout(cast(TextIO, counter)):
        pillow_ok = check_pillow()
        typst_ok, use_cli = check_typst()
        if use_cli or typst_py() is not None:
            check_fonts()
        pdf_ok, backend = check_pdf_tools()
        all_ok = pillow_ok and typst_ok and pdf_ok
        pypdf_missing = backend in ("poppler", "pdfium") and not _importable("pypdf")
        if pypdf_missing:
            # the WARN check_hidden_text prints for this backend, quoted so the doctor and the gate agree
            skipped = ("the tiny-text check of the hidden-text gate will NOT run "
                       "(WARN \"tiny-text check not run (pypdf missing)\")" if backend == "pdfium" else
                       "the off-page check of the hidden-text gate will NOT run "
                       "(WARN \"hidden text: off-page check not run (pypdf missing)\")")
            print(f"DEGRADED  pypdf: not installed. {skipped}. Fix: pip install pypdf")
        if (all_ok and not counter.n and not use_cli and backend == "pdfium" and typst_py() is not None
                and _ver_tuple(_typst_py_probe()[1]) >= TYPST_MIN):
            print("OK (Python)  no typst CLI, no poppler: compile, query, fonts, text, boxes and raster all run in Python "
                  "(typst-py + pypdfium2 + pypdf + Pillow); academic mode still needs poppler")
    return all_ok, use_cli, backend


def typst_font_kw() -> dict[str, list[str]]:
    """typst-py keyword for the font route of references/fonts.md: TYPST_FONT_PATHS (what the
    CLI reads on its own) as `font_paths`; typst-py ignores the variable, so pass it by hand."""
    fp = [p for p in os.environ.get("TYPST_FONT_PATHS", "").split(os.pathsep) if p]
    return {"font_paths": fp} if fp else {}


def _ver_tuple(v: str) -> tuple[int, int]:
    """(major, minor) of the first `X.Y` in `v`; (0, 0) when there is none, which reads as older than TYPST_MIN."""
    m = re.search(r"(\d+)\.(\d+)", v)
    return (int(m.group(1)), int(m.group(2))) if m else (0, 0)


@functools.lru_cache(maxsize=None)
def _typst_py_probe() -> tuple[ModuleType | None, str, str, bool]:
    """(module, version, problem, full) for the `typst` Python package, by running it: a tiny
    document is compiled and an expression evaluated, so a broken wheel is reported broken
    (an attribute check passes it). module None + problem "" = not installed; module None +
    problem = installed but unusable; full = also query, eval and Fonts."""
    try:
        mod = importlib.import_module("typst")   # ModuleType: attribute access is untyped (no stubs)
    except ImportError:
        return None, "", "", False
    except Exception as e:
        return None, "", f"import failed: {e}", False
    comp_cls = getattr(mod, "Compiler", None)
    if comp_cls is not None and not hasattr(comp_cls, "compile_with_warnings"):
        # a working but old wheel (typst-py 0.11.x): the API this script drives is newer
        return None, "", f"TOOLOLD typst {getattr(mod, '__version__', '?')}: its Compiler has no compile_with_warnings", False
    try:
        with tempfile.TemporaryDirectory() as td:
            src = os.path.join(td, "probe.typ")
            with open(src, "w", encoding="utf-8") as fh:
                fh.write("#set page(width: 50pt, height: 50pt)\nprobe\n")
            comp = mod.Compiler(src, **typst_font_kw())
            res = comp.compile_with_warnings()
            doc = res[0] if isinstance(res, tuple) else res      # (pdf bytes, warnings)
            if not isinstance(doc, bytes | bytearray) or not doc.startswith(b"%PDF"):
                return None, "", "compiling a one-line document returned no PDF", False
        try:
            ver = str(json.loads(mod.Compiler().eval("str(sys.version)", format="json")))
        except Exception:
            ver = str(getattr(mod, "__version__", "?"))
        full = False
        try:
            full = (hasattr(comp, "query") and hasattr(comp, "eval")
                    and bool(mod.Fonts(include_system_fonts=True, **typst_font_kw()).families()))
        except Exception:
            pass
        return mod, ver, "", full
    except Exception as e:
        return None, "", f"{type(e).__name__}: {e}", False


def typst_py() -> ModuleType | None:
    """The `typst` Python module if it works and can run query/eval/fonts too (a working
    install, proven by `_typst_py_probe`), else None. A broken, old or compile-only module
    does not qualify."""
    mod, _, _, full = _typst_py_probe()
    return mod if full else None


def typst_can_query() -> bool:
    """True when `typst query`/`eval`/`fonts` can run: the CLI, or typst-py."""
    return bool(shutil.which("typst")) or typst_py() is not None


def typst_fonts() -> list[str] | None:
    """Family names `typst fonts` reports (CLI, else typst-py), or None."""
    if shutil.which("typst"):
        try:
            r = subprocess.run(["typst", "fonts"], capture_output=True, text=True, timeout=20)
        except (OSError, subprocess.SubprocessError):
            return None
        return [l.strip() for l in r.stdout.splitlines() if l.strip()] if r.returncode == 0 else None
    mod = typst_py()
    try:
        return list(mod.Fonts(include_system_fonts=True, **typst_font_kw()).families()) if mod else None
    except Exception:
        return None

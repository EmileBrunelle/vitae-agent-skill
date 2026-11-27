"""Dependency preflight ("doctor") and the typst-py / typst CLI probes (a leaf under verify_base: no `import verify`).

Tests that patch `subprocess.run` / `shutil.which` for it target this module's own `shutil` / `subprocess`.
"""
from __future__ import annotations

import contextlib
import functools
import importlib
import importlib.metadata
import inspect
import io
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import sysconfig
import tempfile
import tomllib
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Literal, TextIO, TypeAlias

from vitae.core import proc
from vitae.core.narrow import is_object_list, is_object_tuple

# ---------- dependency preflight ("doctor") ----------

# The PEP 723 reference regex (packaging.python.org, "Inline script metadata"): the `# /// script` block of an entry script.
_PEP723 = re.compile(r"(?m)^# /// (?P<type>[a-zA-Z0-9-]+)$\s(?P<content>(^#(| .*)$\s)+)^# ///$")
_SCRIPTS_DIR = Path(__file__).resolve().parents[2]


def pep723_requirements(text: str) -> tuple[str, ...]:
    """The `dependencies` of the `# /// script` block in `text` (the requirement strings, markers included), () when
    there is no block."""
    for m in _PEP723.finditer(text):
        if m.group("type") == "script":
            lines = m.group("content").splitlines(keepends=True)
            try:
                meta = tomllib.loads("".join(ln[2:] if ln.startswith("# ") else ln[1:] for ln in lines))
            except tomllib.TOMLDecodeError:
                return ()
            deps = meta.get("dependencies", [])
            return tuple(str(d) for d in deps) if is_object_list(deps) else ()
    return ()


@functools.cache
def script_requirements(script: str) -> tuple[str, ...]:
    """The dependencies declared in the PEP 723 header of `scripts/<script>`, () when it is unreadable or has none."""
    try:
        return pep723_requirements((_SCRIPTS_DIR / script).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError):
        return ()


def _running_script() -> str:
    """Name of the entry script being run when it declares dependencies (else verify.py, whose header every gate shares)."""
    name = Path(sys.argv[0]).name if sys.argv and sys.argv[0] else ""
    return name if script_requirements(name) else "verify.py"


def requirement(name: str) -> str:
    """The requirement string for dependency `name` as the running script's header declares it (e.g. `typst==X`,
    `pikepdf>=Y; sys_platform != ...`); the bare name when the header has none."""
    for req in script_requirements(_running_script()):
        if re.split(r"[=<>!~;\s\[]", req, maxsplit=1)[0].lower() == name.lower():
            return req
    return name


def _pip(name: str, flags: str = "") -> str:
    """`pip install [flags] '<requirement>'` for dependency `name`, the requirement read from the script header."""
    return f"pip install {flags}{_quote_requirement(requirement(name))}"


def _quote_requirement(req: str) -> str:
    """`req` as one shell word: double-quoted around single-quoted markers when that is safe, else shlex-quoted."""
    if any(c in req for c in '"$`\\'):
        return shlex.quote(req)
    return f'"{req}"'


def _uv_line() -> str:
    """The first install advice: run the script through uv, which installs the header's dependencies itself."""
    script = shlex.quote(str(_SCRIPTS_DIR / _running_script()))
    return (f"  uv run {script} --help   # the dependencies in its PEP 723 header install themselves "
            "(`pipx run` works too); else:")

def check_pillow() -> bool:
    """Doctor line for Pillow, which the fill, text-clip, hidden-text and crop measurements read rasters through:
    without it the doctor fails."""
    try:
        import PIL
        print(f"OK    Pillow {PIL.__version__}")
        return True
    except ImportError:
        print("MISSING  Pillow -- needed for the page-fill measurement:")
        print(_uv_line())
        print(f"  {_pip('Pillow')}   # no root: add --user, or use a venv")
        return False


# Oldest typst the fill targets were calibrated on; an older one still works and is reported DEGRADED, not refused.
TYPST_MIN = (0, 15)   # tests/unit/test_env_requirements.py: equals the major.minor of the `typst==X` pin in the script headers
# Oldest typst that can write the PDFs vitae asks for: `--pdf-standard ua-1` (typst-py `pdf_standards`) and `pdf.artifact`
# both arrived in Typst 0.14.0 (Typst changelog 0.14.0, "PDF export"). Older is BROKEN: every compile would be refused.
TYPST_STANDARDS_MIN = (0, 14)
# The PDF standards every compile asks Typst to enforce: PDF/UA-1 (accessible tagged PDF) and PDF/A-2a, the archival
# level that is itself tagged and accepts the UA-1 PDF version range (A-1 caps the PDF version at 1.4, A-4 needs 2.0).
# Typst refuses to write the file when the document breaks one (no title, an image with no description, ...). Next to
# TYPST_STANDARDS_MIN: the floor is the first Typst that writes exactly these.
PDF_STANDARDS = ("a-2a", "ua-1")
_NO_STANDARDS = "PDF/UA-1 + PDF/A-2a output (`--pdf-standard`, `pdf.artifact`) needs Typst 0.14 or newer"
def _new_typst() -> str:
    return ("fill targets are calibrated on typst 0.15; newer versions may measure differently "
            f"-- pin with {_pip('typst')} if fills drift")

_OLD_TYPST = ("fill targets are calibrated on typst 0.15; older versions measure lower "
              "(0.13/0.14 miss 2 templates at 91% against 93-96%)")


def _wheel_platform_tag() -> str:
    """The running interpreter's most specific wheel platform tag (e.g. manylinux_2_28_x86_64,
    macosx_14_0_arm64, win_amd64): from packaging/pip's tag list when importable, else sysconfig."""
    for mod in ("packaging.tags", "pip._vendor.packaging.tags"):
        try:
            tags = importlib.import_module(mod)
            return str(next(iter(tags.sys_tags())).platform)
        except (ImportError, StopIteration):   # module absent, or an empty tag list
            continue
    return re.sub(r"[-.]", "_", sysconfig.get_platform())


def _before_pdf_standards(ver: str, via: str) -> bool:
    """Print the BROKEN lines and return True when `ver` (unreadable "?" counts as fine) is older than TYPST_STANDARDS_MIN."""
    if ver == "?" or _ver_tuple(ver) >= TYPST_STANDARDS_MIN:
        return False
    print(f"BROKEN  typst {ver} ({via}): {_NO_STANDARDS}.")
    print(_uv_line())
    print(f"  {_pip('typst', '--upgrade ')}")
    return True


CLI_TIMED_OUT = "timed-out"   # `_cli_probe` value for a `typst --version` that hung: not a version, not "?"


@functools.cache
def _cli_probe() -> str | None:
    """Version token of the `typst` CLI on PATH, "?" when it cannot run or prints none, CLI_TIMED_OUT when it hung, None when there is no CLI.
    `which` and `typst --version` run once per process, the doctor included."""
    if not shutil.which("typst"):
        return None
    return _cli_version()


def _cli_version() -> str:
    """Version token of `typst --version`; "?" when the CLI cannot run or prints none."""
    try:
        return proc.run(["typst", "--version"], proc.PROBE_S, name="typst --version").stdout.split()[1]
    except proc.ToolTimeout:
        return CLI_TIMED_OUT
    except (OSError, subprocess.SubprocessError, IndexError):   # cannot run, or no version token in the output
        return "?"


def _check_typst_cli(ver: str) -> bool:
    """Doctor lines for the typst CLI on PATH, whose version `ver` is new enough to write PDF/UA-1."""
    if ver != "?" and _ver_tuple(ver) < TYPST_MIN:
        print(f"DEGRADED  typst {ver} (CLI): {_OLD_TYPST}.")
        print(_uv_line())
        print(f"  {_pip('typst', '--upgrade ')}   # no root: add --user, or use a venv; pip picks the CPU architecture")
        return True
    print(f"OK    typst {ver} (CLI)")
    if ver != "?" and _ver_tuple(ver) > TYPST_MIN:
        print(f"  NOTE: {_new_typst()}.")
    return True


def _use_api_for_old_cli(cli_ver: str, mod: ModuleType | None, api_ver: str) -> bool:
    """The typst CLI on PATH is older than PDF/UA-1 support: print why, and return True when a working Python API
    new enough to write it takes over (the BROKEN lines otherwise)."""
    if mod is None or _ver_tuple(api_ver) < TYPST_STANDARDS_MIN:
        _before_pdf_standards(cli_ver, "CLI")
        return False
    print(f"DEGRADED  typst {cli_ver} (CLI): too old for PDF/UA-1 + PDF/A-2a, so the Python API (typst {api_ver}) is used instead.")
    return True


def check_typst() -> bool:
    """Doctor lines for typst; returns whether it is available. The CLI is preferred, the Python API is the fallback and
    is judged by running it, not by its attributes. Older than TYPST_MIN, or a Python API without query/fonts, is
    DEGRADED (still available); a broken or missing install is not."""
    if _cli_probe() == CLI_TIMED_OUT:
        # a hung CLI is a failed doctor whatever else is installed; the route falls back to typst-py without it
        print(f"FAIL  typst --version timed out after {proc.PROBE_S:g} s: the `typst` CLI on PATH hangs (it is not used)")
        _check_typst_without_cli()
        return False
    return _check_typst_without_cli()


def _check_typst_without_cli() -> bool:
    """`check_typst` past the CLI probe: judged on a usable CLI when one answers, else on the Python API."""
    cli_old = ""
    probed = _cli_probe()
    cli_ver = None if probed == CLI_TIMED_OUT else probed
    if cli_ver is not None:
        if cli_ver == "?" or _ver_tuple(cli_ver) >= TYPST_STANDARDS_MIN:
            return _check_typst_cli(cli_ver)
        cli_old = cli_ver
    probe = _typst_py_probe()
    mod, ver, why, full = probe.module, probe.version, probe.problem, probe.full
    if cli_old and not _use_api_for_old_cli(cli_old, mod, ver):
        return False
    if mod is None and probe.too_old:
        print(f"BROKEN  typst: the Python package `typst` is too old ({why}).")
        print(_uv_line())
        print(f"  Upgrade it: {_pip('typst', '--upgrade ')}")
        return False
    if mod is None and why:
        print(f"BROKEN  typst: the Python package `typst` is installed but does not work ({why}).")
        print(_uv_line())
        print(f"  Reinstall it: {_pip('typst', '--force-reinstall ')}")
        return False
    if mod is not None and _before_pdf_standards(ver, "Python API"):
        return False
    if mod is not None and not full:
        print("DEGRADED  typst: Python API only, no typst CLI. Compiling and fill measurement work, but these checks are SKIPPED (WARN):")
        print("  - date adjacency (needs `typst query`, and pdftotext)")
        print("  - group proximity (needs `typst query` and pdftotext)")
        print("  - the design font-availability check of pick_design.py (needs `typst fonts`)")
        print(_uv_line())
        print(f"  Upgrade the Python package: {_pip('typst', '--upgrade ')}")
        return True
    if mod is not None:
        if _ver_tuple(ver) < TYPST_MIN:
            print(f"DEGRADED  typst {ver} (Python API): {_OLD_TYPST}.")
            print(_uv_line())
            print(f"  {_pip('typst', '--upgrade ')}")
            return True
        print(f"OK    typst {ver} (Python API: compile, query, fonts)")
        if _ver_tuple(ver) > TYPST_MIN:
            print(f"  NOTE: {_new_typst()}.")
        return True
    print("MISSING  typst -- install it:")
    print(_uv_line())
    print(f"  {_pip('typst')}                    # no root (--user or a venv); no CLI needed: compiles, queries and lists fonts via the Python API")
    print("  (a `typst` CLI already on PATH is used when present; there is nothing else to install for it)")
    print("  OFFLINE sandbox (no DNS / pip index)? On the user's own machine run:")
    plat, pyver = _wheel_platform_tag(), f"{sys.version_info.major}.{sys.version_info.minor}"
    print(f"    pip download {shlex.quote(requirement('typst'))} --no-deps --only-binary=:all: --platform {plat} --python-version {pyver}")
    print("    (if that platform has no wheel, `python3 -m pip debug --verbose` lists every compatible tag; never install a wheel built for another platform)")
    print("    (or pick the matching wheel from https://pypi.org/project/typst/#files), upload the .whl, then:")
    print("    pip install --no-index <path-to-wheel>")
    return False


PdfBackend: TypeAlias = Literal["poppler", "pdfium", "pypdf"] | None


@functools.cache
def importable(name: str) -> bool:
    """True when `name` really imports (find_spec says only that a file exists: a broken
    wheel or a missing shared library passes it and then fails on first use)."""
    try:
        importlib.import_module(name)
        return True
    except Exception:   # noqa: BLE001 - kept broad: a broken wheel may raise anything on import (OSError, RuntimeError...); False reads as backend absent, the callers WARN
        return False




def pdf_backend() -> PdfBackend:
    """The PDF reader every check uses: poppler when pdfinfo and pdftotext are on PATH
    (the reference), else pypdfium2 (text, word boxes, raster, metadata and attachments in
    Python: close to poppler, not identical, see the CHANGELOG for where it differs), else
    pypdf (page count and indicative text only: it splits words), else None. A module that
    does not import is not selected, the doctor tests it the same way."""
    if shutil.which("pdfinfo") and shutil.which("pdftotext"):
        return "poppler"
    fallbacks: tuple[tuple[str, Literal["pdfium", "pypdf"]], ...] = (("pypdfium2", "pdfium"), ("pypdf", "pypdf"))
    for name, backend in fallbacks:
        if importable(name):
            return backend
    return None


@dataclass(frozen=True)
class PdfCheck:
    """Outcome of the PDF-reader doctor check: `ok` is False only when nothing can read a PDF; `backend` is the one
    pdf_backend() would pick (None when there is none)."""
    ok: bool
    backend: PdfBackend


def check_pdf_tools() -> PdfCheck:
    """Doctor lines for the PDF reader; returns whether one is available and which backend, the one pdf_backend() would
    pick. A missing pdftoppm, or pypdf standing in for poppler, only degrades: the checks it cannot serve are named
    in the output."""
    if shutil.which("pdfinfo") and shutil.which("pdftotext"):
        if not shutil.which("pdftoppm"):
            print("DEGRADED  poppler-utils: pdftotext and pdfinfo found, pdftoppm missing. SKIPPED (WARN):")
            print("  - hidden-text ink check (also used by verify_letter.py / verify_academic.py)")
            print("  Weaker without a WARN: group proximity falls back to the pdftotext box gap instead of the ink gap")
            print("  poppler (academic mode only): install `poppler-utils` (or `poppler`) with the system package manager")
            return PdfCheck(True, "poppler")
        print("OK    poppler-utils (pdftotext, pdfinfo, pdftoppm)")
        return PdfCheck(True, "poppler")
    if importable("pypdfium2"):
        try:
            ver = importlib.metadata.version("pypdfium2")
        except importlib.metadata.PackageNotFoundError:
            ver = "?"
        print(f"OK    pdf: pypdfium2 {ver} (Python: text, word boxes, raster, metadata, attachments)")
        print("  - academic mode still needs poppler (verify_academic.py reads `pdftotext -layout`)")
        return PdfCheck(True, "pdfium")
    if importable("pypdf"):
        print("DEGRADED  pypdf: Python fallback, no poppler. Page count is exact, but:")
        print("  - ATS text extraction is indicative only (spurious spaces, e.g. \"FORMA TION\")")
        print("  - SKIPPED (WARN): hidden-text gate and text-clip gate (need pdftotext and pdftoppm)")
        print("  - SKIPPED (WARN): group proximity and date adjacency (need pdftotext)")
        print("  - academic mode cannot run (verify_academic.py requires pdftotext)")
        print(f"  - `{_pip('pypdfium2')}`: text, word boxes, raster and metadata then run in Python close to poppler's (see the CHANGELOG)")
        print("  poppler (academic mode only): install `poppler-utils` (or `poppler`) with the system package manager")
        return PdfCheck(True, "pypdf")
    print("MISSING  poppler-utils -- needed for page-count and ATS extraction checks:")
    print("  poppler-utils: install it with your system package manager (academic mode requires it)")
    print(_uv_line())
    print(f"  {_pip('pypdfium2')}                                  # fallback: text, boxes, raster and metadata in Python, close to poppler's (used automatically if present)")
    print(f"  {_pip('pypdf')}                                      # last resort: exact page count, indicative extraction only (used automatically if present)")
    return PdfCheck(False, None)


def check_pikepdf() -> None:
    """Doctor line for the optional PDF post-step (verify/hexstrings.py); never a failure or a DEGRADED."""
    from vitae.verify.hexstrings import MIN_VERSION, version_tuple
    need = ".".join(map(str, MIN_VERSION))
    if not importable("pikepdf"):
        print(f"INFO  pikepdf not installed (optional, >= {need}): compiled PDFs keep Typst's literal strings, which PHP's "
              f"smalot/pdfparser can truncate. `uv run` installs it; or `{_pip('pikepdf')}`")
        return
    try:
        ver = importlib.metadata.version("pikepdf")
    except importlib.metadata.PackageNotFoundError:
        ver = "?"
    if version_tuple(ver) < MIN_VERSION:
        print(f"INFO  pikepdf {ver} too old (need >= {need}), optional step skipped")
    else:
        print(f"OK    pikepdf {ver} (optional: PDF text strings re-serialised with escaped parentheses so PHP's smalot/pdfparser reads them whole)")


def check_fonts() -> None:
    """Doctor line for fonts (typst CLI or typst-py; local, no network, 20 s cap).

    Reuses pick_design's own logic: a design family is usable when every role of
    its pool has at least one installed member (`installed_face`). pick_design
    draws from at least MIN_POOL families, so fewer usable ones means it will
    substitute."""
    import vitae.design.fonts as design_fonts
    from vitae.design.tables import FONTS, MIN_POOL
    have = design_fonts.fonts_available()
    if have is None:
        print("WARN  fonts not checked (`typst fonts` failed or timed out)")
        return
    pools = FONTS
    usable = sum(1 for f in pools if design_fonts.family_usable(f, have))
    if usable < MIN_POOL:
        print(f"DEGRADED  fonts: only {usable} of {len(pools)} design families have their fonts installed "
              f"(pick_design draws from at least {MIN_POOL}), so it will substitute.")
        print("  Fetch only the fonts the draw asks for (references/fonts.md, \"Downloading from Google Fonts\"):")
        r2 = ("typst --font-path <dir> (no install)" if typst_route().compile == "cli"
              else "export TYPST_FONT_PATHS=<dir> (no install; the Python API reads it here)")
        print(f"  Route 1: install into ~/.local/share/fonts/vitae (persistent, recommended); Route 2: {r2}")
    else:
        print(f"OK    fonts ({usable} of {len(pools)} design families have an installed face for every role; a drawn face may still be substituted, {len(have)} families)")


class _CountDegraded(io.StringIO):
    """stdout wrapper: counts the doctor lines that start with DEGRADED, so no path can print one and still end on an
    OK summary, whichever check wrote it. A StringIO only so that it is a TextIO redirect_stdout accepts: it keeps
    nothing, every write goes to `inner`."""
    def __init__(self, inner: TextIO) -> None:
        super().__init__()
        self.inner, self.n, self._bol = inner, 0, True

    def write(self, text: str) -> int:
        for part in text.splitlines(keepends=True):
            if self._bol and part.startswith("DEGRADED"):
                self.n += 1
            self._bol = part.endswith("\n")
        return int(self.inner.write(text))

    def flush(self) -> None:
        self.inner.flush()

    def isatty(self) -> bool:
        return self.inner.isatty()

    def fileno(self) -> int:
        return self.inner.fileno()

    def __getattr__(self, name: str) -> object:
        return getattr(self.inner, name)


def preflight() -> PdfCheck:
    """Print the doctor output; returns all_ok and the pdf backend. all_ok is False only when something
    has no fallback (Pillow, typst, a PDF reader); DEGRADED lines leave it True."""
    counter = _CountDegraded(sys.stdout)
    with contextlib.redirect_stdout(counter):
        pillow_ok = check_pillow()
        typst_ok = check_typst()
        route = typst_route()
        if route.query is not None:
            check_fonts()
        pdf = check_pdf_tools()
        backend = pdf.backend
        all_ok = pillow_ok and typst_ok and pdf.ok
        pypdf_missing = backend in ("poppler", "pdfium") and not importable("pypdf")
        if pypdf_missing:
            # the WARN check_hidden_text prints for this backend, quoted so the doctor and the gate agree
            skipped = ("the tiny-text check of the hidden-text gate will NOT run "
                       "(WARN \"tiny-text check not run (pypdf missing)\")" if backend == "pdfium" else
                       "the off-page check of the hidden-text gate will NOT run "
                       "(WARN \"hidden text: off-page check not run (pypdf missing)\")")
            print(f"DEGRADED  pypdf: not installed. {skipped}. Fix: {_pip('pypdf')}")
        check_pikepdf()
        if (all_ok and not counter.n and route.compile != "cli" and backend == "pdfium" and typst_py() is not None
                and _ver_tuple(_typst_py_probe().version) >= TYPST_MIN):
            print("OK (Python)  no typst CLI, no poppler: compile, query, fonts, text, boxes and raster all run in Python "
                  "(typst-py + pypdfium2 + pypdf + Pillow); academic mode still needs poppler")
    return PdfCheck(all_ok, backend)


def typst_font_kw() -> dict[str, list[str]]:
    """typst-py keyword for the font route of references/fonts.md: TYPST_FONT_PATHS (what the
    CLI reads on its own) as `font_paths`; typst-py ignores the variable, so pass it by hand."""
    fp = [p for p in os.environ.get("TYPST_FONT_PATHS", "").split(os.pathsep) if p]
    return {"font_paths": fp} if fp else {}


def _ver_tuple(v: str) -> tuple[int, int]:
    """(major, minor) of the first `X.Y` in `v`; (0, 0) when there is none, which reads as older than TYPST_MIN."""
    m = re.search(r"(\d+)\.(\d+)", v)
    return (int(m.group(1)), int(m.group(2))) if m else (0, 0)


@dataclass(frozen=True)
class TypstPyProbe:
    """Result of running the `typst` Python package: `module` (None when absent or unusable), `version`, `problem`
    (text; "" when none) and `full` (also query, eval and Fonts)."""
    module: ModuleType | None
    version: str
    problem: str
    full: bool
    too_old: bool = False   # a working but old wheel: `problem` then says which, and the doctor says "too old", not "broken"


@functools.cache
def _typst_py_probe() -> TypstPyProbe:
    """The TypstPyProbe (module, version, problem, full) for the `typst` Python package, by running it: a tiny
    document is compiled and an expression evaluated, so a broken wheel is reported broken
    (an attribute check passes it). module None + problem "" = not installed; module None +
    problem = installed but unusable; full = also query, eval and Fonts."""
    try:
        mod = importlib.import_module("typst")   # ModuleType: attribute access is untyped (no stubs)
    except ImportError:
        return TypstPyProbe(None, "", "", False)
    except Exception as e:   # noqa: BLE001 - kept broad: a broken wheel may raise anything on import; reported as the probe's problem text, which the doctor prints
        return TypstPyProbe(None, "", f"import failed: {type(e).__name__}: {e}", False)
    comp_cls = getattr(mod, "Compiler", None)
    if comp_cls is not None and not hasattr(comp_cls, "compile_with_warnings"):
        # a working but old wheel (typst-py 0.11.x): the API this script drives is newer
        return TypstPyProbe(None, "", f"typst {getattr(mod, '__version__', '?')}: its Compiler has no compile_with_warnings", False, too_old=True)
    try:
        with tempfile.TemporaryDirectory() as td:
            src = os.path.join(td, "probe.typ")
            with open(src, "w", encoding="utf-8") as fh:
                fh.write("#set page(width: 50pt, height: 50pt)\nprobe\n")
            comp = mod.Compiler(src, **typst_font_kw())
            res: object = comp.compile_with_warnings()
            doc = res[0] if is_object_tuple(res) else res      # (pdf bytes, warnings)
            if not isinstance(doc, bytes | bytearray) or not doc.startswith(b"%PDF"):
                return TypstPyProbe(None, "", "compiling a one-line document returned no PDF", False)
        ver = str(getattr(mod, "__version__", "?"))
        if hasattr(comp_cls, "eval"):   # typst-py 0.13.4-0.14.x has no Compiler.eval: DEGRADED, still compiles
            try:
                ver = str(json.loads(mod.Compiler().eval("str(sys.version)", format="json")))
            except (RuntimeError, ValueError, TypeError):   # eval error, a reply that is not JSON, or a signature mismatch
                pass
        full = False
        try:
            full = (hasattr(comp, "query") and hasattr(comp, "eval")
                    and bool(mod.Fonts(include_system_fonts=True, **typst_font_kw()).families()))
        except (RuntimeError, OSError):   # Fonts() failing: the module is compile-only, full stays False
            pass
        return TypstPyProbe(mod, ver, "", full)
    except Exception as e:   # noqa: BLE001 - kept broad: the probe runs a third-party wheel; any failure is reported as the problem text (type and message)
        return TypstPyProbe(None, "", f"{type(e).__name__}: {e}", False)


def typst_py() -> ModuleType | None:
    """The `typst` Python module if it works and can run query/eval/fonts too (a working
    install, proven by `_typst_py_probe`), else None. A broken, old or compile-only module
    does not qualify."""
    probe = _typst_py_probe()
    return probe.module if probe.full else None


def _accepts(fn: Callable[..., object], keyword: str) -> bool:
    """Whether `fn` takes the keyword `keyword`; True when its signature cannot be read (a modern wheel is assumed)."""
    try:
        params = inspect.signature(fn).parameters
    except (TypeError, ValueError):   # no readable signature (builtin without __text_signature__)
        return True
    return keyword in params or any(p.kind is inspect.Parameter.VAR_KEYWORD for p in params.values())


@dataclass(frozen=True)
class TypstPyCaps:
    """What the installed typst-py takes, recorded once from its signatures (wheels differ): `compile` and
    `Compiler.compile_with_warnings` take `ppi`; `Compiler.query` takes `field`; `Compiler.eval` takes `format`."""
    ppi: bool = True
    query_field: bool = True
    eval_format: bool = True


def _typst_py_caps(mod: ModuleType | None) -> TypstPyCaps:
    """The capabilities of the typst-py module `mod` (all True when there is none to ask)."""
    comp = getattr(mod, "Compiler", None)
    if comp is None:
        return TypstPyCaps()
    return TypstPyCaps(ppi=_accepts(comp.compile_with_warnings, "ppi"),
                       query_field=_accepts(comp.query, "field") if hasattr(comp, "query") else True,
                       eval_format=_accepts(comp.eval, "format") if hasattr(comp, "eval") else True)


Route: TypeAlias = Literal["cli", "api"] | None


@dataclass(frozen=True)
class TypstRoute:
    """How Typst is reached, decided once per process. `compile` writes PDFs and PNGs: the CLI when it can write
    PDF/UA-1 + PDF/A-2a (0.14 or newer; a version it will not print counts as fine), else the Python API, else None.
    `query` serves query / eval / fonts (they write no PDF): a usable CLI, else a full Python API (not a compile-only
    one), else any CLI on PATH, even an old one. `api` is the working typst-py module (compile at least) and `caps` its
    signature capabilities."""
    compile: Route
    query: Route
    api: ModuleType | None
    caps: TypstPyCaps


@functools.cache
def typst_route() -> TypstRoute:
    """The one decision for every typst call (compile, PNG render, query, eval, fonts), as `check_typst` reports it.
    Probed once per process: `which`, `typst --version` and the typst-py probe each run once."""
    cli_ver = _cli_probe()
    cli_usable = cli_ver is not None and cli_ver != CLI_TIMED_OUT and (cli_ver == "?" or _ver_tuple(cli_ver) >= TYPST_STANDARDS_MIN)
    probe = _typst_py_probe()
    mod, full = probe.module, probe.full
    compile_route: Route = "cli" if cli_usable else "api" if mod is not None else None
    query_route: Route = "cli" if cli_usable else "api" if full else "cli" if cli_ver not in (None, CLI_TIMED_OUT) else None
    return TypstRoute(compile_route, query_route, mod, _typst_py_caps(mod))


def typst_can_query() -> bool:
    """True when `typst query`/`eval`/`fonts` can run: the CLI, or typst-py."""
    return typst_route().query is not None


def typst_fonts() -> list[str] | None:
    """Family names `typst fonts` reports (CLI, else typst-py), or None."""
    if typst_route().query == "cli":
        try:
            r = proc.run(["typst", "fonts"], proc.PROBE_S, name="typst fonts")
        except (OSError, subprocess.SubprocessError):
            return None
        return [l.strip() for l in r.stdout.splitlines() if l.strip()] if r.returncode == 0 else None
    mod = typst_py()
    try:
        return list(mod.Fonts(include_system_fonts=True, **typst_font_kw()).families()) if mod else None
    except (RuntimeError, OSError):   # typst-py Fonts() failing
        return None

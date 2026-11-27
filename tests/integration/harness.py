"""Helpers shared by the integration checks: run a subprocess check into a log, apply the PASS rule.

The rule: a check PASSES only if it exits 0 AND prints no line starting with "FAIL" (verify.py's verdict
is its last line; a wrapper that swallows the exit code must not turn a FAIL into a PASS).
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"


def pdf_tool(name: str) -> bool:
    """True when `name` (pdftotext, pdftoppm, pdfdetach) can be served: on PATH, or by pypdfium2."""
    from vitae.core.env import pdf_backend

    return bool(shutil.which(name)) or pdf_backend() == "pdfium"


@dataclass(frozen=True)
class CheckResult:
    name: str
    rc: int
    output: str
    log: Path | None
    stdout: str = ""   # stdout alone, for the checks that parse it (stderr is in `output`)

    @property
    def passed(self) -> bool:
        return self.rc == 0 and not any(line.startswith("FAIL") for line in self.output.splitlines())

    def tail(self, n: int = 15) -> str:
        return "\n".join(self.output.splitlines()[-n:])

    def failures(self) -> str:
        """The FAIL lines (and the NEXT line after them): the cause, which the tail of a long verify output hides."""
        return "\n".join(ln for ln in self.output.splitlines() if ln.startswith(("FAIL", "NEXT")))


def run_check(name: str, argv: Sequence[str | int | os.PathLike[str]], cwd: Path,
              env: Mapping[str, str] | None = None, log_dir: Path | None = None,
              timeout: float = 600) -> CheckResult:
    """Run `argv` in `cwd` (stdout+stderr merged, written to `log_dir/<name>.log`). `env` is added to os.environ
    (the doctor simulations pass a PATH with shims here). A timeout is a failed check, not a hang."""
    full_env = dict(os.environ)
    if env:
        full_env.update(env)
    try:
        p = subprocess.run([str(a) for a in argv], cwd=cwd, env=full_env, capture_output=True, text=True,
                           errors="replace", timeout=timeout, stdin=subprocess.DEVNULL, check=False)
        rc, out, so = p.returncode, p.stdout + p.stderr, p.stdout
    except subprocess.TimeoutExpired:
        rc, out, so = 124, f"FAIL timeout after {timeout}s", ""
    except OSError as e:
        rc, out, so = 127, f"FAIL cannot run {argv[0]}: {e}", ""
    log: Path | None = None
    if log_dir is not None:
        log_dir.mkdir(parents=True, exist_ok=True)
        log = log_dir / (re.sub(r"[/\\]", "_", name) + ".log")
        log.write_text(out, encoding="utf-8")
    return CheckResult(name, rc, out, log, so)


def assert_passed(r: CheckResult) -> None:
    assert r.passed, f"FAIL {r.name} (exit {r.rc}; see {r.log})\n{r.failures()}\n--- tail ---\n{r.tail()}"


# The first 3 templates only under --quick.
QUICK_TEMPLATES = 3
# The 2-page variants and their fill targets (tables.py declares none): a resume-2page.typ in a family not listed here fails
# test_every_family_has_its_templates instead of silently getting someone else's target.
TWO_PAGE_FILL = {"swiss-grid": (94, 96)}


@dataclass(frozen=True)
class Template:
    family: str
    name: str
    pages: int
    fill_min: int
    fill_max: int

    @property
    def check_name(self) -> str:
        return f"template/{self.family}/{self.name}"


def discover_templates() -> list[Template]:
    """One entry per `templates/families/<f>/{resume,resume-pair-b}.typ` (fill from tables.FAMILIES[f]['page']['fill']),
    then every `resume-2page.typ` found. Discovered, not listed: a new family joins the suite by existing."""
    from vitae.design.tables import FAMILIES
    out: list[Template] = []
    for fam in sorted(FAMILIES):
        lo, hi = (int(x) for x in FAMILIES[fam]["page"]["fill"].split("-"))
        out.extend(Template(fam, name, 1, lo, hi) for name in ("resume", "resume-pair-b"))
    for fam, (lo, hi) in sorted(TWO_PAGE_FILL.items()):
        out.append(Template(fam, "resume-2page", 2, lo, hi))
    return out


def grep(text: str, pattern: str) -> bool:
    """`grep -q PATTERN` on a captured output: a regex matched line by line (so ^ and $ anchor a line, as in grep -E)."""
    return re.search(pattern, text, re.MULTILINE) is not None


# Doctor simulations: a PATH of symlinks and shims, plus a stub `typst` Python module on PYTHONPATH.

def doctor_env(d: Path, tools: Sequence[str] = ()) -> Path:
    """Fresh `d/bin` (symlinks to the host `tools`) and `d/py` (for a stub typst.py); returns d."""
    shutil.rmtree(d, ignore_errors=True)
    (d / "bin").mkdir(parents=True)
    (d / "py").mkdir()
    for t in tools:
        host = shutil.which(t)
        assert host, f"host tool {t} not found"
        (d / "bin" / t).symlink_to(host)
    return d


def shim_typst(d: Path, families: Sequence[str], version: str = "0.15.0") -> None:
    """Fake `typst` CLI of the given version that lists only `families` as its fonts."""
    echoes = "".join(f'echo "{f}"; ' for f in families)
    shim = d / "bin" / "typst"
    shim.write_text(f'#!/bin/sh\n[ "$1" = fonts ] && {{ {echoes}exit 0; }}\necho "typst {version}"\n')
    shim.chmod(0o755)


_STUB_COMPILE = ('class Compiler:\n    def __init__(self, *a, **k): pass\n'
                 '    def compile_with_warnings(self, **k): return (b"%PDF-1", [])\n')
STUB_TYPST = {
    "broken": "",    # imports, has no Compiler: a broken install
    "compile-only": _STUB_COMPILE + '__version__ = "9.9.9"\n',
    "working": _STUB_COMPILE + '    def query(self, *a, **k): return "[]"\n    def eval(self, e, **k): return "\\"9.9.9\\""\n'
                               'class Fonts:\n    def __init__(self, *a, **k): pass\n    def families(self): return ["DejaVu Sans"]\n'
                               '__version__ = "9.9.9"\n',
}


def stub_typst(d: Path, kind: str, version: str | None = None) -> None:
    """Write d/py/typst.py: `broken`, `compile-only` or `working` (by how much of the API works)."""
    src = STUB_TYPST[kind]
    d.joinpath("py", "typst.py").write_text(src.replace("9.9.9", version) if version else src)


def run_doctor(name: str, d: Path, cwd: Path, log_dir: Path, *, stub: bool = False) -> CheckResult:
    """`verify.py --doctor` with PATH = d/bin only (and PYTHONPATH = d/py when a stub is in play), by the interpreter's own
    path: a `python3` symlink in the stripped PATH would resolve out of a venv and lose its site-packages."""
    env = {"PATH": str(d / "bin")}
    if stub:
        env["PYTHONPATH"] = str(d / "py")
    return run_check(name, [sys.executable, "scripts/verify.py", "--doctor"], cwd, env, log_dir)


def importable_isolated(module: str) -> bool:
    """Whether `python -I` can import `module`. The gates run isolated (no user site, no PYTHONPATH), so a skip guard
    must decide the same way: find_spec in the pytest process also sees a `pip install --user` copy the gate cannot."""
    return subprocess.run([sys.executable, "-I", "-c", f"import {module}"], capture_output=True, check=False).returncode == 0

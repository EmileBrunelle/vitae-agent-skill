"""Helpers shared by the integration checks: run a subprocess check into a log, apply the PASS rule, run a batch in parallel.

The rule is run_all.sh's: a check PASSES only if it exits 0 AND prints no line starting with "FAIL" (verify.py's verdict
is its last line; a wrapper that swallows the exit code must not turn a FAIL into a PASS).
"""
from __future__ import annotations

import os
import re
import subprocess
from collections.abc import Callable, Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"


@dataclass(frozen=True)
class CheckResult:
    name: str
    rc: int
    output: str
    log: Path | None

    @property
    def passed(self) -> bool:
        return self.rc == 0 and not any(line.startswith("FAIL") for line in self.output.splitlines())

    def tail(self, n: int = 15) -> str:
        return "\n".join(self.output.splitlines()[-n:])


def run_check(name: str, argv: Sequence[str | os.PathLike[str]], cwd: Path,
              env: Mapping[str, str] | None = None, log_dir: Path | None = None,
              timeout: float = 600) -> CheckResult:
    """Run `argv` in `cwd` (stdout+stderr merged, written to `log_dir/<name>.log`). `env` is added to os.environ
    (the doctor simulations pass a PATH with shims here). A timeout is a failed check, not a hang."""
    full_env = dict(os.environ)
    if env:
        full_env.update(env)
    try:
        p = subprocess.run([str(a) for a in argv], cwd=cwd, env=full_env, capture_output=True, text=True,
                           errors="replace", timeout=timeout, stdin=subprocess.DEVNULL)
        rc, out = p.returncode, p.stdout + p.stderr
    except subprocess.TimeoutExpired:
        rc, out = 124, f"FAIL timeout after {timeout}s"
    except OSError as e:
        rc, out = 127, f"FAIL cannot run {argv[0]}: {e}"
    log: Path | None = None
    if log_dir is not None:
        log_dir.mkdir(parents=True, exist_ok=True)
        log = log_dir / (re.sub(r"[/\\]", "_", name) + ".log")
        log.write_text(out, encoding="utf-8")
    return CheckResult(name, rc, out, log)


def assert_passed(r: CheckResult) -> None:
    assert r.passed, f"FAIL {r.name} (exit {r.rc}; see {r.log})\n{r.tail()}"


def jobs() -> int:
    """Pool size: $VITAE_JOBS (as run_all.sh), else the CPU count; anything unusable means 1."""
    raw = os.environ.get("VITAE_JOBS")
    if raw is None:
        return os.cpu_count() or 2
    return int(raw) if raw.isdigit() and int(raw) > 0 else 1


def run_parallel(thunks: Mapping[str, Callable[[], CheckResult]]) -> dict[str, CheckResult]:
    """Run the checks concurrently (subprocess-bound, so threads are enough); results keyed like the input."""
    with ThreadPoolExecutor(max_workers=jobs()) as pool:
        futures = {k: pool.submit(t) for k, t in thunks.items()}
        return {k: f.result() for k, f in futures.items()}


# The first 3 templates only under --quick.
QUICK_TEMPLATES = 3
TWO_PAGE_FILL = (94, 96)   # swiss-grid/resume-2page.typ: 2 pages, 94-96 % (run_all.sh's hard-coded target)


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
        for name in ("resume", "resume-pair-b"):
            out.append(Template(fam, name, 1, lo, hi))
    for typ in sorted((ROOT / "templates" / "families").glob("*/resume-2page.typ")):
        out.append(Template(typ.parent.name, "resume-2page", 2, *TWO_PAGE_FILL))
    return out

"""Client-neutral trigger eval. Python 3.11+, stdlib only; runs on Windows, macOS, Linux.

Usage: python evals/run_triggers.py ADAPTER [RUNS=3]
  ADAPTER: module evals/adapters/<ADAPTER>.py exposing
      command(query, workdir) -> list[str]   argv of one non-interactive run (required)
      env() -> dict[str, str | None]         child env overrides, None unsets (optional)
      triggered(transcript) -> bool          custom detection (optional)
  A run that cannot start, times out, exits non-zero or prints nothing is an ERROR: reported
  apart from PASS/FAIL, excluded from the score, listed at the end, exit code 1 (2 = bad usage/config).
  env vars: WORK=scratch dir (finished runs are reused), JOBS=4, QUERY=regex on query ids.
  Client-specific settings (config dir, model, ...) are env vars documented in the adapter.
"""

import importlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import ModuleType
from typing import Any

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
TIMEOUT = 180
_SKILL_PATH = re.compile(r"skills[/\\]+vitae[/\\]+SKILL\.md")
_SKILL_EVENT = re.compile(r"\bskill\b[^\n]{0,60}\bvitae\b", re.IGNORECASE)


def default_triggered(transcript: str) -> bool:
    """SKILL.md path in the transcript, or a skill-activation event naming vitae."""
    return bool(_SKILL_PATH.search(transcript) or _SKILL_EVENT.search(transcript))


def _text(data: str | bytes | None) -> str:
    if isinstance(data, bytes):
        return data.decode("utf-8", errors="replace")
    return data or ""


def run_one(adapter: ModuleType, workdir: Path, query: str) -> str | None:
    """Run one query. Returns None on success, else a one-line error (the run is not a result)."""
    out = workdir / "out.txt"
    if out.exists() and out.stat().st_size:
        return None
    workdir.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    for key, value in (getattr(adapter, "env", dict)()).items():
        if value is None:
            env.pop(key, None)
        else:
            env[key] = value
    argv = list(adapter.command(query, workdir))
    # which() resolves PATHEXT on Windows, so npm .cmd shims run without shell=True
    exe = shutil.which(argv[0], path=env.get("PATH"))
    if exe is None:
        return f"client binary {argv[0]!r} not found on PATH"
    argv[0] = exe
    try:
        done = subprocess.run(  # noqa: S603
            argv, cwd=workdir, env=env, stdin=subprocess.DEVNULL,
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=TIMEOUT,
        )  # fmt: skip
    except subprocess.TimeoutExpired as exc:
        (workdir / "out.partial.txt").write_text(_text(exc.stdout), encoding="utf-8")
        (workdir / "err.txt").write_text(_text(exc.stderr) or str(exc), encoding="utf-8")
        return f"timeout after {TIMEOUT}s"
    except OSError as exc:
        (workdir / "err.txt").write_text(str(exc), encoding="utf-8")
        return f"cannot start client: {exc}"
    (workdir / "err.txt").write_text(done.stderr, encoding="utf-8")
    if done.returncode != 0 or not done.stdout.strip():
        (workdir / "out.partial.txt").write_text(done.stdout, encoding="utf-8")
        why = f"exit code {done.returncode}" if done.returncode else "empty output"
        return f"{why} (see err.txt)"
    out.write_text(done.stdout, encoding="utf-8")
    return None


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    name = argv[0]
    try:
        runs = int(argv[1]) if len(argv) > 1 else 3
        jobs = int(os.environ.get("JOBS", "4"))
        if runs < 1 or jobs < 1:
            raise ValueError
    except ValueError:
        print("RUNS and JOBS must be positive integers", file=sys.stderr)
        return 2
    try:
        pattern = re.compile(os.environ.get("QUERY", "."))
    except re.error as exc:
        print(f"QUERY is not a valid regex: {exc}", file=sys.stderr)
        return 2
    try:
        adapter = importlib.import_module(f"adapters.{name}")
    except ImportError as exc:
        print(f"no adapter {name!r}: {exc}", file=sys.stderr)
        return 2
    try:  # fail before any run if the adapter is not configured (missing env var, unfilled template)
        getattr(adapter, "env", dict)()
        adapter.command("probe", Path("."))
    except KeyError as exc:
        print(f"adapter {name!r} is not configured: missing environment variable {exc}", file=sys.stderr)
        return 2
    except (NotImplementedError, AttributeError, TypeError) as exc:
        print(f"adapter {name!r} is incomplete: {exc!r}", file=sys.stderr)
        return 2
    detect = getattr(adapter, "triggered", None) or default_triggered
    queries: list[dict[str, Any]] = [
        q for q in json.loads((HERE / "triggers.json").read_text(encoding="utf-8"))["queries"]
        if pattern.search(q["id"])
    ]  # fmt: skip
    if not queries:
        print("QUERY matches no query id", file=sys.stderr)
        return 2
    work = Path(os.environ.get("WORK") or tempfile.mkdtemp(prefix="vitae-triggers-"))
    errors: dict[tuple[str, int], str] = {}
    with ThreadPoolExecutor(max_workers=jobs) as pool:
        futures = {
            (q["id"], r): pool.submit(run_one, adapter, work / q["id"] / str(r), q["query"])
            for q in queries for r in range(1, runs + 1)
        }  # fmt: skip
        for key, future in futures.items():
            try:
                error = future.result()
            except Exception as exc:  # noqa: BLE001 - any failure of a run is an ERROR, never a silent miss
                error = f"{type(exc).__name__}: {exc}"
            if error:
                errors[key] = error
    agg: dict[str, list[bool]] = defaultdict(list)
    for q in queries:
        good = [r for r in range(1, runs + 1) if (q["id"], r) not in errors]
        if not good:
            print(f"{q['id']:4} {q['split']:10} should={int(q['should_trigger'])} ERROR (all {runs} runs failed)")
            continue
        hits = 0
        for r in good:
            text = (work / q["id"] / str(r) / "out.txt").read_text(encoding="utf-8", errors="replace")
            hits += bool(detect(text))
        rate = hits / len(good)
        ok = rate > 0.5 if q["should_trigger"] else rate < 0.5
        agg[q["split"]].append(ok)
        note = f" ({len(good)}/{runs} runs valid)" if len(good) < runs else ""
        print(f"{q['id']:4} {q['split']:10} should={int(q['should_trigger'])} rate={rate:.2f} "
              f"{'PASS' if ok else 'FAIL'}{note}")  # fmt: skip
    for split, oks in agg.items():
        print(f"{split}: {sum(oks)}/{len(oks)} pass (ERROR queries excluded)")
    if errors:
        print(f"\n{len(errors)} run(s) ERROR, excluded from the score (details in <run>/err.txt under {work}):")
        for (qid, r), why in errors.items():
            print(f"  {qid}/{r}: {why}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

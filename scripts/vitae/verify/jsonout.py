"""`--json`: the one-file gate (and --doctor) as one JSON object on stdout, diagnostics on stderr.

The gate code still prints its text lines; they are captured here and turned into the object. Gate lines
come from the `(Level, message)` tuples `registry.run_gates` recorded (so the check id is the gate's name
and a multi-line message stays whole); the few lines `_check_cv` prints itself are read back by their
level word. Whatever is not a check (the extraction dump, compile noise, the PASS banner) goes to stderr.

Verdicts: PASS (exit 0), FAIL (exit 1, the gate said so), ERROR (exit 2: usage error, unsupported mode, or an
exception inside the gate; the object carries `error`, the captured output goes to stderr).
"""
from __future__ import annotations

import io
import json
import re
import sys
from collections.abc import Callable
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from typing import TypeAlias

from vitae.core.level import Level
from vitae.verify import registry

_UNSUPPORTED = ("--all", "--gates", "--render", "--text", "--tune")
_LINE = re.compile(r"^(OK|INFO|WARN|FAIL|NEXT) +(\S.*)$")
_DUMP = "──── extraction"    # cv.py prints this line, then the raw PDF text, with no end marker
_AFTER_DUMP = re.compile(r"^(OK|INFO|WARN|FAIL|NEXT)  \S")   # what cv.py prints after the dump uses two spaces
_BANNER = re.compile(r"^PASS .*mechanical checks")
_LAYOUT_REVIEW = re.compile(r"^Layout review: (\S.*)$")   # printed by the gates after the PASS line (review_record.layout_report_line)
_NAME = re.compile(r"^([a-z][a-z0-9 _-]{0,24}?) *(?::|\()")
_FILL = re.compile(r"to (\d+)%")
Dispatch: TypeAlias = Callable[[list[str]], tuple[int, str | None]]


def skill_version() -> str | None:
    """`version:` of SKILL.md's frontmatter, None if the file or the key is not there."""
    try:
        text = (Path(__file__).resolve().parents[3] / "SKILL.md").read_text(encoding="utf-8")
    except OSError:
        return None
    m = re.search(r'^\s+version:\s*"?([^"\s]+)"?\s*$', text.split("\n---", 2)[0], re.M)
    return m.group(1) if m else None


def _checks(text: str, sink: list[tuple[str, Level, str]], dump_len: int | None = None) -> tuple[list[dict[str, str]], str | None]:
    """(checks, the PASS banner line) from the captured stdout; every other line goes to stderr."""
    lines, checks, banner, i, k, dumped = text.split("\n"), [], None, 0, 0, False
    while i < len(lines):
        if dumped and dump_len:     # the dump's length is known: its lines are CV text, whatever shape they have
            for ln in lines[i:i + dump_len]:
                print(ln, file=sys.stderr)
            i, dumped, dump_len = i + dump_len, False, None
            continue
        if k < len(sink):
            name, lvl, msg = sink[k]
            n = f"{lvl:<5} {msg}".count("\n") + 1
            if "\n".join(lines[i:i + n]) == f"{lvl:<5} {msg}":
                checks.append({"level": str(lvl), "check": name, "message": msg})
                i, k = i + n, k + 1
                continue
        if lines[i].startswith(_DUMP):
            dumped = True
            if dump_len:
                print(lines[i], file=sys.stderr)
                i += 1
                continue
        # Past the dump, when its length is unknown, a line is a check only in the two-space shape cv.py prints;
        # a CV heading such as "INFO SYSTEMS" is not (the length is known for the real gate: see registry.note_extraction).
        m = _LINE.match(lines[i]) if not dumped or _AFTER_DUMP.match(lines[i]) else None
        if m:
            nm = _NAME.match(m.group(2))
            checks.append({"level": "INFO" if m.group(1) == "NEXT" else m.group(1),
                           "check": nm.group(1) if nm else "cv", "message": m.group(2)})
        elif _BANNER.match(lines[i]):
            banner = lines[i]
        elif lines[i]:
            print(lines[i], file=sys.stderr)
        i += 1
    return checks, banner


def _layout_review(text: str) -> str | None:
    """The `<kind> [<model>]` of the `Layout review:` line the gate printed under its PASS line, None without one."""
    lines = text.split("\n")
    for i in range(len(lines) - 1, -1, -1):
        if lines[i].startswith("PASS "):
            for ln in lines[i + 1:]:
                if m := _LAYOUT_REVIEW.match(ln):
                    return m.group(1)
            return None
    return None


def _positionals(argv: list[str]) -> list[str]:
    rest = [a for a in argv if a not in ("--allow-placeholders", "--rebuild")]
    if "--facts" in rest:
        i = rest.index("--facts")
        rest = rest[:i] + rest[i + 2:]
    return rest


def _emit(obj: dict[str, object]) -> None:
    sys.stdout.write(json.dumps(obj, ensure_ascii=False) + "\n")


def run_json(argv: list[str], dispatch: Dispatch) -> tuple[int, None]:
    """Run `dispatch(argv)` (argv without --json), print the JSON object; returns (exit code, None) so `_run`
    prints no text footer."""
    mode = argv[0] if argv else ""
    if mode in _UNSUPPORTED:
        msg = f"--json supports the one-file gate and --doctor, not {mode}"
        print(msg, file=sys.stderr)
        _emit({"tool": "verify", "verdict": "ERROR", "exit_code": 2, "error": msg})
        return 2, None
    out, err = io.StringIO(), io.StringIO()
    sink: list[tuple[str, Level, str]] = []
    rc, footer, bad, crash = 0, None, False, None
    with redirect_stdout(out), redirect_stderr(err), registry.recording(sink):
        try:
            rc, footer = dispatch(argv)
        except SystemExit as e:
            if isinstance(e.code, int) and e.code in (0, 1) and mode == "--doctor":
                rc = e.code
            else:
                bad, rc = True, 2
                if isinstance(e.code, str):
                    print(e.code, file=sys.stderr)
        except Exception as e:      # kept broad: top-level; a gate crash is not a gate FAIL: exit 2, one JSON line with the type and message
            crash, rc = f"{type(e).__name__}: {e}", 2
    if crash:
        sys.stderr.write(out.getvalue() + err.getvalue())
        _emit({"tool": "verify", "verdict": "ERROR", "exit_code": 2, "error": crash})
        return 2, None
    if bad:
        sys.stderr.write(out.getvalue() + err.getvalue())
        _emit({"tool": "verify", "verdict": "ERROR", "exit_code": 2,
               "error": (err.getvalue().strip() or "usage error")})
        return 2, None
    sys.stderr.write(err.getvalue())
    checks, banner = _checks(out.getvalue(), sink, registry.extraction_lines())
    obj: dict[str, object] = {"tool": "doctor" if mode == "--doctor" else "verify"}
    if (v := skill_version()) is not None:
        obj["version"] = v
    if mode != "--doctor":
        pos = _positionals(argv)
        obj["file"] = pos[0] if pos else None
        if len(pos) > 1 and pos[1].isdigit():
            obj["pages_expected"] = int(pos[1])
        if len(pos) > 3 and pos[2].isdigit() and pos[3].isdigit():
            fills = [int(m.group(1)) for c in checks if c["check"] == "fill" for m in [_FILL.search(c["message"])] if m]
            obj["fill"] = {"min": int(pos[2]), "max": int(pos[3]), "measured": max(fills) if fills else None}
    obj.update(verdict="PASS" if rc == 0 else "FAIL", exit_code=rc, checks=checks,
               footer=footer if rc else None)   # as in text mode, the footer is only for a failure
    if banner:
        obj["summary"] = banner
    if rc == 0 and (layout := _layout_review(out.getvalue())):
        obj["layout_review"] = layout
    _emit(obj)
    return rc, None

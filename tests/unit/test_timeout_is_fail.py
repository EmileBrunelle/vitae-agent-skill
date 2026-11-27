"""A timeout is never a WARN, a skip or a silent fallback: a hung tool must end as `FAIL  <tool> timed out after N s`
(exit 1), because anything softer turns a hung tool into a false PASS. A tool that is NOT installed stays a WARN.

Fake tools are executables first on PATH that sleep past a monkeypatched small limit.
"""
from __future__ import annotations

import os
import struct
import subprocess
import sys
import time
import zlib
from pathlib import Path
from types import ModuleType

import pytest
from _paths import SCRIPTS
from vitae import fill
from vitae.core import env, proc
from vitae.verify import cli as verify_cli
from vitae.verify import cv, pdf, text, tune
from vitae.verify.groups import ink, query

LIMIT = 1
SLEEP = 8


def _tool(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, name: str, body: str = "") -> None:
    d = tmp_path / "bin"
    d.mkdir(exist_ok=True)
    exe = d / name
    exe.write_text(f"#!/bin/sh\n{body}\nexec sleep {SLEEP}\n", encoding="utf-8")
    exe.chmod(0o755)
    monkeypatch.setenv("PATH", f"{d}:/usr/bin:/bin")


def _fail_line(capsys: pytest.CaptureFixture[str], needle: str) -> None:
    out = capsys.readouterr()
    assert out.out.startswith(f"FAIL  {needle} timed out after 1 s"), out
    assert "Traceback" not in out.err


def _typst_cli_only(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(env, "_typst_py_probe", lambda: env.TypstPyProbe(None, "", "", False))
    monkeypatch.setattr(proc, "TYPST_S", LIMIT)


_VERSION = 'if [ "$1" = "--version" ]; then echo "typst 0.15.2"; exit 0; fi'


# ---- 1. bbox_pages / hidden-text gate
def test_hung_pdftotext_fails_the_hidden_text_gate(tmp_path, monkeypatch, capsys):
    _tool(tmp_path, monkeypatch, "pdftotext")
    monkeypatch.setattr(proc, "POPPLER_S", LIMIT)
    monkeypatch.setattr(pdf, "pdf_backend", lambda: "poppler")
    monkeypatch.setattr(text, "pdf_backend", lambda: "poppler")
    t0 = time.monotonic()
    with pytest.raises(SystemExit) as ei:
        proc.guarded(lambda: text.check_hidden_text(str(tmp_path / "x.pdf")))
    assert ei.value.code == 1 and time.monotonic() - t0 < SLEEP - 1
    _fail_line(capsys, "pdftotext")


def test_missing_pdftotext_is_still_a_warn(tmp_path, monkeypatch):
    monkeypatch.setenv("PATH", str(tmp_path))           # no pdftotext anywhere
    monkeypatch.setattr(pdf, "pdf_backend", lambda: "poppler")
    monkeypatch.setattr(text, "pdf_backend", lambda: "poppler")
    msgs = text.check_hidden_text(str(tmp_path / "x.pdf"))
    assert len(msgs) == 1 and "skipped" in msgs[0][1] and "not found" in msgs[0][1]


# ---- 2. typst query
def test_hung_typst_query_fails_and_is_not_memoized(tmp_path, monkeypatch, capsys, fresh_typst_probes):
    _tool(tmp_path, monkeypatch, "typst", _VERSION)
    _typst_cli_only(monkeypatch)
    typ = tmp_path / "cv.typ"
    typ.write_text("#set page()\nhello\n", encoding="utf-8")
    with pdf.run_memo() as memo:
        with pytest.raises(SystemExit) as ei:
            proc.guarded(lambda: query.typst_values(str(typ), "<mark>"))
        assert ei.value.code == 1 and memo.values == {}
    _fail_line(capsys, "typst query")


# ---- 3. pdftoppm in the ink gap
def test_hung_pdftoppm_fails_the_ink_gap(tmp_path, monkeypatch, capsys):
    _tool(tmp_path, monkeypatch, "pdftoppm")
    monkeypatch.setattr(proc, "POPPLER_S", LIMIT)
    monkeypatch.setattr(ink, "pdf_backend", lambda: "poppler")
    with pytest.raises(SystemExit) as ei:
        proc.guarded(lambda: ink._render_page(str(tmp_path / "x.pdf"), 1))
    assert ei.value.code == 1
    _fail_line(capsys, "pdftoppm")


# ---- 4. --tune aborts on the first compile timeout
def test_tune_probe_timeout_aborts_instead_of_reading_as_page_count_off(tmp_path, monkeypatch, capsys, fresh_typst_probes):
    _tool(tmp_path, monkeypatch, "typst", _VERSION)
    _typst_cli_only(monkeypatch)
    typ = tmp_path / "cv.typ"
    typ.write_text("#set page()\nhello\n", encoding="utf-8")
    t0 = time.monotonic()
    with pytest.raises(SystemExit) as ei:
        proc.guarded(lambda: tune._probe_text(str(typ), "#set page()\nhello\n", 1, "poppler"))
    assert ei.value.code == 1 and time.monotonic() - t0 < SLEEP - 1     # one probe, not a bisection of N
    _fail_line(capsys, "typst compile")


# ---- 5. doctor and route
def test_hung_typst_version_is_a_doctor_fail_and_the_cli_is_not_routed(tmp_path, monkeypatch, capsys, fresh_typst_probes):
    _tool(tmp_path, monkeypatch, "typst")
    monkeypatch.setattr(proc, "PROBE_S", LIMIT)
    api = ModuleType("typst")
    monkeypatch.setattr(env, "_typst_py_probe", lambda: env.TypstPyProbe(api, "0.15.2", "", True))
    assert env.check_typst() is False
    assert "FAIL  typst --version timed out after 1 s" in capsys.readouterr().out
    route = env.typst_route()
    assert (route.compile, route.query) == ("api", "api")       # typst-py takes over, as for a missing CLI


def test_hung_typst_version_without_typst_py_leaves_no_route(tmp_path, monkeypatch, fresh_typst_probes):
    _tool(tmp_path, monkeypatch, "typst")
    monkeypatch.setattr(proc, "PROBE_S", LIMIT)
    monkeypatch.setattr(env, "_typst_py_probe", lambda: env.TypstPyProbe(None, "", "", False))
    route = env.typst_route()
    assert (route.compile, route.query) == (None, None)


# ---- 6. the whole process tree dies
def _alive(pid: int) -> bool:
    try:
        state = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8").rsplit(")", 1)[1].split()[0]
    except OSError:
        return False
    return state != "Z"


@pytest.mark.skipif(os.name == "nt" or not Path("/proc/self/stat").exists(), reason="process groups and /proc: POSIX only")
def test_timeout_kills_the_grandchild_too(tmp_path, monkeypatch):
    pidfile = tmp_path / "grandchild.pid"
    d = tmp_path / "bin"
    d.mkdir()
    exe = d / "spawner"
    exe.write_text(f"#!/bin/sh\nsleep 30 &\necho $! > {pidfile}\nwait\n", encoding="utf-8")
    exe.chmod(0o755)
    monkeypatch.setenv("PATH", f"{d}:/usr/bin:/bin")
    t0 = time.monotonic()
    with pytest.raises(proc.ToolTimeout):
        proc.run(["spawner"], LIMIT)
    assert time.monotonic() - t0 < 10, "the pipes stayed open: the grandchild was not killed with its parent"
    pid = int(pidfile.read_text(encoding="utf-8"))
    deadline = time.monotonic() + 3
    while _alive(pid) and time.monotonic() < deadline:
        time.sleep(0.05)
    try:
        assert not _alive(pid), "the grandchild outlived the timeout"
    finally:
        if _alive(pid):
            os.kill(pid, 9)


# ---- 7. --all goes on after one deliverable times out
def test_all_reports_the_timed_out_file_and_checks_the_next(tmp_path, monkeypatch, capsys):
    for name in ("a.typ", "b.typ"):
        (tmp_path / name).write_text("// plain\nhello\n", encoding="utf-8")
    seen: list[str] = []

    def fake_run(argv, limit, *, name=None, capture=True):
        seen.append(os.path.basename(argv[2]))
        if argv[2].endswith("a.typ"):
            raise proc.ToolTimeout("verify.py", limit)
        return subprocess.CompletedProcess(list(argv), 0)

    monkeypatch.setattr(proc, "run", fake_run)
    rc = cv.check_all(str(tmp_path))
    out = capsys.readouterr().out
    assert seen == ["a.typ", "b.typ"] and rc == 1
    assert f"FAIL  {tmp_path / 'a.typ'}: verify timed out after {proc.RERUN_S:g} s" in out
    assert "FAIL — see above" in out


# ---- 8. a decompression bomb PNG
def _bomb_png(path: Path, side: int) -> None:
    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))
    ihdr = struct.pack(">IIBBBBB", side, side, 8, 0, 0, 0, 0)
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(b"\0")) + chunk(b"IEND", b""))


def test_huge_raster_png_is_one_fail_line(tmp_path):
    png = tmp_path / "bomb.png"
    _bomb_png(png, 60000)
    assert png.stat().st_size < 200
    r = subprocess.run([sys.executable, "-I", str(SCRIPTS / "measure_fill.py"), str(png)],
                       capture_output=True, text=True, check=False)
    assert r.returncode == 1 and "Traceback" not in r.stderr
    assert r.stderr.startswith(f"FAIL  {png}:") and len(r.stderr.strip().splitlines()) == 1
    assert fill.measure.__name__ == "measure"           # the module under test is the one the façade runs


# ---- 9. --gates refuses an academic CV
def test_gates_refuses_an_academic_cv(tmp_path, monkeypatch, capsys):
    typ, pdf_path = tmp_path / "ac.typ", tmp_path / "ac.pdf"
    typ.write_text("// vitae-academic: sections=1 entries=1\nhello\n", encoding="utf-8")
    pdf_path.write_bytes(b"%PDF-1.4\n")
    monkeypatch.setattr(sys, "argv", ["verify.py", "--gates", str(typ), str(pdf_path)])
    with pytest.raises(SystemExit) as ei:
        verify_cli._dispatch(["--gates", str(typ), str(pdf_path)])
    assert ei.value.code == 2
    assert "academic CV" in capsys.readouterr().err

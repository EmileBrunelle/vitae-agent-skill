"""Every typst call (compile, PNG render, query, fonts) follows `env.typst_route`, decided once per process: an old CLI on
PATH never compiles when the Python API can, and neither does it answer query / fonts when a full Python API is there."""
import os
import stat
import subprocess
import types
from pathlib import Path
from typing import ClassVar

import pytest
from vitae.core import env
from vitae.verify import pdf
from vitae.verify.groups import query

API_VERSION = "0.15.2"


class FakeCompiler:
    calls: ClassVar[list[str]] = []

    def __init__(self, src: str, **_kw: object) -> None:
        self.src = src

    def compile_with_warnings(self, **_kw: object) -> tuple[bytes, list[str]]:
        FakeCompiler.calls.append(f"compile {self.src}")
        return b"%PDF", []

    def query(self, selector: str, **_kw: object) -> str:
        FakeCompiler.calls.append(f"query {selector}")
        return '[{"text": "from-api"}]'

    def eval(self, *_a: object, **_kw: object) -> str:
        return "[]"


class FakeFonts:
    def __init__(self, **_kw: object) -> None:
        pass

    def families(self) -> list[str]:
        return ["ApiFont"]


API = types.ModuleType("typst")
API.Compiler = FakeCompiler   # type: ignore[attr-defined]
API.Fonts = FakeFonts         # type: ignore[attr-defined]


@pytest.fixture
def fake_cli(fresh_typst_probes, tmp_path, monkeypatch):
    """Install an executable `typst` first on PATH printing `version`; every other call appends its arguments to a log.
    Returns install(version) -> list of the CLI's invocations (read from the log)."""
    def install(version: str) -> Path:
        bindir = tmp_path / "bin"
        bindir.mkdir(exist_ok=True)
        log = tmp_path / "cli.log"
        exe = bindir / "typst"
        exe.write_text(
            "#!/bin/sh\n"
            f'if [ "$1" = "--version" ]; then echo "typst {version} (fake)"; exit 0; fi\n'
            f'echo "$@" >> "{log}"\n'
            'if [ "$1" = "fonts" ]; then echo CliFont; fi\n'
            'if [ "$1" = "query" ]; then echo \'[{"text": "from-cli"}]\'; fi\n',
            encoding="utf-8")
        exe.chmod(exe.stat().st_mode | stat.S_IEXEC)
        monkeypatch.setenv("PATH", f"{bindir}{os.pathsep}{os.environ['PATH']}")
        return log
    return install


def _api(monkeypatch, full: bool = True) -> None:
    FakeCompiler.calls = []
    monkeypatch.setattr(env, "_typst_py_probe", lambda: (API, API_VERSION, "", full))


def _typ(tmp_path: Path) -> str:
    src = tmp_path / "a.typ"
    src.write_text("hello", encoding="utf-8")
    return str(src)


def _calls(log: Path) -> list[str]:
    return log.read_text(encoding="utf-8").splitlines() if log.exists() else []


class TestOldCliWithPythonApi:
    def test_the_route_is_the_api_for_an_old_cli(self, fake_cli, monkeypatch):
        fake_cli("0.13.1")
        _api(monkeypatch)
        assert env.typst_route().compile == "api"

    def test_compile_goes_through_the_api(self, fake_cli, tmp_path, monkeypatch):
        log = fake_cli("0.13.1")
        _api(monkeypatch)
        ok, _ = pdf.typst_compile(_typ(tmp_path), str(tmp_path / "a.pdf"), standards=True)
        assert ok and _calls(log) == [] and FakeCompiler.calls == [f"compile {tmp_path / 'a.typ'}"]

    def test_fonts_go_through_the_api(self, fake_cli, monkeypatch):
        log = fake_cli("0.13.1")
        _api(monkeypatch)
        assert env.typst_fonts() == ["ApiFont"] and _calls(log) == []

    def test_query_goes_through_the_api(self, fake_cli, tmp_path, monkeypatch):
        log = fake_cli("0.13.1")
        _api(monkeypatch)
        assert query._typst_values(_typ(tmp_path), "<m>") == [{"text": "from-api"}]
        assert _calls(log) == []

    def test_old_cli_still_answers_query_and_fonts_when_the_api_cannot(self, fake_cli, tmp_path, monkeypatch):
        """A compile-only API has no query / fonts: the old CLI, which writes no PDF for them, is better than nothing."""
        log = fake_cli("0.13.1")
        _api(monkeypatch, full=False)
        assert env.typst_fonts() == ["CliFont"]
        assert query._typst_values(_typ(tmp_path), "<m>") == [{"text": "from-cli"}]
        assert [c.split()[0] for c in _calls(log)] == ["fonts", "query"]


class TestUsableCli:
    def test_new_cli_is_used_for_everything(self, fake_cli, tmp_path, monkeypatch):
        log = fake_cli("0.15.0")
        _api(monkeypatch)
        assert env.typst_route().compile == "cli"
        ok, _ = pdf.typst_compile(_typ(tmp_path), str(tmp_path / "a.pdf"))
        assert ok and env.typst_fonts() == ["CliFont"]
        assert [c.split()[0] for c in _calls(log)] == ["compile", "fonts"] and FakeCompiler.calls == []

    def test_png_render_follows_the_same_route(self, fake_cli, tmp_path, monkeypatch):
        log = fake_cli("0.13.1")
        _api(monkeypatch)
        pdf.render_pngs(_typ(tmp_path), str(tmp_path))
        assert _calls(log) == [] and FakeCompiler.calls == [f"compile {tmp_path / 'a.typ'}"]

    def test_no_route_is_a_failed_compile_not_a_crash(self, tmp_path, fake_typst):
        fake_typst()
        ok, err = pdf.compile_pdf(_typ(tmp_path), str(tmp_path / "a.pdf"))
        assert ok is False and "no usable typst" in err
        assert pdf.render_pngs(_typ(tmp_path), str(tmp_path)) == []


ALL_PROBES = {
    # id: (cli version, api module, api full) -> (compile route, query route)
    "old-cli+api": (("0.13.1", API, True), ("api", "api")),
    "new-cli+api": (("0.15.0", API, True), ("cli", "cli")),
    "new-cli, no-api": (("0.15.0", None, True), ("cli", "cli")),
    "cli-version-unreadable": (("?", None, True), ("cli", "cli")),
    "no-cli+api": ((None, API, True), ("api", "api")),
    "no-cli+compile-only-api": ((None, API, False), ("api", None)),
    "old-cli+compile-only-api": (("0.13.1", API, False), ("api", "cli")),
    "old-cli, no-api": (("0.13.1", None, True), (None, "cli")),
    "nothing": ((None, None, True), (None, None)),
}


@pytest.mark.parametrize("probes, routes", ALL_PROBES.values(), ids=ALL_PROBES.keys())
def test_the_route_decision(fake_typst, probes, routes):
    """One table for the whole decision: where a compile goes, where query / eval / fonts go, and whether they can."""
    cli, api, full = probes
    fake_typst(cli=cli, api=api, full=full)
    route = env.typst_route()
    assert (route.compile, route.query) == routes
    assert env.typst_can_query() is (routes[1] is not None)


def test_the_route_is_decided_once(fake_typst):
    fake_typst(cli="0.15.0")
    first = env.typst_route()
    fake_typst(cli="0.13.1")   # install() clears the cache; without it the first decision would stay
    assert env.typst_route() is not first
    assert env.typst_route() is env.typst_route()


class TestProbedOncePerProcess:
    """`which typst` and `typst --version` each run once, whoever asks and in whatever order (doctor included)."""

    @pytest.fixture
    def counts(self, fresh_typst_probes, monkeypatch):
        seen: dict[str, int] = {"which": 0, "version": 0}

        def which(name: str, *_a: object, **_k: object) -> str:
            seen["which"] += 1
            return "/usr/bin/typst"

        def run(argv: list[str], *_a: object, **_k: object) -> subprocess.CompletedProcess[str]:
            seen["version"] += argv[1:] == ["--version"]
            return subprocess.CompletedProcess(argv, 0, stdout="typst 0.15.0 (x)\n" if argv[1:] == ["--version"] else "Font\n", stderr="")

        monkeypatch.setattr(env.shutil, "which", which)
        monkeypatch.setattr(env.subprocess, "run", run)
        monkeypatch.setattr(env, "_typst_py_probe", lambda: (None, "", "", False))
        return seen

    def test_route_queries_fonts_and_doctor_share_one_probe(self, counts, capsys):
        for _ in range(3):
            env.typst_route()
            env.typst_can_query()
            env.typst_fonts()
            env.check_typst()
        assert counts == {"which": 1, "version": 1}
        assert "OK    typst 0.15.0 (CLI)" in capsys.readouterr().out

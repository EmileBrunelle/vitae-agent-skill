"""Every typst call (compile, query, fonts) follows `env.typst_cli_usable`: an old CLI on PATH never compiles when the
Python API can, and neither does it answer query / fonts when a full Python API is there."""
import os
import stat
import types
from pathlib import Path

import pytest
from vitae.core import env
from vitae.verify import pdf
from vitae.verify.groups import query

API_VERSION = "0.15.2"


class FakeCompiler:
    calls: list[str] = []

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
def fake_cli(tmp_path, monkeypatch):
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
    def test_decision_is_false_for_an_old_cli(self, fake_cli):
        fake_cli("0.13.1")
        assert env.typst_cli_usable() is False

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
        assert env.typst_cli_usable() is True
        ok, _ = pdf.typst_compile(_typ(tmp_path), str(tmp_path / "a.pdf"))
        assert ok and env.typst_fonts() == ["CliFont"]
        assert [c.split()[0] for c in _calls(log)] == ["compile", "fonts"] and FakeCompiler.calls == []

    def test_no_cli_is_not_usable(self, monkeypatch):
        monkeypatch.setenv("PATH", "")
        assert env.typst_cli_usable() is False

    def test_version_is_probed_once_per_process(self, fake_cli):
        fake_cli("0.15.0")
        assert env.typst_cli_usable() is True
        fake_cli("0.13.1")   # the CLI changed under us: the decision stays the one taken first
        assert env.typst_cli_usable() is True

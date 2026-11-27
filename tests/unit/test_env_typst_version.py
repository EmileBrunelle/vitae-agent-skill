"""Typst version parsing and the calibration (doctor) decision of vitae.core.env.check_typst, inputs injected."""
import types

import pytest
from vitae.core import env

# the doctor reads the CLI version through the once-per-process probe: each test starts with none cached
pytestmark = pytest.mark.usefixtures("fresh_typst_probes")


class TestVerTuple:
    @pytest.mark.parametrize("text, expected", [
        ("0.15.0", (0, 15)), ("0.15.1", (0, 15)), ("0.16.0", (0, 16)), ("0.9.3", (0, 9)),
        ("1.0.0", (1, 0)), ("0.15", (0, 15)), ("0.15.0-rc1", (0, 15)),
        ("typst 0.14.2 (abc123)", (0, 14)),
    ], ids=["0.15.0", "0.15.1", "0.16.0", "0.9.3", "1.0.0", "no-patch", "prerelease", "with-prefix"])
    def test_major_minor_of_first_x_dot_y(self, text, expected):
        assert env._ver_tuple(text) == expected

    @pytest.mark.parametrize("text", ["", "?", "garbage", "15", "v-"], ids=["empty", "qmark", "word", "one-number", "noise"])
    def test_unparsable_reads_as_oldest(self, text):
        assert env._ver_tuple(text) == (0, 0)

    def test_minor_compares_numerically_not_lexically(self):
        assert env._ver_tuple("0.9.0") < env._ver_tuple("0.15.0") < env._ver_tuple("0.100.0")

    def test_patch_level_is_ignored_by_the_calibration_comparison(self):
        assert env._ver_tuple("0.15.0") == env._ver_tuple("0.15.9") == env.TYPST_MIN


@pytest.fixture
def cli(monkeypatch):
    """Install a fake typst CLI printing `stdout` for --version; no process is spawned."""
    def install(stdout):
        monkeypatch.setattr(env.shutil, "which", lambda name: "/usr/bin/typst")
        monkeypatch.setattr(env.subprocess, "run", lambda *a, **k: types.SimpleNamespace(stdout=stdout))
    return install


class TestCheckTypstCli:
    def test_calibrated_version_is_ok_without_note(self, cli, capsys):
        cli("typst 0.15.0 (deadbeef)\n")
        assert env.check_typst() is True
        out = capsys.readouterr().out
        assert "OK    typst 0.15.0 (CLI)" in out and "NOTE" not in out and "DEGRADED" not in out

    def test_next_patch_release_is_not_flagged(self, cli, capsys):
        cli("typst 0.15.1 (x)")
        env.check_typst()
        out = capsys.readouterr().out
        assert "OK    typst 0.15.1" in out and "NOTE" not in out

    def test_newer_minor_is_ok_with_calibration_note(self, cli, capsys):
        cli("typst 0.16.0 (x)")
        assert env.check_typst() is True
        out = capsys.readouterr().out
        assert out.startswith("OK    typst 0.16.0") and "NOTE: fill targets are calibrated" in out
        assert "newer versions may measure differently" in out

    def test_older_minor_is_degraded_but_still_available(self, cli, capsys):
        cli("typst 0.14.9 (x)")
        assert env.check_typst() is True
        out = capsys.readouterr().out
        assert "DEGRADED  typst 0.14.9" in out and "OK    typst" not in out

    def test_before_pdf_standards_is_broken_and_unavailable(self, cli, capsys, monkeypatch):
        cli("typst 0.13.1 (x)")
        monkeypatch.setattr(env, "_typst_py_probe", lambda: (None, "", "", False))
        assert env.check_typst() is False
        out = capsys.readouterr().out
        assert out.startswith("BROKEN  typst 0.13.1 (CLI)") and "needs Typst 0.14 or newer" in out and "OK    typst" not in out

    def test_first_pdf_standards_release_is_not_broken(self, cli, capsys):
        cli("typst 0.14.0 (x)")
        assert env.check_typst() is True
        assert "BROKEN" not in capsys.readouterr().out

    def test_unreadable_version_output_is_assumed_fine(self, cli, capsys):
        cli("")
        assert env.check_typst() is True
        out = capsys.readouterr().out
        assert "OK    typst ? (CLI)" in out and "NOTE" not in out

    def test_cli_that_cannot_run_is_assumed_fine(self, monkeypatch, capsys):
        def boom(*a, **k):
            raise OSError("exec format error")
        monkeypatch.setattr(env.shutil, "which", lambda n: "/usr/bin/typst")
        monkeypatch.setattr(env.subprocess, "run", boom)
        assert env.check_typst() is True
        assert "OK    typst ? (CLI)" in capsys.readouterr().out


@pytest.fixture
def py_only(monkeypatch):
    """No CLI on PATH; the Python package probe returns the injected tuple."""
    def install(probe):
        monkeypatch.setattr(env.shutil, "which", lambda name: None)
        monkeypatch.setattr(env, "_typst_py_probe", lambda: probe)
    return install


class TestCheckTypstPythonApi:
    MOD = types.ModuleType("typst")

    def test_missing_everywhere_is_unavailable(self, py_only, capsys):
        py_only((None, "", "", False))
        assert env.check_typst() is False
        assert "MISSING  typst" in capsys.readouterr().out

    def test_too_old_package_is_broken(self, py_only, capsys):
        py_only((None, "", "TOOLOLD typst 0.11.1: no compile_with_warnings", False))
        assert env.check_typst() is False
        assert "BROKEN  typst: the Python package `typst` is too old" in capsys.readouterr().out

    def test_installed_but_unusable_is_broken(self, py_only, capsys):
        py_only((None, "", "import failed: boom", False))
        assert env.check_typst() is False
        assert "does not work (import failed: boom)" in capsys.readouterr().out

    def test_api_without_query_is_degraded_but_available(self, py_only, capsys):
        py_only((self.MOD, "0.15.0", "", False))
        assert env.check_typst() is True
        assert "DEGRADED  typst: Python API only" in capsys.readouterr().out

    def test_full_api_at_calibrated_version_is_ok(self, py_only, capsys):
        py_only((self.MOD, "0.15.0", "", True))
        assert env.check_typst() is True
        out = capsys.readouterr().out
        assert "OK    typst 0.15.0 (Python API" in out and "NOTE" not in out

    @pytest.mark.parametrize("full", [True, False], ids=["full-api", "no-query"])
    def test_before_pdf_standards_is_broken_and_unavailable(self, py_only, capsys, full):
        py_only((self.MOD, "0.13.2", "", full))
        assert env.check_typst() is False
        out = capsys.readouterr().out
        assert out.startswith("BROKEN  typst 0.13.2 (Python API)") and "needs Typst 0.14 or newer" in out

    def test_full_api_older_is_degraded(self, py_only, capsys):
        py_only((self.MOD, "0.14.0", "", True))
        assert env.check_typst() is True
        assert "DEGRADED  typst 0.14.0 (Python API)" in capsys.readouterr().out

    def test_full_api_newer_carries_note(self, py_only, capsys):
        py_only((self.MOD, "0.16.0", "", True))
        env.check_typst()
        assert "NOTE" in capsys.readouterr().out


class TestOldCliWithPythonApi:
    """A distro CLI older than 0.14 must not mask a working typst-py: the API is used (the API route)."""
    MOD = types.ModuleType("typst")

    def _setup(self, cli, monkeypatch, probe):
        cli("typst 0.13.1 (x)")
        monkeypatch.setattr(env, "_typst_py_probe", lambda: probe)

    def test_working_api_is_used_instead_of_the_old_cli(self, cli, monkeypatch, capsys):
        self._setup(cli, monkeypatch, (self.MOD, "0.15.2", "", True))
        assert env.check_typst() is True
        out = capsys.readouterr().out
        assert "BROKEN" not in out and "DEGRADED  typst 0.13.1 (CLI)" in out
        assert "too old" in out and "Python API (typst 0.15.2) is used" in out
        assert "OK    typst 0.15.2 (Python API" in out

    def test_compile_only_api_is_still_available(self, cli, monkeypatch):
        self._setup(cli, monkeypatch, (self.MOD, "0.15.2", "", False))
        assert env.check_typst() is True

    def test_api_older_than_pdf_standards_is_broken(self, cli, monkeypatch, capsys):
        self._setup(cli, monkeypatch, (self.MOD, "0.13.4", "", True))
        assert env.check_typst() is False
        assert "BROKEN  typst 0.13.1 (CLI)" in capsys.readouterr().out

    def test_broken_api_is_broken(self, cli, monkeypatch, capsys):
        self._setup(cli, monkeypatch, (None, "", "import failed: boom", False))
        assert env.check_typst() is False
        assert "BROKEN" in capsys.readouterr().out

    def test_preflight_does_not_fail_and_selects_the_api(self, cli, monkeypatch):
        self._setup(cli, monkeypatch, (self.MOD, "0.15.2", "", True))
        monkeypatch.setattr(env, "check_pillow", lambda: True)
        monkeypatch.setattr(env, "check_fonts", lambda: None)
        monkeypatch.setattr(env, "check_pdf_tools", lambda: (True, "pdfium"))
        monkeypatch.setattr(env, "importable", lambda m: True)
        monkeypatch.setattr(env, "check_pikepdf", lambda: None)
        ok, _ = env.preflight()
        assert ok and env.typst_route().compile == "api"

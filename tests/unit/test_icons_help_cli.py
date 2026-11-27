"""harvest_icons.py CLI: --help/-h as the sole argument print usage on stdout, exit 0; any other argument stays a positional folder."""
import subprocess
import sys

import pytest
from _paths import ROOT

sys.path.insert(0, str(ROOT / "scripts"))
from vitae import icons


def run(*args):
    return subprocess.run([sys.executable, "-I", str(ROOT / "scripts" / "harvest_icons.py"), *args],
                          capture_output=True, text=True)


@pytest.mark.parametrize("flag", ["--help", "-h"])
def test_help_prints_usage_and_exits_zero(flag):
    r = run(flag)
    assert r.returncode == 0 and "harvest_icons.py <folder>" in r.stdout and r.stderr == ""


def test_no_args_is_usage_error_on_stderr_exit_1():
    r = run()
    assert r.returncode == 1 and "harvest_icons.py <folder>" in r.stderr and r.stdout == ""


def test_help_with_other_args_is_not_help(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["harvest_icons.py", "--help", "x"])
    with pytest.raises(SystemExit) as e:
        icons.main()
    assert e.value.code != 0 and capsys.readouterr().out == ""


def test_dash_x_is_still_a_folder(monkeypatch, tmp_path):
    (tmp_path / "-x").mkdir()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(icons, "fetch_set", lambda prefix, names: ({}, {}))
    monkeypatch.setattr(sys, "argv", ["harvest_icons.py", "-x"])
    icons.main()
    assert (tmp_path / "-x" / "icons.typ").exists()

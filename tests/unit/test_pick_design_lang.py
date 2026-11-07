import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "pick_design.py"


def run(*extra):
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--name", "A B", "--field", "software",
         "--emit-typ", "--no-font-check", *extra],
        capture_output=True, text=True)


def test_default_en():
    r = run()
    assert r.returncode == 0 and 'lang: "en"' in r.stdout


def test_fr_and_region():
    r = run("--lang", "fr", "--region", "CA")
    assert 'lang: "fr", region: "ca"' in r.stdout
    assert "region:" not in run("--lang", "fr").stdout


def test_bad_lang_exits():
    for bad in ("FR", "french", "f", "f1"):
        r = run("--lang", bad)
        assert r.returncode == 2 and "--lang" in r.stderr

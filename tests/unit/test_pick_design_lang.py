"""pick_design.py --lang / --region: validation (lowercase ISO 639, 2-3 letters) and emission."""
import pytest
from _pick_design_cli import run

pytestmark = pytest.mark.integration


def emit(*extra):
    return run("--name", "A B", "--field", "software", "--emit-typ", *extra)


def test_default_en():
    r = emit()
    assert r.returncode == 0 and 'lang: "en"' in r.stdout


def test_fr_and_region():
    assert 'lang: "fr", region: "ca"' in emit("--lang", "fr", "--region", "CA").stdout


def test_region_omitted_without_region():
    assert "region:" not in emit("--lang", "fr").stdout


@pytest.mark.parametrize("code", ["fr", "fil"], ids=["two-letters", "three-letters"])
def test_valid_lang_accepted(code):
    r = emit("--lang", code)
    assert r.returncode == 0 and f'lang: "{code}"' in r.stdout


@pytest.mark.parametrize("bad", ["f", "frfr", "FR", "Fr", "french", "f1", ""],
                         ids=["one-letter", "four-letters", "uppercase", "capitalised", "word", "digit", "empty"])
def test_bad_lang_exits(bad):
    r = emit("--lang", bad)
    assert r.returncode == 2 and "--lang" in r.stderr

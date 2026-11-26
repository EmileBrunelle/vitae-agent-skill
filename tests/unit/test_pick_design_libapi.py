"""--init prints the lib.typ functions the CV calls, with their parameters, so lib.typ is never opened."""
import re

from _paths import ROOT
from _pick_design_cli import init
from vitae.design.libapi import public_signatures, signatures

TEMPLATES = ROOT / "templates"


def printed(tmp_path):
    r = init(tmp_path / "f", "Jane Roe", "accounting")
    assert r.returncode == 0, r.stderr
    line = next(ln for ln in r.stdout.splitlines() if ln.startswith("lib.typ API"))
    return line.split(": ", 1)[1].split("  ")


def test_signature_parsing_splits_positional_and_named():
    src = '#let f(a, b, c: (1, 2), d: "x,y", e: it => text(it)) = a\n#let g() = 1\n#let k = 2\n'
    assert signatures(src) == {"f": "f(a, b; c, d, e)", "g": "g()"}


def test_multiline_signature_and_nested_defaults():
    src = '#let f(a,\n       b: (x: 1, y: [ — ]),\n       c: 2) = {\n  1\n}\n'
    assert signatures(src) == {"f": "f(a; b, c)"}


def test_printed_names_are_the_lib_functions_the_worked_files_call(tmp_path):
    lib = (TEMPLATES / "lib.typ").read_text(encoding="utf-8")
    defs = set(re.findall(r"^#let ([A-Za-z][\w-]*)\(", lib, re.M))
    worked = [TEMPLATES / "resume.typ", *TEMPLATES.glob("families/*/*.typ")]
    called = {n for n in defs
              if any(re.search(r"(?<![\w-])%s\(" % re.escape(n), w.read_text(encoding="utf-8")) for w in worked)}
    names = {s.split("(")[0] for s in printed(tmp_path)}
    assert names == called
    assert {"entry", "srow", "masthead", "marks", "derive"} <= names
    assert "head-mark" not in names and "wd-norm" not in names          # internal helpers stay out


def test_every_printed_parameter_exists_in_lib(tmp_path):
    lib = (TEMPLATES / "lib.typ").read_text(encoding="utf-8")
    for sig in printed(tmp_path):
        name, rest = sig.split("(", 1)
        for p in re.split(r"[;,]\s*", rest.rstrip(")")):
            if p:
                assert p in lib.split("#let %s(" % name, 1)[1].split("\n#let ", 1)[0], sig


def test_a_function_no_worked_file_calls_is_not_public(tmp_path):
    (tmp_path / "families" / "x").mkdir(parents=True)
    (tmp_path / "lib.typ").write_text("#let used(a, b: 1) = a\n#let hidden(z) = z\n", encoding="utf-8")
    (tmp_path / "resume.typ").write_text("#used(1)\n", encoding="utf-8")
    assert public_signatures(tmp_path) == ["used(a; b)"]

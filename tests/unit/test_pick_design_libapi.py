"""--init prints the lib.typ functions the CV calls, with their parameters, so lib.typ is never opened."""
import re

from _paths import ROOT
from _pick_design_cli import init
from vitae.design.libapi import signatures

TEMPLATES = ROOT / "templates"


def public_signatures(lib_path):
    """Signatures of every top-level `#let` of `lib_path`, in file order."""
    return list(signatures(lib_path.read_text(encoding="utf-8")).values())


def printed(tmp_path):
    r = init(tmp_path / "f", "Jane Roe", "accounting")
    assert r.returncode == 0, r.stderr
    line = next(ln for ln in r.stdout.splitlines() if ln.startswith("lib.typ API"))
    return line.split(": ", 1)[1].split("  ")


def test_signature_parsing_splits_positional_and_named():
    src = '#let f(a, b, c: (1, 2), d: "x,y", e: it => text(it)) = a\n#let g() = 1\n#let k = 2\n'
    assert signatures(src) == {"f": "f(a, b; c, d, e)", "g": "g()", "k": "k"}


def test_multiline_signature_and_nested_defaults():
    src = '#let f(a,\n       b: (x: 1, y: [ — ]),\n       c: 2) = {\n  1\n}\n'
    assert signatures(src) == {"f": "f(a; b, c)"}


# Independent expectation: the primitive names core.md documents (parsed from its table)
# plus values and functions worked files are known to use, hand-listed.
HAND = {"runhead", "photo", "workday", "wd-page", "ghost", "wd-section", "accent-band", "drawn-marker"}


def core_primitives():
    core = (ROOT / "references" / "design" / "core.md").read_text(encoding="utf-8")
    table = core.split("## Structure primitives", 1)[1].split("\n\n", 3)[2]
    return {n for row in table.splitlines()[2:] for n in re.findall(r"`([a-z-]+)`", row.split("|")[1])}


def test_printed_names_cover_every_primitive_an_agent_needs(tmp_path):
    out = printed(tmp_path)
    names = {re.split(r"[(\s]", s)[0] for s in out}
    assert core_primitives() >= {"entry", "runhead", "photo", "pmark"}      # the parser found the table
    assert core_primitives() | HAND <= names
    assert len(names) == len(out)


def test_values_print_bare_and_functions_with_parameters(tmp_path):
    out = printed(tmp_path)
    assert "workday" in out and "ghost" in out
    assert any(s.startswith("runhead(") for s in out) and any(s.startswith("photo(") for s in out)


def test_content_block_call_style_and_value_exports_are_public(tmp_path):
    (tmp_path / "lib.typ").write_text("#let rh(n, st: it => it) = n\n#let val = 3\n#let _x(a) = a\n",
                                      encoding="utf-8")
    assert public_signatures(tmp_path / "lib.typ") == ["rh(n; st)", "val"]


def test_folder_lib_not_skill_lib_is_the_source(tmp_path):
    f = tmp_path / "f"
    assert init(f, "Jane Roe", "accounting").returncode == 0
    old = (f / "lib.typ").read_text(encoding="utf-8").replace("#let runhead(", "#let renamed-away(")
    (f / "lib.typ").write_text(old, encoding="utf-8")
    r = init(f, "Jane Roe", "accounting", "--force")
    line = next(ln for ln in r.stdout.splitlines() if ln.startswith("lib.typ API"))
    assert r.returncode == 0 and "kept existing" in r.stdout
    names = {re.split(r"[(\s]", x)[0] for x in line.split(": ", 1)[1].split("  ")}
    assert "runhead" not in names and "renamed-away" in names


def test_escaped_quote_and_comments_in_parameters():
    src = ('#let f(a, b: "x\\"), y", c: 1) = a\n'
           '#let g(a, // a ) bracket and a " quote\n  b: 2, /* ( " */ c: 3) = a\n')
    assert signatures(src) == {"f": "f(a; b, c)", "g": "g(a; b, c)"}


def test_unbalanced_list_degrades_instead_of_aborting(tmp_path):
    from vitae.design.libapi import api_line
    lib = tmp_path / "lib.typ"
    lib.write_text("#let ok(a) = a\n#let broken(a, b: (1) = a\n", encoding="utf-8")
    line = api_line(lib)
    assert line.startswith("ok(a)  broken(?)") and "WARN" in line and "broken" in line.splitlines()[1]


def test_init_still_writes_every_file_with_a_hostile_lib(tmp_path):
    f = tmp_path / "f"
    assert init(f, "Jane Roe", "accounting").returncode == 0
    (f / "lib.typ").write_text('#let weird(a, b: "\\"( ") = a\n#let broken(a = 1\n', encoding="utf-8")
    r = init(f, "Jane Roe", "accounting", "--force")
    assert r.returncode == 0, r.stderr
    assert "WARN" in r.stdout and (f / "icons.typ").exists()


def test_every_printed_parameter_exists_in_lib(tmp_path):
    lib = (TEMPLATES / "lib.typ").read_text(encoding="utf-8")
    for sig in (x for x in printed(tmp_path) if "(" in x):
        name, rest = sig.split("(", 1)
        for p in re.split(r"[;,]\s*", rest.rstrip(")")):
            if p:
                assert p in lib.split("#let {}(".format(name), 1)[1].split("\n#let ", 1)[0], sig


def test_signature_of_every_value_and_function_is_listed_in_file_order(tmp_path):
    lib = tmp_path / "lib.typ"
    lib.write_text("#let used(a, b: 1) = a\n#let v = 1\n#let w(z) = z\n", encoding="utf-8")
    assert public_signatures(lib) == ["used(a; b)", "v", "w(z)"]


def _old_lib_folder(tmp_path):
    """A CV folder whose lib.typ predates `contact()`: `nb` is defined, `contact` is not."""
    f = tmp_path / "f"
    assert init(f, "Jane Roe", "accounting").returncode == 0
    lib = (f / "lib.typ").read_text(encoding="utf-8").replace("#let contact(", "#let contact-gone(")
    (f / "lib.typ").write_text(lib, encoding="utf-8")
    return f


def test_init_warns_when_the_kept_lib_is_old(tmp_path):
    f = _old_lib_folder(tmp_path)
    r = init(f, "Jane Roe", "accounting", "--force")
    warn = [ln for ln in r.stdout.splitlines() if ln.startswith("WARN") and "OLD lib.typ" in ln]
    assert r.returncode == 0 and len(warn) == 1 and "cp " in warn[0]


def test_init_no_old_lib_warning_for_a_current_or_merely_edited_lib(tmp_path):
    f = tmp_path / "f"
    assert init(f, "Jane Roe", "accounting").returncode == 0
    (f / "lib.typ").write_text((f / "lib.typ").read_text(encoding="utf-8") + "\n#let extra = 1\n", encoding="utf-8")
    r = init(f, "Jane Roe", "accounting", "--force")
    assert "kept existing" in r.stdout and "OLD lib.typ" not in r.stdout


def test_verify_names_an_old_lib(tmp_path):
    from vitae.verify.cv import check_lib_integrity
    f = _old_lib_folder(tmp_path)
    out = check_lib_integrity(str(f / "cv.typ"), str(ROOT))
    assert out and "OLD lib.typ" in out[0][1]

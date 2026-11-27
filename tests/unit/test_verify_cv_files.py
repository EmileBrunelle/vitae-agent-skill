"""verify.cv: file classification, the --all sweep (subprocess faked) and the lib.typ integrity gate."""
import inspect
from collections.abc import Callable
from pathlib import Path
from types import SimpleNamespace
from typing import ClassVar

import pytest
from vitae.core import proc
from vitae.core.base import LEADING_FAMILY_RATIO_WARN, LOWERED_FILL_FLOOR
from vitae.core.env import PdfBackend, PdfCheck
from vitae.core.level import Level
from vitae.verify import cv
from vitae.verify import gates as real_gates
from vitae.verify import layout as real_layout
from vitae.verify import pdf as real_pdf
from vitae.verify.cv import BODY_SIZE_WARN, LEADING_WARN, _leading_warn

LIB_SRC = "#let derive() = 1\n"


# ---------- pages_from_name ----------

@pytest.mark.parametrize("name,pages", [
    ("cv-2page.typ", "2"), ("cv_2pages.typ", "2"), ("cv-2p.typ", "2"), ("CV-2PAGE.typ", "2"),
    ("cv-2 page.typ", "2"), ("cv-2page-fr.typ", "2"),
    ("cv.typ", "1"), ("cv-1page.typ", "1"), ("cv-2pagex.typ", "1"), ("cv-3page.typ", "1"),
    ("cv2page.typ", "1"), ("cv-22.typ", "1"),
])
def test_pages_from_name(name, pages):
    assert cv.pages_from_name(name) == pages


def test_pages_from_name_reads_only_the_basename():
    assert cv.pages_from_name("/work/x-2page/cv.typ") == "1"


# ---------- is_gated ----------

@pytest.mark.parametrize("name", ["cv.typ", "resume.typ", "guideline.typ", "lettres.typ", "discover.typ", "coverage.typ"])
def test_ordinary_names_are_gated_without_reading_the_file(tmp_path, name):
    assert cv.is_gated(str(tmp_path / name))      # the file does not even exist


@pytest.mark.parametrize("name", ["guide.typ", "Guide.typ", "lettre.typ", "letter.typ", "cover.typ", "readme.typ",
                                  "lisez-moi.typ", "cv-letter.typ", "cover_letter.typ", "guide2.typ", "1guide.typ"])
def test_companion_names_are_skipped_unless_they_carry_a_header(tmp_path, name):
    p = tmp_path / name
    p.write_text("#set page()\n", encoding="utf-8")
    assert not cv.is_gated(str(p))
    p.write_text("// vitae: pages=1\n", encoding="utf-8")
    assert cv.is_gated(str(p))


def test_missing_companion_file_is_not_gated(tmp_path):
    assert not cv.is_gated(str(tmp_path / "guide.typ"))


def test_header_beyond_4096_bytes_does_not_opt_in(tmp_path):
    p = tmp_path / "guide.typ"
    p.write_text("x" * 4090 + "\n// vitae: pages=1\n", encoding="utf-8")
    assert not cv.is_gated(str(p))
    p.write_text("x" * 4000 + "\n// vitae: pages=1\n", encoding="utf-8")
    assert cv.is_gated(str(p))


def test_header_regex_reads_pages_and_fill():
    m = cv.HEADER_RE.search("// vitae: pages=2 fill=70-85\n")
    assert m and m.groups() == ("2", "70", "85")
    m = cv.HEADER_RE.search("// vitae: pages=1\n")
    assert m and m.groups() == ("1", None, None)
    assert cv.HEADER_RE.search("body\n//vitae:   pages=3\n")      # any line start, spaces around the colon
    assert not cv.HEADER_RE.search("x // vitae: pages=1\n")       # not at line start


# ---------- is_academic / is_letter ----------

@pytest.mark.parametrize("fn,marker", [(cv.is_academic, cv.ACADEMIC_MARKER), (cv.is_letter, cv.LETTER_MARKER)])
def test_marker_detection_window_and_missing_file(tmp_path, fn, marker):
    p = tmp_path / "a.typ"
    p.write_text(marker + "\n", encoding="utf-8")
    assert fn(str(p))
    p.write_text("x" * 3900 + marker, encoding="utf-8")
    assert fn(str(p))
    p.write_text("x" * 4090 + marker, encoding="utf-8")
    assert not fn(str(p))                                         # only the first 4 KiB is read
    p.write_text("#set page()\n", encoding="utf-8")
    assert not fn(str(p))
    assert not fn(str(tmp_path / "missing.typ"))


def test_academic_and_letter_markers_are_distinct(tmp_path):
    p = tmp_path / "a.typ"
    p.write_text(cv.ACADEMIC_MARKER, encoding="utf-8")
    assert cv.is_academic(str(p)) and not cv.is_letter(str(p))
    p.write_text(cv.LETTER_MARKER, encoding="utf-8")
    assert cv.is_letter(str(p)) and not cv.is_academic(str(p))


# ---------- check_all (the per-file subprocess is faked) ----------

@pytest.fixture
def sweep(monkeypatch):
    calls = []
    codes = {}

    def fake_run(cmd, *_a, **kw):
        calls.append(cmd)
        return SimpleNamespace(returncode=codes.get(cmd[2], 0))

    monkeypatch.setattr(proc, "run", fake_run)
    return calls, codes


def _w(d, name, text="#set page()\n"):
    p = d / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return str(p)


def test_empty_directory_fails_with_a_message(tmp_path, capsys, sweep):
    assert cv.check_all(str(tmp_path)) == 1
    assert capsys.readouterr().out.strip() == f"no .typ found under {tmp_path}"


def test_only_skipped_files_fail_and_count_them(tmp_path, capsys, sweep):
    _w(tmp_path, "guide.typ")
    _w(tmp_path, "readme.typ")
    assert cv.check_all(str(tmp_path)) == 1
    out = capsys.readouterr().out
    assert out.strip().endswith("2 skipped, 0 checked")
    assert out.count("SKIP  ") == 2 and "(name matches a non-CV deliverable, no `// vitae:` header)" in out
    assert not sweep[0]


def test_shared_code_academic_and_letter_files_are_not_swept(tmp_path, capsys, sweep):
    _w(tmp_path, "lib.typ")
    _w(tmp_path, "libextra.typ")
    _w(tmp_path, "icons.typ")
    _w(tmp_path, "icons-fa.typ")
    _w(tmp_path, "acad.typ", cv.ACADEMIC_MARKER + "\n")
    _w(tmp_path, "lett.typ", cv.LETTER_MARKER + "\n")
    _w(tmp_path, "mylib.typ")                                      # only a PREFIX is excluded
    _w(tmp_path, "sub/deep/cv.typ")                                # recursive
    assert cv.check_all(str(tmp_path)) == 0
    swept = sorted(c[2] for c in sweep[0])
    assert sorted(s.rsplit("/", 1)[-1] for s in swept) == ["cv.typ", "mylib.typ"]


def test_header_args_are_passed_and_flags_forwarded(tmp_path, capsys, sweep):
    t = _w(tmp_path, "cv.typ", "// vitae: pages=2 fill=70-85\n")
    assert cv.check_all(str(tmp_path), allow_placeholders=True, rebuild=True) == 0
    (cmd,) = sweep[0]
    assert cmd[0] and cmd[1].endswith("verify.py") and cmd[2:] == [t, "2", "70", "85", "--allow-placeholders", "--rebuild"]
    out = capsys.readouterr().out
    assert f"=== {t}  (expects 2 70 85)" in out
    assert "inferred" not in out and "NOTE" not in out
    assert out.splitlines()[-2:] == ["", "PASS — 1 deliverable(s), all siblings checked together"]


def test_header_pages_only_passes_one_arg_and_no_flags_by_default(tmp_path, sweep):
    t = _w(tmp_path, "cv.typ", "// vitae: pages=1\n")
    cv.check_all(str(tmp_path))
    assert sweep[0][0][2:] == [t, "1"]


def test_headerless_file_takes_pages_from_name_and_is_reported(tmp_path, capsys, sweep):
    one = _w(tmp_path, "cv.typ")
    two = _w(tmp_path, "cv-2page.typ")
    assert cv.check_all(str(tmp_path)) == 0
    assert sorted(c[2:] for c in sweep[0]) == sorted([[one, "1"], [two, "2"]])
    out = capsys.readouterr().out
    assert "(expects 2 — inferred from the file name, no header)" in out
    assert ("NOTE — page count inferred from the file name, fill not checked "
            "(add `// vitae: pages=N fill=A-B` to pin either):") in out.splitlines()
    assert f"  {one}\n" in out and f"  {two}\n" in out


def test_a_failing_file_fails_the_sweep_but_all_files_run(tmp_path, capsys, sweep):
    calls, codes = sweep
    a = _w(tmp_path, "a.typ")
    b = _w(tmp_path, "b.typ")
    _w(tmp_path, "c.typ")
    codes[b] = 1
    assert cv.check_all(str(tmp_path)) == 1
    assert len(calls) == 3                                         # the failure after a pass does not stop it
    out = capsys.readouterr().out
    assert out.splitlines()[-1] == "FAIL — see above" and out.splitlines()[-2] == "" and "PASS" not in out
    codes[b] = 0
    codes[a] = 1                                                   # an early failure is not erased by later passes
    assert cv.check_all(str(tmp_path)) == 1


def test_skipped_header_file_is_swept_but_listed_files_not(tmp_path, capsys, sweep):
    _w(tmp_path, "guide.typ")
    h = _w(tmp_path, "letter.typ", "// vitae: pages=1\n")
    assert cv.check_all(str(tmp_path)) == 0
    assert [c[2] for c in sweep[0]] == [h]
    assert capsys.readouterr().out.count("SKIP  ") == 1


# ---------- placeholders_allowed edge ----------

def test_sweep_runs_verify_py_sitting_next_to_the_vitae_package(tmp_path, sweep):
    import os

    import vitae
    _w(tmp_path, "cv.typ")
    cv.check_all(str(tmp_path))
    script = sweep[0][0][1]
    assert os.path.basename(script) == "verify.py"
    assert os.path.dirname(script) == os.path.dirname(os.path.dirname(os.path.abspath(vitae.__file__)))


# ---------- check_lib_integrity ----------

@pytest.fixture
def skill(tmp_path):
    d = tmp_path / "skill"
    (d / "templates").mkdir(parents=True)
    (d / "templates" / "lib.typ").write_text(LIB_SRC, encoding="utf-8")
    return str(d)


def _cv(tmp_path, text, name="cv.typ"):
    return _w(tmp_path / "work", name, text)


def test_no_import_and_no_sibling_lib_is_clean(tmp_path, skill):
    assert cv.check_lib_integrity(_cv(tmp_path, "hello\n"), skill) == []


def test_identical_lib_is_clean_even_with_bom_and_crlf(tmp_path, skill):
    t = _cv(tmp_path, '#import "lib.typ": *\n')
    lib = tmp_path / "work" / "lib.typ"
    lib.write_bytes(b"\xef\xbb\xbf" + LIB_SRC.replace("\n", "\r\n").encode())
    assert cv.check_lib_integrity(t, skill) == []
    lib.write_bytes(LIB_SRC.encode())
    assert cv.check_lib_integrity(t, skill) == []


def test_edited_lib_fails_with_the_copy_command(tmp_path, skill):
    t = _cv(tmp_path, '#import "lib.typ": *\n')
    (tmp_path / "work" / "lib.typ").write_text("#let derive() = 2\n", encoding="utf-8")
    ((lvl, msg),) = cv.check_lib_integrity(t, skill)
    assert lvl == Level.FAIL
    assert msg.startswith("lib.typ differs from the skill's (older release or edited): copy it again: cp ")
    assert f"{skill}/templates/lib.typ" in msg and f"{tmp_path}/work/" in msg


def test_a_one_byte_difference_is_detected(tmp_path, skill):
    t = _cv(tmp_path, '#import "lib.typ": *\n')
    (tmp_path / "work" / "lib.typ").write_text(LIB_SRC + " ", encoding="utf-8")
    assert cv.check_lib_integrity(t, skill)[0][0] == Level.FAIL


def test_missing_imported_lib_fails(tmp_path, skill):
    t = _cv(tmp_path, '#import "lib.typ": *\n')
    ((lvl, msg),) = cv.check_lib_integrity(t, skill)
    assert lvl == Level.FAIL and msg.startswith("lib.typ is imported but missing — copy it: cp ")


def test_import_outside_the_folder_fails_and_says_to_copy_next_to_cv(tmp_path, skill):
    t = _cv(tmp_path, '#import "../lib.typ": *\n')
    ((lvl, msg),) = cv.check_lib_integrity(t, skill)
    assert lvl == Level.FAIL
    assert msg.startswith('cv.typ imports "../lib.typ" (outside this folder): change the import to ')
    assert f"cp {skill}/templates/lib.typ {tmp_path}/work/" in msg
    # a correct copy up there makes it pass: the outside import is accepted when the file is identical
    (tmp_path / "lib.typ").write_text(LIB_SRC, encoding="utf-8")
    assert cv.check_lib_integrity(t, skill) == []


def test_outside_import_with_a_differing_copy_still_fails(tmp_path, skill):
    t = _cv(tmp_path, '#import "../lib.typ": *\n')
    (tmp_path / "lib.typ").write_text("#let x = 1\n", encoding="utf-8")
    assert cv.check_lib_integrity(t, skill)[0][0] == Level.FAIL


def test_lib_reached_through_a_family_file_is_followed(tmp_path, skill):
    t = _cv(tmp_path, '#import "family.typ": *\n')
    _w(tmp_path / "work", "family.typ", '#import "lib.typ": *\n')
    ((lvl, msg),) = cv.check_lib_integrity(t, skill)
    assert lvl == Level.FAIL and "is imported but missing" in msg
    (tmp_path / "work" / "lib.typ").write_text(LIB_SRC, encoding="utf-8")
    assert cv.check_lib_integrity(t, skill) == []


def test_family_file_outside_import_is_not_the_cv_importing_it(tmp_path, skill):
    # the CV's own file imports a family file; only the family file climbs out: no "copy next to cv.typ" rule
    t = _cv(tmp_path, '#import "family.typ": *\n')
    _w(tmp_path / "work", "family.typ", '#import "../lib.typ": *\n')
    (tmp_path / "lib.typ").write_text("#let x = 1\n", encoding="utf-8")
    ((lvl, msg),) = cv.check_lib_integrity(t, skill)
    assert lvl == Level.FAIL and msg.startswith("lib.typ differs from the skill's")


def test_import_cycle_terminates(tmp_path, skill):
    t = _cv(tmp_path, '#import "a.typ": *\n')
    _w(tmp_path / "work", "a.typ", '#import "cv.typ": *\n')
    assert cv.check_lib_integrity(t, skill) == []


def test_rooted_import_resolves_from_the_cv_folder(tmp_path, skill):
    t = _cv(tmp_path, '#import "sub/f.typ": *\n')
    _w(tmp_path / "work", "sub/f.typ", '#import "/lib.typ": *\n')          # "/" = the CV's own folder
    (tmp_path / "work" / "lib.typ").write_text(LIB_SRC, encoding="utf-8")
    assert cv.check_lib_integrity(t, skill) == []
    (tmp_path / "work" / "lib.typ").write_text("#let x = 1\n", encoding="utf-8")
    ((lvl, msg),) = cv.check_lib_integrity(t, skill)
    assert lvl == Level.FAIL and msg.startswith("lib.typ differs")


def test_an_unreadable_import_does_not_stop_the_search(tmp_path, skill):
    t = _cv(tmp_path, '#import "gone.typ": *\n#import "family.typ": *\n')
    _w(tmp_path / "work", "family.typ", '#import "lib.typ": *\n')
    ((lvl, msg),) = cv.check_lib_integrity(t, skill)
    assert lvl == Level.FAIL and "is imported but missing" in msg


def test_an_already_seen_file_does_not_stop_the_search(tmp_path, skill):
    t = _cv(tmp_path, '#import "a.typ": *\n#import "b.typ": *\n')
    _w(tmp_path / "work", "a.typ", '#import "b.typ": *\n')
    _w(tmp_path / "work", "b.typ", '#import "c.typ": *\n')
    _w(tmp_path / "work", "c.typ", '#import "lib.typ": *\n')
    ((lvl, msg),) = cv.check_lib_integrity(t, skill)
    assert lvl == Level.FAIL and "is imported but missing" in msg


def test_commented_out_import_is_ignored(tmp_path, skill):
    t = _cv(tmp_path, '// #import "lib.typ": *\nhello\n')
    assert cv.check_lib_integrity(t, skill) == []


def test_parenthesised_import_form_is_recognised(tmp_path, skill):
    t = _cv(tmp_path, '#import( "lib.typ": *)\n')
    assert cv.check_lib_integrity(t, skill)[0][0] == Level.FAIL     # imported, missing


def test_unresolved_sibling_lib_warns_instead_of_checking(tmp_path, skill):
    t = _cv(tmp_path, "hello\n")
    (tmp_path / "work" / "lib.typ").write_text("#let x = 1\n", encoding="utf-8")
    ((lvl, msg),) = cv.check_lib_integrity(t, skill)
    assert lvl == Level.WARN
    assert msg.startswith("lib import not recognised: a lib.typ sits next to the CV but no #import ")
    assert msg.endswith("resolves to it, so its integrity was NOT checked")


def test_only_a_lib_typ_import_counts(tmp_path, skill):
    t = _cv(tmp_path, '#import "other.typ": *\n')
    _w(tmp_path / "work", "other.typ", "#let x = 1\n")
    assert cv.check_lib_integrity(t, skill) == []


def test_missing_reference_lib_means_no_check(tmp_path, skill):
    import os
    os.remove(f"{skill}/templates/lib.typ")
    t = _cv(tmp_path, '#import "lib.typ": *\n')
    assert cv.check_lib_integrity(t, skill) == []
    (tmp_path / "work" / "lib.typ").write_text("x", encoding="utf-8")
    assert cv.check_lib_integrity(t, skill) == []


def test_default_skill_dir_is_the_repository_and_ships_clean_templates():
    from pathlib import Path
    root = Path(cv.__file__).resolve().parents[3]
    fam = root / "templates" / "families" / "swiss-grid" / "resume.typ"
    assert cv.check_lib_integrity(str(fam)) == []


# ---------- _body_size_warn ----------

def _size_cv(tmp_path, size):
    p = tmp_path / "cv.typ"
    p.write_text(f"#set text(size: {size}pt)\nbody\n", encoding="utf-8")
    return str(p)


@pytest.mark.parametrize("size,warns", [(10.5, False), (BODY_SIZE_WARN, False), (BODY_SIZE_WARN + 0.01, True), (BODY_SIZE_WARN + 0.5, True),
                                       (BODY_SIZE_WARN + 3, True), (BODY_SIZE_WARN - 2, False)])
def test_body_size_warns_strictly_above_the_threshold(tmp_path, size, warns):
    out = cv._body_size_warn(_size_cv(tmp_path, size))
    assert bool(out) == warns, out


def test_body_size_warn_message_names_size_and_threshold(tmp_path):
    out = cv._body_size_warn(_size_cv(tmp_path, 12.5))
    assert out.startswith(f"WARN  body text 12.5pt (shipped templates stay at 10.5-11pt; warns above {BODY_SIZE_WARN:g}pt)")
    assert "add a real fact" in out and "accept the lower fill and tell the user" in out


def test_body_size_warn_silent_without_a_size_or_file(tmp_path):
    p = tmp_path / "cv.typ"
    p.write_text("body\n", encoding="utf-8")
    assert cv._body_size_warn(str(p)) == ""
    assert cv._body_size_warn(str(tmp_path / "missing.typ")) == ""


# ---------- check_cv (every collaborator faked: this tests the gate's own decisions and messages) ----------

class Env:
    """Knobs for the faked pipeline; `run` calls `check_cv` and returns (rc, footer, printed lines)."""
    pages = "1"
    pngs = ("p1.png",)
    fills: ClassVar[dict[str, str]] = {"p1.png": "ink from 3% to 95%"}
    err = ""
    compile_ok = True
    preflight_ok = True
    backend: PdfBackend = "poppler"
    record = ()
    clip = ()
    ws = ()
    lib = ()
    layout = None
    can_query = False
    boxes: ClassVar[list[list[object]]] = [[]]
    # set by the `env` fixture
    dir: Path
    calls: dict[str, list[tuple[tuple[object, ...], dict[str, object]]]]
    capsys: pytest.CaptureFixture[str]
    run: Callable[..., tuple[int, str | None, str]]


@pytest.fixture
def env(monkeypatch, tmp_path):
    e = Env()
    e.dir = tmp_path
    e.calls = {}

    def rec(name, ret):
        def f(*a, **k):
            e.calls.setdefault(name, []).append((a, k))
            return ret() if callable(ret) else ret
        return f

    monkeypatch.setattr(cv, "preflight", lambda: PdfCheck(e.preflight_ok, e.backend))
    monkeypatch.setattr(cv, "check_lib_integrity", lambda t: list(e.lib))
    monkeypatch.setattr(cv, "ensure_icons", lambda t: None)
    monkeypatch.setattr(cv, "compile_or_messages",
                        lambda t, p: (e.err, []) if e.compile_ok else ("", real_pdf.compile_failure_messages(e.err)))
    monkeypatch.setattr(cv, "count_pages", rec("count_pages", lambda: e.pages))
    monkeypatch.setattr(cv, "word_boxes", rec("word_boxes", lambda: e.boxes))
    monkeypatch.setattr(cv, "render_pngs", rec("render_pngs", lambda: list(e.pngs)))
    monkeypatch.setattr(cv.measure_fill, "measure", lambda path: e.fills[path])
    monkeypatch.setattr(cv, "check_text_clip", rec("check_text_clip", lambda: list(e.clip)))
    monkeypatch.setattr(cv, "check_whitespace", rec("check_whitespace", lambda: iter(e.ws)))
    monkeypatch.setattr(cv, "extract_text", rec("extract_text", "EXTRACTED TEXT"))
    monkeypatch.setattr(cv, "make_context", rec("make_context", object))
    monkeypatch.setattr(cv, "typst_can_query", lambda: e.can_query)
    monkeypatch.setattr(cv, "GATES", ())
    monkeypatch.setattr(cv, "run_gates", lambda gates, ctx: 0)
    monkeypatch.setattr(cv, "check_review_record", lambda t: list(e.record))
    monkeypatch.setattr(cv, "layout_report_line", lambda t: e.layout)

    def run(src="body\n", expected="1", fmin=None, fmax=None, **kw):
        t = e.dir / "cv.typ"
        t.write_text(src, encoding="utf-8")
        rc, footer = cv.check_cv(str(t), cv.PageTarget(expected, fmin, fmax), **kw)
        return rc, footer, e.capsys.readouterr().out
    e.run = run
    return e


@pytest.fixture(autouse=True)
def _cap(request):
    if "env" in request.fixturenames:
        request.getfixturevalue("env").capsys = request.getfixturevalue("capsys")


def test_pass_without_fill_targets_warns_and_says_how_to_rerun(env):
    rc, _footer, out = env.run()
    assert rc == 0
    (w,) = [ln for ln in out.splitlines() if ln.startswith("WARN  fill NOT checked")]
    assert w.startswith("WARN  fill NOT checked (no FILL_MIN FILL_MAX given) — rerun as scripts/verify.py ")
    assert w.endswith(' FILL_MIN FILL_MAX; the targets come from the pick_design.py report ("fill target : NN-NN%") and differ per family')
    assert "OK    pages: 1" in out
    assert "INFO  fill: p1.png: ink from 3% to 95% (target = (100 - bottom-margin%) - 0..2%)" in out
    assert "PASS  mechanical checks except fill (no FILL_MIN FILL_MAX given)" in out
    assert out.rstrip().endswith("then LOOK at the PNGs")
    assert "EXTRACTED TEXT" in out and "──── extraction" in out


def test_extraction_is_printed_before_the_verdict(env):
    _, _, out = env.run(fmin="90", fmax="99")
    assert ("──── extraction (check reading order, orphaned dates, intact skill lines) ────"
            in out.splitlines())
    assert out.index("EXTRACTED TEXT") < out.index("PASS ")


@pytest.mark.parametrize("fill,ok", [(89, False), (90, True), (95, True), (99, True), (100, False)])
def test_fill_target_bounds_are_inclusive(env, fill, ok):
    env.fills = {"p1.png": f"ink from 3% to {fill}%"}
    rc, _, out = env.run(fmin="90", fmax="99")
    assert (rc == 0) == ok
    assert ("OK    fill: p1.png: " in out) == ok
    assert ("PASS  all mechanical checks — now LOOK at the PNGs" in out) == ok
    if not ok:
        assert f"FAIL  fill: p1.png: ink from 3% to {fill}% (target 90-99%)" in out
        assert "scripts/verify.py --tune " in out and " 1 90 99" in out


def test_under_fill_above_floor_suggests_a_lowered_target(env):
    env.fills = {"p1.png": "ink from 3% to 80%"}
    rc, _, out = env.run(fmin="90", fmax="99")
    assert rc == 1
    (w,) = [ln for ln in out.splitlines() if ln.startswith("NEXT")]
    assert w.startswith("NEXT  if --tune already reported UNDER-FILLED, a fact is missing: add one, or — only ")
    assert "pass a lowered target: `scripts/verify.py " in w and " 1 80 99` (FILL_MIN = the lowest" in w
    assert w.endswith(f"not below {LOWERED_FILL_FLOOR}) and tell the user")


def test_under_fill_below_floor_says_a_fact_is_missing(env):
    env.fills = {"p1.png": f"ink from 3% to {LOWERED_FILL_FLOOR - 1}%"}
    _, _, out = env.run(fmin="90", fmax="99")
    (w,) = [ln for ln in out.splitlines() if ln.startswith("NEXT")]
    assert w.startswith(f"NEXT  fill {LOWERED_FILL_FLOOR - 1}% is below the {LOWERED_FILL_FLOOR}% floor, so a lowered target cannot pass")
    assert w.endswith("add real facts or ask the user")
    env.pages = "2"
    _, _, out = env.run(expected="2", fmin="90", fmax="99")
    assert next(ln for ln in out.splitlines() if ln.startswith("NEXT")).endswith(
        "add real facts or ask the user, or drop to fewer pages")


def test_floor_boundary_is_exclusive(env):
    env.fills = {"p1.png": f"ink from 3% to {LOWERED_FILL_FLOOR}%"}
    _, _, out = env.run(fmin="90", fmax="99")
    assert f"is below the {LOWERED_FILL_FLOOR}% floor" not in out and "NEXT  if --tune already" in out


def test_over_fill_gives_no_next_hint(env):
    env.fills = {"p1.png": "ink from 3% to 100%"}
    rc, _, out = env.run(fmin="90", fmax="99")
    assert rc == 1 and "NEXT" not in out


def test_the_lowest_page_decides_the_under_fill_hint(env):
    env.pngs = ("p1.png", "p2.png")
    env.fills = {"p1.png": f"ink from 3% to {LOWERED_FILL_FLOOR + 10}%", "p2.png": f"ink from 3% to {LOWERED_FILL_FLOOR - 10}%"}
    env.pages = "2"
    _, _, out = env.run(expected="2", fmin="90", fmax="99")
    assert f"NEXT  fill {LOWERED_FILL_FLOOR - 10}% is below the {LOWERED_FILL_FLOOR}% floor" in out


def test_fill_result_without_a_percentage_is_not_judged(env):
    env.fills = {"p1.png": "something else"}
    rc, _, out = env.run(fmin="90", fmax="99")
    assert rc == 0 and "PASS  all mechanical checks" in out and "fill:" not in out


def test_pass_line_lists_nothing_extra_when_clean(env):
    _, _, out = env.run(fmin="90", fmax="99")
    assert "PASS  all mechanical checks — now LOOK at the PNGs" in out
    assert "lowered" not in out


def test_blank_page_fails_and_skips_the_other_page_checks(env):
    env.fills = {"p1.png": "blank page"}
    rc, _, out = env.run(fmin="90", fmax="99")
    assert rc == 1 and "FAIL  fill: p1.png: blank page" in out and "PASS" not in out


def test_missing_render_fails(env):
    env.pngs = ()
    rc, _, out = env.run(fmin="90", fmax="99")
    assert rc == 1 and "FAIL  no PNG rendered — fill unmeasured" in out.splitlines()


def test_page_count_mismatch_fails_with_both_numbers(env):
    env.pages = "3"
    rc, _, out = env.run(expected="2", fmin="90", fmax="99")
    assert rc == 1
    assert "FAIL  pages: 3 (expected 2) — cut or add real content in cv.typ (or, if 2 was the wrong target" in out
    assert "OK    pages" not in out


def test_non_integer_arguments_stop_before_anything_runs(env):
    rc, footer, out = env.run(fmin="9x", fmax="99")
    assert (rc, footer) == (1, None)
    assert out.splitlines()[0] == "FAIL  fill args must be integers (got '9x') — e.g. verify.py cv.typ 1 94 96"
    assert "pages:" not in out


def test_preflight_failure_stops_with_no_footer(env):
    env.preflight_ok = False
    rc, footer, out = env.run()
    assert (rc, footer) == (1, None) and "pages:" not in out


def test_footer_is_armed_after_preflight(env):
    from vitae.core.base import FOOTER_GATE
    _rc, footer, _ = env.run(fmin="90", fmax="99")
    assert footer == FOOTER_GATE


def test_compile_failure_prints_the_error_and_stops(env):
    env.compile_ok, env.err = False, "error: boom"
    rc, footer, out = env.run(fmin="90", fmax="99")
    assert rc == 1 and footer
    assert out.splitlines()[:1] == ["FAIL  compile failed: error: boom"] and "pages:" not in out


def test_a_refusal_by_the_pdf_standard_leads_with_the_advice_line(env):
    """Same lines as the letter and academic gates: the line saying what to add first, then Typst's own error."""
    advice = real_pdf.standard_failure_advice("error: PDF/UA-1 error: missing document title\n")
    env.compile_ok, env.err = False, f"{advice}\nerror: PDF/UA-1 error: missing document title\n"
    rc, _, out = env.run(fmin="90", fmax="99")
    lines = out.splitlines()
    assert rc == 1 and lines[0] == advice and lines[1].startswith("FAIL  compile failed: error: PDF/UA-1")


def test_non_convergence_is_a_fail_with_the_reason(env):
    env.err = "warning: layout did not converge"
    rc, _, out = env.run(fmin="90", fmax="99")
    assert rc == 1
    (w,) = [ln for ln in out.splitlines() if ln.startswith("FAIL  compile")]
    assert w.startswith("FAIL  compile: Typst warns the layout did not converge, so the PDF depends on ")
    assert w.endswith("(the shipped lib converges)") and "the CV's lib.typ is an older copy (recopy" in w
    assert "WARN  compile stderr" in out


def test_compile_stderr_alone_is_a_warn(env):
    env.err = "warning: unknown font family"
    rc, _, out = env.run(fmin="90", fmax="99")
    assert rc == 0 and "WARN  compile stderr (a missing font only warns and falls back):\nwarning: unknown font family" in out
    env.err = "   \n"
    _, _, out = env.run(fmin="90", fmax="99")
    assert "compile stderr" not in out


def test_lib_findings_print_and_a_fail_one_fails(env):
    env.lib = [(Level.WARN, "careful")]
    rc, _, out = env.run(fmin="90", fmax="99")
    assert rc == 0 and "WARN  careful" in out
    env.lib = [(Level.FAIL, "lib.typ differs")]
    rc, _, out = env.run(fmin="90", fmax="99")
    assert rc == 1 and "FAIL  lib.typ differs" in out


def test_text_clip_and_whitespace_findings_fail(env):
    env.clip = ["header band cuts the text"]
    rc, _, out = env.run(fmin="90", fmax="99")
    assert rc == 1 and "FAIL  header band cuts the text" in out
    env.clip = ()
    env.ws = [(False, "gap ok")]
    rc, _, out = env.run(fmin="90", fmax="99")
    assert rc == 0 and "OK    gap ok" in out
    env.ws = [(True, "gap too big")]
    rc, _, out = env.run(fmin="90", fmax="99")
    assert rc == 1 and "FAIL  gap too big" in out


def test_clone_markers_warn_without_failing(env):
    rc, _, out = env.run(src="#let accent = rgb(\"#7D2231\")\n", fmin="90", fmax="99")
    assert rc == 0 and "WARN  template default accent (#7d2231)" in out and "clone marker #2" not in out
    rc, _, out = env.run(src="[#cat:] x\n", fmin="90", fmax="99")
    (w,) = [ln for ln in out.splitlines() if "clone marker #2" in ln]
    assert w == 'WARN  template skills block ("Category: items") — clone marker #2; use the chosen family\'s skills shape'
    assert rc == 0 and "template default accent" not in out


def test_pypdf_backend_is_flagged(env):
    env.backend = "pypdf"
    _, _, out = env.run(fmin="90", fmax="99")
    (w,) = [ln for ln in out.splitlines() if "pypdf extraction" in ln]
    assert w.startswith("WARN  pypdf extraction is indicative only (spurious spaces inside words")
    assert w.endswith("(references/ats.md)")
    env.backend = "poppler"
    _, _, out = env.run(fmin="90", fmax="99")
    assert "pypdf extraction" not in out


def test_placeholders_flag_is_refused_outside_the_templates(env):
    rc, _, out = env.run(fmin="90", fmax="99", allow_placeholders=True)
    assert rc == 1
    assert out.splitlines()[0] == cv.ALLOW_REFUSED
    assert "placeholder gate skipped" not in out


def test_gate_failures_fail_the_run(env, monkeypatch):
    monkeypatch.setattr(cv, "run_gates", lambda gates, ctx: 1)
    rc, _, out = env.run(fmin="90", fmax="99")
    assert rc == 1 and "PASS" not in out and "EXTRACTED TEXT" in out


def test_placeholder_gate_is_dropped_only_when_allowed(env, monkeypatch):
    seen = []
    monkeypatch.setattr(cv, "run_gates", lambda gates, ctx: seen.append([g.name for g in gates]) or 0)
    monkeypatch.setattr(cv, "GATES", (SimpleNamespace(name="placeholders"), SimpleNamespace(name="other")))
    env.run(fmin="90", fmax="99")
    monkeypatch.setattr(cv, "placeholders_allowed", lambda t: True)
    _, _, out = env.run(fmin="90", fmax="99", allow_placeholders=True)
    assert seen == [["placeholders", "other"], ["other"]]
    (w,) = [ln for ln in out.splitlines() if "placeholder gate skipped (--allow" in ln]
    assert w == ("WARN  placeholder gate skipped (--allow-placeholders): only for the shipped templates, "
                 "never a real CV")
    assert "PASS (placeholder gate skipped) all mechanical checks" in out and "review record skipped" not in out


def test_rebuild_skips_the_review_record(env):
    env.record = [(Level.FAIL, "no review.md")]
    rc, _, out = env.run(fmin="90", fmax="99", rebuild=True)
    assert rc == 0 and "PASS (review record skipped: --rebuild, candidate rebuild) " in out
    assert "no review.md" not in out


def test_missing_review_record_blocks_delivery(env):
    env.record = [(Level.FAIL, "no review.md")]
    rc, footer, out = env.run(fmin="90", fmax="99")
    assert (rc, footer) == (1, None)
    assert "mechanical gates: PASS (fill 95%) — now LOOK at the PNGs" in out
    assert "FAIL  no review.md" in out
    assert out.rstrip().endswith("FAIL  not deliverable: the review record is missing or incomplete (step 7)")


def test_missing_review_record_without_fill_targets(env):
    env.record = [(Level.FAIL, "no review.md")]
    _, _, out = env.run()
    assert "mechanical gates: PASS except fill (no FILL_MIN FILL_MAX given) — now LOOK" in out


def test_record_info_and_layout_line_follow_the_pass(env):
    env.record = [(Level.INFO, "review: 3 findings")]
    env.layout = "layout: 2 pages"
    _, _, out = env.run(fmin="90", fmax="99")
    assert out.index("INFO  review: 3 findings") < out.index("PASS ") < out.index("layout: 2 pages")


def test_record_failure_repeats_the_leading_and_size_warns(env):
    env.record = [(Level.FAIL, "no review.md")]
    src = "#set par(leading: 1.4em)\n#set text(size: 12pt)\nbody\n"
    _, _, out = env.run(src=src, fmin="90", fmax="99")
    assert out.count("reads as DOUBLE-SPACED") == 2 and out.count("body text 12pt") == 2


def test_leading_and_size_warns_print_up_front_and_again_after_pass(env):
    src = "#set par(leading: 1.4em)\n#set text(size: 12pt)\nbody\n"
    rc, _, out = env.run(src=src, fmin="90", fmax="99")
    assert rc == 0
    assert out.count("reads as DOUBLE-SPACED") == 2 and out.count("body text 12pt") == 2
    assert out.rindex("body text 12pt") > out.index("PASS ")


def test_clean_pass_prints_no_warns_after_the_verdict(env):
    _, _, out = env.run(fmin="90", fmax="99")
    assert out.rstrip().endswith("LOOK at the PNGs") and "WARN" not in out


# fill target drawn by the `// vitae:` header (no family known)

DRAWN = "// vitae: pages=1 fill=94-96\n"


def test_drawn_target_is_used_when_none_given(env):
    env.fills = {"p1.png": "ink from 3% to 95%"}
    rc, _, out = env.run(src=DRAWN)
    assert rc == 0
    assert "INFO  fill target 94-96% drawn for this CV (family table / cv.typ header)" in out
    assert "OK    fill: p1.png" in out and "fill NOT checked" not in out


def test_given_target_equal_to_drawn_is_silent(env):
    _, _, out = env.run(src=DRAWN, fmin="94", fmax="96")
    assert "drawn for this CV" not in out and "lowered" not in out


def test_raising_the_target_above_drawn_is_silent(env):
    env.fills = {"p1.png": "ink from 3% to 97%"}
    rc, _, out = env.run(src=DRAWN, fmin="96", fmax="98")
    assert rc == 0 and "lowered" not in out


def test_lowered_target_warns_and_is_carried_to_the_pass_line(env):
    env.fills = {"p1.png": "ink from 3% to 92%"}
    rc, _, out = env.run(src=DRAWN, fmin="90", fmax="96")
    assert rc == 0
    assert out.count("WARN  fill target lowered below drawn target 94-96 — allowed ONLY") == 2
    assert "PASS (fill target lowered: 94-96 → 90-96) all mechanical checks — now LOOK at the PNGs" in out
    assert out.rindex("fill target lowered below") > out.index("PASS ")


def test_lowered_target_one_below_drawn_still_warns(env):
    _, _, out = env.run(src=DRAWN, fmin="93", fmax="96")
    assert "fill target lowered below drawn target" in out


def test_target_below_the_floor_is_a_fail(env):
    env.fills = {"p1.png": f"ink from 3% to {LOWERED_FILL_FLOOR + 10}%"}      # inside the target: only the floor decides
    lo = LOWERED_FILL_FLOOR - 1
    rc, _, out = env.run(src=DRAWN, fmin=str(lo), fmax="96")
    assert rc == 1
    assert f"FAIL  fill target lowered to {lo}-96% is below the lowered-target floor ({LOWERED_FILL_FLOOR}%, drawn target 94-96)" in out


def test_target_exactly_at_the_floor_only_warns(env):
    env.fills = {"p1.png": f"ink from 3% to {LOWERED_FILL_FLOOR + 10}%"}
    rc, _, out = env.run(src=DRAWN, fmin=str(LOWERED_FILL_FLOOR), fmax="96")
    assert rc == 0 and "lowered-target floor" not in out
    assert "WARN  fill target lowered below drawn target 94-96 — allowed ONLY" in out


# ---------- check_cv: what is passed to the collaborators, and multi-page behaviour ----------

def _bound_all(env, name, real):
    """The arguments each recorded call of the faked collaborator passed, by the REAL function's parameter names."""
    sig = inspect.signature(real)
    return [dict(sig.bind(*a, **k).arguments) for a, k in env.calls[name]]


def _bound(env, name, real):
    (args,) = _bound_all(env, name, real)
    return args


def test_backend_facts_and_query_flag_reach_the_collaborators(env):
    env.backend = "pypdf"
    env.run(fmin="90", fmax="99", facts="facts.md")
    assert _bound(env, "count_pages", real_pdf.count_pages)["backend"] == "pypdf"
    assert _bound(env, "extract_text", real_pdf.extract_text)["backend"] == "pypdf"
    ctx = _bound(env, "make_context", real_gates.make_context)
    assert ctx["backend"] == "pypdf" and ctx["facts"] == "facts.md"
    assert ctx["src"] == "body\n"                                  # the source text
    assert ctx["txt"] == "EXTRACTED TEXT"


@pytest.mark.parametrize("can_query", [False, True])
def test_gates_may_query_when_typst_can(env, can_query):
    env.can_query = can_query
    env.run(fmin="90", fmax="99")
    assert _bound(env, "make_context", real_gates.make_context)["can_query"] is can_query


def test_whitespace_gate_gets_boxes_family_and_degraded_flag(env):
    env.boxes = [[(("b1",), "w")]]
    env.run(src="// FAMILY: swiss-grid\nbody\n", fmin="90", fmax="99")
    ws = _bound(env, "check_whitespace", real_layout.check_whitespace)
    assert ws["boxes"] == [("b1",)] and ws["family"] == "swiss-grid" and ws["degraded"] is False
    assert _bound(env, "check_text_clip", real_layout.check_text_clip)["boxes"] == [(("b1",), "w")]


def test_without_word_boxes_the_dependent_gates_degrade_with_one_notice(env, monkeypatch):
    env.boxes = None
    env.pngs = ("p1.png", "p2.png")
    env.fills = {"p1.png": "ink from 3% to 95%", "p2.png": "ink from 3% to 95%"}
    env.pages = "2"
    monkeypatch.setattr(cv, "boxes_unavailable", lambda pdf: f"no word boxes for {pdf}")
    _, _, out = env.run(expected="2", fmin="90", fmax="99")
    lines = out.splitlines()
    notice = f"WARN  text-clip gate skipped: no word boxes for {env.dir}/cv.pdf"
    assert lines.count(notice) == 1
    assert lines.index(notice) < next(i for i, ln in enumerate(lines) if ln.startswith("OK    fill: p2.png"))
    for ws in _bound_all(env, "check_whitespace", real_layout.check_whitespace):
        assert ws["boxes"] is None and ws["degraded"] is True
    assert [c["boxes"] for c in _bound_all(env, "check_text_clip", real_layout.check_text_clip)] == [None, None]


def test_each_page_gets_its_own_boxes(env):
    env.boxes = [[(("a",), "x")], [(("b",), "y")]]
    env.pngs = ("p1.png", "p2.png")
    env.fills = {"p1.png": "ink from 3% to 95%", "p2.png": "ink from 3% to 95%"}
    env.pages = "2"
    env.run(expected="2", fmin="90", fmax="99")
    assert [c["boxes"] for c in _bound_all(env, "check_whitespace", real_layout.check_whitespace)] == [[("a",)], [("b",)]]
    assert [c["boxes"] for c in _bound_all(env, "check_text_clip", real_layout.check_text_clip)] == [[(("a",), "x")], [(("b",), "y")]]


def test_more_pages_than_boxes_does_not_crash(env):
    env.boxes = [[(("a",), "x")]]
    env.pngs = ("p1.png", "p2.png")
    env.fills = {"p1.png": "ink from 3% to 95%", "p2.png": "ink from 3% to 95%"}
    env.pages = "2"
    rc, _, _ = env.run(expected="2", fmin="90", fmax="99")
    assert rc == 0 and _bound_all(env, "check_whitespace", real_layout.check_whitespace)[1]["boxes"] is None


def test_a_blank_first_page_does_not_hide_the_second_page(env):
    env.pngs = ("p1.png", "p2.png")
    env.fills = {"p1.png": "blank page", "p2.png": "ink from 3% to 50%"}
    env.pages = "2"
    _, _, out = env.run(expected="2", fmin="90", fmax="99")
    assert "FAIL  fill: p1.png: blank page" in out and "FAIL  fill: p2.png: ink from 3% to 50%" in out
    assert len(env.calls["check_whitespace"]) == 1                    # the blank page is skipped, not the loop


def test_an_unparsed_first_page_does_not_hide_the_second_page(env):
    env.pngs = ("p1.png", "p2.png")
    env.fills = {"p1.png": "unreadable", "p2.png": "ink from 3% to 50%"}
    env.pages = "2"
    _, _, out = env.run(expected="2", fmin="90", fmax="99")
    assert "FAIL  fill: p2.png" in out


def test_only_one_fill_bound_means_fill_is_not_checked(env):
    for fmin, fmax in (("90", None), (None, "99")):
        rc, _, out = env.run(fmin=fmin, fmax=fmax)
        assert rc == 0
        assert "WARN  fill NOT checked" in out and "INFO  fill: p1.png" in out
        assert "PASS  mechanical checks except fill" in out


def test_one_bound_given_still_takes_the_drawn_target(env):
    env.fills = {"p1.png": "ink from 3% to 95%"}
    for fmin, fmax in (("94", None), (None, "96")):
        rc, _, out = env.run(src=DRAWN, fmin=fmin, fmax=fmax)
        assert rc == 0 and "INFO  fill target 94-96% drawn for this CV" in out


def test_a_later_lib_ok_does_not_erase_an_earlier_lib_fail(env):
    env.lib = [(Level.FAIL, "lib.typ differs"), (Level.INFO, "fine")]
    rc, _, _ = env.run(fmin="90", fmax="99")
    assert rc == 1


def test_lowered_floor_fail_alone_fails_the_run(env):
    env.fills = {"p1.png": f"ink from 3% to {LOWERED_FILL_FLOOR + 10}%"}
    rc, _, out = env.run(src=DRAWN, fmin=str(LOWERED_FILL_FLOOR - 1), fmax="96")
    assert rc == 1 and "PASS" not in out


def test_record_failure_names_every_fill_and_the_lowered_target(env):
    env.record = [(Level.FAIL, "no review.md")]
    env.pngs = ("p1.png", "p2.png")
    env.fills = {"p1.png": "ink from 3% to 92%", "p2.png": "ink from 3% to 95%"}
    env.pages = "2"
    src = "// vitae: pages=2 fill=94-96\n"
    _, _, out = env.run(src=src, expected="2", fmin="90", fmax="96")
    assert ("mechanical gates: PASS (fill 92/95%) (fill target lowered: 94-96 → 90-96) — "
            "now LOOK at the PNGs (Visual pass:), then step 7") in out.splitlines()
    assert out.count("fill target lowered below drawn target 94-96 — allowed ONLY") == 2


def test_record_failure_with_no_measurable_fill_names_none(env):
    env.record = [(Level.FAIL, "no review.md")]
    env.fills = {"p1.png": "unreadable"}
    _, _, out = env.run(fmin="90", fmax="99")
    assert "mechanical gates: PASS — now LOOK at the PNGs (Visual pass:), then step 7" in out.splitlines()


def test_skip_notes_are_joined_in_the_pass_line(env, monkeypatch):
    monkeypatch.setattr(cv, "placeholders_allowed", lambda t: True)
    env.fills = {"p1.png": "ink from 3% to 92%"}
    _, _, out = env.run(src=DRAWN, fmin="90", fmax="96", allow_placeholders=True, rebuild=True)
    assert ("PASS (fill target lowered: 94-96 → 90-96; placeholder gate skipped; review record skipped: "
            "--rebuild, candidate rebuild) all mechanical checks — now LOOK at the PNGs") in out.splitlines()
    env.fills = {"p1.png": "ink from 3% to 95%"}
    _, _, out = env.run(fmin="90", fmax="99", allow_placeholders=True, rebuild=True)
    assert ("PASS (placeholder gate skipped; review record skipped: --rebuild, candidate rebuild) "
            "all mechanical checks — now LOOK at the PNGs") in out.splitlines()


def test_under_fill_hint_for_a_two_page_cv_uses_that_page_count(env):
    env.fills = {"p1.png": "ink from 3% to 80%"}
    env.pages = "2"
    _, _, out = env.run(expected="2", fmin="90", fmax="99")
    assert "scripts/verify.py --tune " in out and " 2 90 99`" in out
    assert " 2 80 99`" in out


def test_leading_ratio_depends_on_the_page_count(env, rhythm):
    lead, lsp = FAMILY_2P[0] * 1.05, FAMILY_2P[1]
    src = f"// FAMILY: color-band\n#set par(leading: {lead}em)\n#set list(spacing: {lsp}em)\nbody\n"
    _, _, out = env.run(src=src, expected="2", fmin="90", fmax="99")
    assert "list rhythm no longer matches" not in out
    _, _, out = env.run(src=src, expected="1", fmin="90", fmax="99")
    assert "WARN  the list rhythm no longer matches" in out
    _, _, out = env.run(src=src, expected="x", fmin="90", fmax="99")          # not a page count: the 1-page rhythm
    assert "WARN  the list rhythm no longer matches" in out


# ---------- the 4 KiB window ends exactly at byte 4096 ----------

@pytest.mark.parametrize("fn,marker", [(cv.is_academic, cv.ACADEMIC_MARKER), (cv.is_letter, cv.LETTER_MARKER)])
def test_marker_ending_exactly_at_the_window_edge(tmp_path, fn, marker):
    p = tmp_path / "a.typ"
    p.write_text("x" * (4096 - len(marker)) + marker, encoding="utf-8")
    assert fn(str(p))
    p.write_text("x" * (4097 - len(marker)) + marker, encoding="utf-8")
    assert not fn(str(p))


def test_header_ending_exactly_at_the_window_edge_opts_in(tmp_path):
    head = "// vitae: pages=1"
    p = tmp_path / "guide.typ"
    p.write_text("\n" * (4096 - len(head)) + head, encoding="utf-8")
    assert cv.is_gated(str(p))
    p.write_text("\n" * (4097 - len(head)) + head, encoding="utf-8")
    assert not cv.is_gated(str(p))


def test_check_all_reads_only_the_first_4096_bytes_for_the_header(tmp_path, sweep):
    head = "// vitae: pages=2"
    _w(tmp_path, "cv.typ", "\n" * (4096 - len(head) - 1) + head + "\n")        # complete header just inside
    _w(tmp_path, "cv-2page.typ", "\n" * (4097 - len(head) - 1) + head + "5\n")  # cut right after `pages=`
    cv.check_all(str(tmp_path))
    by_file = {c[2].rsplit("/", 1)[-1]: c[3:] for c in sweep[0]}
    assert by_file == {"cv.typ": ["2"], "cv-2page.typ": ["2"]}


def test_unreadable_file_in_the_sweep_is_reported_and_fails(tmp_path, capsys, sweep):
    _w(tmp_path, "cv.typ", "// vitae: pages=1\n")
    (tmp_path / "bad.typ").write_bytes(b"\xff\xfe\x00\xc3(")          # not UTF-8
    assert cv.check_all(str(tmp_path)) == 1
    out = capsys.readouterr().out
    assert f"=== {tmp_path}/bad.typ\nFAIL  unreadable" in out
    assert [c[2].rsplit("/", 1)[-1] for c in sweep[0]] == ["cv.typ"]       # the rest is still checked
    assert out.rstrip().endswith("FAIL — see above")


def test_unreadable_companion_is_skipped_not_gated(tmp_path, capsys, sweep):
    _w(tmp_path, "cv.typ")
    (tmp_path / "guide.typ").write_bytes(b"\xff\xfe\xc3(")
    assert cv.check_all(str(tmp_path)) == 0
    assert "SKIP  " in capsys.readouterr().out


def test_check_all_opens_each_file_once(tmp_path, sweep, monkeypatch):
    import builtins
    _w(tmp_path, "cv.typ", "// vitae: pages=1\n")
    _w(tmp_path, "guide.typ", "// vitae: pages=1\n")
    _w(tmp_path, "plain.typ")
    opened: list[str] = []
    real_open = builtins.open

    def spy(file, *a, **kw):
        if str(file).endswith(".typ"):
            opened.append(Path(str(file)).name)
        return real_open(file, *a, **kw)

    monkeypatch.setattr(builtins, "open", spy)
    assert cv.check_all(str(tmp_path)) == 0
    assert sorted(opened) == ["cv.typ", "guide.typ", "plain.typ"]


# ---------- _leading_warn: silent cases and the printed numbers ----------

def _lead_cv(tmp_path, body, banner=""):
    p = tmp_path / "cv.typ"
    p.write_text(banner + body, encoding="utf-8")
    return str(p)


def test_leading_warn_is_silent_for_a_missing_file_or_no_leading(tmp_path):
    assert _leading_warn(str(tmp_path / "missing.typ")) == ""
    assert _leading_warn(_lead_cv(tmp_path, "#set list(spacing: 0.5em)\nbody\n")) == ""


def test_leading_warn_ignores_a_zero_or_missing_list_spacing(tmp_path):
    assert _leading_warn(_lead_cv(tmp_path, "#set par(leading: 0.8em)\n#set list(spacing: 0em)\nbody\n")) == ""
    assert _leading_warn(_lead_cv(tmp_path, "#set par(leading: 0.8em)\nbody\n")) == ""


def test_leading_warn_without_a_known_family_uses_the_absolute_ratio(tmp_path):
    from vitae.core.base import LEADING_ABS_RATIO_WARN
    lsp = 0.4
    just_over = lsp * LEADING_ABS_RATIO_WARN + 0.01
    just_under = lsp * LEADING_ABS_RATIO_WARN - 0.01
    assert LEADING_WARN > just_over                                 # the absolute leading check stays out of the way
    assert _leading_warn(_lead_cv(tmp_path, f"#set par(leading: {just_under!r}em)\n#set list(spacing: {lsp}em)\nb\n")) == ""
    out = _leading_warn(_lead_cv(tmp_path, f"#set par(leading: {just_over!r}em)\n#set list(spacing: {lsp}em)\nb\n"))
    assert out.startswith(f"WARN  leading {just_over:.3f}em vs bullet spacing {lsp:.3f}em (ratio {just_over / lsp:.2f}, warns above "
                          f"{LEADING_ABS_RATIO_WARN:.2f})")


# a controlled family: (leading, list spacing) in em for a 1-page and a 2-page CV, whatever the shipped templates say
FAMILY_1P = (0.6, 0.44)
FAMILY_2P = (0.68, 0.42)


@pytest.fixture
def rhythm(monkeypatch):
    monkeypatch.setattr(cv, "_family_default", lambda family, pages: FAMILY_2P if pages >= 2 else FAMILY_1P)
    return FAMILY_1P


def test_leading_warn_family_message_prints_the_family_ratio_and_both_reference_values(tmp_path, rhythm):
    ref_l, ref_s = rhythm
    lsp = ref_s
    lead = ref_l * (LEADING_FAMILY_RATIO_WARN + 0.1)
    assert lead <= LEADING_WARN
    out = _leading_warn(_lead_cv(tmp_path, f"#set par(leading: {lead!r}em)\n#set list(spacing: {lsp!r}em)\nb\n",
                                 "// FAMILY: color-band\n"))
    rel = (lead / lsp) / (ref_l / ref_s)
    assert f"is {rel:.2f}x the ratio of the color-band template ({ref_l:.3f}em / {ref_s:.3f}em)" in out
    assert f"leading {lead:.3f}em vs bullet spacing {lsp:.3f}em" in out


def test_leading_just_above_the_absolute_limit_warns_and_at_it_does_not(tmp_path):
    body = "#set par(leading: {}em)\nbody\n"
    assert _leading_warn(_lead_cv(tmp_path, body.format(LEADING_WARN))) == ""
    assert _leading_warn(_lead_cv(tmp_path, body.format(LEADING_WARN + 0.01))).startswith("WARN  leading")


def test_pdf_sits_beside_the_typ_and_the_hints_name_the_file(env):
    env.fills = {"p1.png": "ink from 3% to 80%"}
    _, _, out = env.run(fmin="90", fmax="99")
    typ = f"{env.dir}/cv.typ"
    assert _bound(env, "count_pages", real_pdf.count_pages)["pdf"] == f"{env.dir}/cv.pdf"
    assert f"run `scripts/verify.py --tune {typ} 1 90 99`" in out
    assert f"`scripts/verify.py {typ} 1 80 99`" in out
    assert ("FILL_MAX; " not in out) and out.count(typ) >= 2
    env.fills = {"p1.png": "ink from 3% to 95%"}
    _, _, out = env.run()
    assert f"rerun as scripts/verify.py {typ} 1 FILL_MIN FILL_MAX; the targets" in out


def test_hints_carry_the_placeholders_flag_when_it_is_in_force(env, monkeypatch):
    monkeypatch.setattr(cv, "placeholders_allowed", lambda t: True)
    env.fills = {"p1.png": "ink from 3% to 80%"}
    _, _, out = env.run(fmin="90", fmax="99", allow_placeholders=True)
    assert " 1 90 99 --allow-placeholders` " in out and " 1 80 99 --allow-placeholders` " in out
    _, _, out = env.run(allow_placeholders=True)
    assert "FILL_MIN FILL_MAX --allow-placeholders; the targets" in out
    _, _, out = env.run(fmin="90", fmax="99")
    assert "--allow-placeholders" not in out.replace("(--allow-placeholders)", "")


def test_record_failure_with_one_fill_bound_says_fill_was_not_checked(env):
    env.record = [(Level.FAIL, "no review.md")]
    _, _, out = env.run(fmin="90")
    assert ("mechanical gates: PASS except fill (no FILL_MIN FILL_MAX given) — now LOOK at the PNGs "
            "(Visual pass:), then step 7") in out.splitlines()


def test_tune_hint_ends_with_the_remedy(env):
    env.fills = {"p1.png": "ink from 3% to 100%"}
    _, _, out = env.run(fmin="90", fmax="99")
    (w,) = [ln for ln in out.splitlines() if ln.startswith("FAIL  fill:")]
    assert w.endswith("(adjusts leading), or add/cut real content")
    assert " — run `scripts/verify.py --tune " in w


# ---------- mutation-driven additions: lib chain resolution, tolerance edges, messages ----------

def test_a_lib_reached_through_a_subfolder_family_file_resolves_beside_that_file(tmp_path, skill):
    t = _cv(tmp_path, '#import "sub/family.typ": *\n')
    _w(tmp_path / "work", "sub/family.typ", '#import "lib.typ": *\n')            # relative to family.typ, not to the CV
    _w(tmp_path / "work", "sub/lib.typ", LIB_SRC)
    assert cv.check_lib_integrity(t, skill) == []
    (tmp_path / "work" / "sub" / "lib.typ").write_text("#let edited = 1\n", encoding="utf-8")
    ((lvl, msg),) = cv.check_lib_integrity(t, skill)
    assert lvl == Level.FAIL and msg.startswith("lib.typ differs from the skill's")


def test_rooted_import_keeps_a_leading_x_in_the_folder_name(tmp_path, skill):
    t = _cv(tmp_path, '#import "/Xfam/family.typ": *\n')                         # "/" = the CV's own folder
    _w(tmp_path / "work", "Xfam/family.typ", '#import "/lib.typ": *\n')
    _w(tmp_path / "work", "lib.typ", LIB_SRC)
    assert cv.check_lib_integrity(t, skill) == []


def test_a_non_utf8_byte_in_an_imported_file_does_not_stop_the_search(tmp_path, skill):
    t = _cv(tmp_path, '#import "family.typ": *\n')
    (tmp_path / "work" / "family.typ").write_bytes(b'// caf\xe9 \xff\n#import "lib.typ": *\n')
    _w(tmp_path / "work", "lib.typ", LIB_SRC)
    assert cv.check_lib_integrity(t, skill) == []
    (tmp_path / "work" / "lib.typ").unlink()
    ((lvl, msg),) = cv.check_lib_integrity(t, skill)
    assert lvl == Level.FAIL and "lib.typ is imported but missing" in msg


def test_leading_warn_default_page_count_is_one(tmp_path, rhythm):
    # the 1- and 2-page rhythms differ: this ratio is loose against the 1-page one only
    lead, lsp = FAMILY_2P[0] * 1.05, FAMILY_2P[1]
    assert lead <= LEADING_WARN
    p = _lead_cv(tmp_path, f"#set par(leading: {lead}em)\n#set list(spacing: {lsp}em)\nb\n", "// FAMILY: color-band\n")
    out = _leading_warn(p)
    assert out.startswith("WARN  the list rhythm no longer matches") and "color-band template (0.600em / 0.440em)" in out
    assert _leading_warn(p, 1) == out
    assert _leading_warn(p, 2) == ""


def test_leading_warn_family_ratio_exactly_at_the_limit_is_silent(tmp_path, rhythm):
    ref_l, ref_s = rhythm
    lead = ref_l * LEADING_FAMILY_RATIO_WARN
    assert lead <= LEADING_WARN
    body = f"#set par(leading: {lead!r}em)\n#set list(spacing: {ref_s!r}em)\nb\n"
    assert _leading_warn(_lead_cv(tmp_path, body, "// FAMILY: color-band\n")) == ""
    body = f"#set par(leading: {lead + 0.01!r}em)\n#set list(spacing: {ref_s!r}em)\nb\n"
    assert _leading_warn(_lead_cv(tmp_path, body, "// FAMILY: color-band\n")).startswith("WARN  the list rhythm")


def test_absolute_ratio_exactly_at_the_limit_is_silent(tmp_path):
    from vitae.core.base import LEADING_ABS_RATIO_WARN
    lsp = 0.5
    lead = lsp * LEADING_ABS_RATIO_WARN
    assert lead <= LEADING_WARN
    assert _leading_warn(_lead_cv(tmp_path, f"#set par(leading: {lead!r}em)\n#set list(spacing: {lsp}em)\nb\n")) == ""


def test_the_float_tolerance_is_part_of_each_limit(tmp_path, monkeypatch):
    from vitae.core.base import LEADING_ABS_RATIO_WARN
    from vitae.core.base import LEADING_FAMILY_RATIO_WARN as FAM
    eps = 1e-9
    # a value written exactly one tolerance above a limit is still "at" it: no WARN
    assert _leading_warn(_lead_cv(tmp_path, f"#set par(leading: {LEADING_WARN + eps!r}em)\nb\n")) == ""
    lsp = 0.5
    ratio = (LEADING_ABS_RATIO_WARN + eps) * lsp
    assert _leading_warn(_lead_cv(tmp_path, f"#set par(leading: {ratio!r}em)\n#set list(spacing: {lsp}em)\nb\n")) == ""
    monkeypatch.setattr(cv, "_family_default", lambda family, pages: (1.0, 1.0))
    lead = (FAM + eps) * lsp
    body = f"#set par(leading: {lead!r}em)\n#set list(spacing: {lsp}em)\nb\n"
    assert _leading_warn(_lead_cv(tmp_path, body, "// FAMILY: color-band\n")) == ""
    assert cv._body_size_warn(_size_cv(tmp_path, repr(cv.BODY_SIZE_WARN + eps))) == ""


def test_a_bad_fill_max_alone_stops_the_run(env):
    rc, footer, out = env.run(fmin="90", fmax="9x")
    assert (rc, footer) == (1, None)
    assert out.splitlines()[0] == "FAIL  fill args must be integers (got '9x') — e.g. verify.py cv.typ 1 94 96"


def test_header_disagreement_warning_is_printed(env):
    env.fills = {"p1.png": "ink from 3% to 95%"}
    _, _, out = env.run(src="// vitae: pages=1 fill=10-20\n// FAMILY: color-band\n")
    assert "WARN  cv.typ header disagrees with family color-band: 10-20; the drawn fill target is " in out


def test_lowering_below_the_drawn_minimum_but_above_the_floor_only_checks_against_the_minimum(env):
    drawn_lo = LOWERED_FILL_FLOOR - 10                                # a drawn target that starts below the floor
    src = f"// vitae: pages=1 fill={drawn_lo}-80\n"
    env.fills = {"p1.png": f"ink from 3% to {LOWERED_FILL_FLOOR + 10}%"}
    rc, _, out = env.run(src=src, fmin=str(drawn_lo + 5), fmax="80")
    assert rc == 0 and "lowered-target floor" not in out
    assert "WARN  fill target lowered below drawn target" not in out      # above the drawn minimum: raised, not lowered
    rc, _, out = env.run(src=src, fmin=str(drawn_lo - 1), fmax="80")
    assert rc == 1 and (f"FAIL  fill target lowered to {drawn_lo - 1}-80% is below the lowered-target floor "
                        f"({LOWERED_FILL_FLOOR}%, drawn target {drawn_lo}-80)") in out


def test_non_convergence_message_gives_the_whole_remedy(env):
    env.err = "warning: layout did not converge"
    _, _, out = env.run(fmin="90", fmax="99")
    (w,) = [ln for ln in out.splitlines() if ln.startswith("FAIL  compile")]
    assert w == ("FAIL  compile: Typst warns the layout did not converge, so the PDF depends on which iteration it "
                 "stopped at — either the CV's lib.typ is an older copy (recopy the skill's lib.typ next to it) or a "
                 "construct in cv.typ reads its own layout (context / query / locate / measure) and changes it; "
                 "remove that construct (the shipped lib converges)")


def test_accent_clone_marker_line_is_a_warn_with_the_remedy(env):
    _, _, out = env.run(src='#let accent = rgb("#7d2231")\n', fmin="90", fmax="99")
    (w,) = [ln for ln in out.splitlines() if "template default accent" in ln]
    assert w == ("WARN  template default accent (#7d2231) — run scripts/pick_design.py and apply the family it draws "
                 "(references/design/families/<family>.md)")

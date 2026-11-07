"""The per-CV gate: header parsing, file classification, check_all, lib integrity, the new-gate runner and _check_cv.

Moved out of verify.py unchanged, re-exported there under the same names. No `import verify`.
"""
from __future__ import annotations

import glob
import hashlib
import os
import re
import shlex
import subprocess
import sys
import tempfile
from typing import NoReturn

import measure_fill
from verify_base import _FOOTER_GATE, LEADING_WARN, LOWERED_FILL_FLOOR, STATE, DetailRow, HiddenStat
from verify_env import preflight, typst_can_query
from verify_groups import ENTRY_MARKS, _typst_query, check_date_adjacency, check_duplicate_names, check_group_proximity
from verify_layout import check_font_fallback, check_text_clip, check_whitespace
from verify_level import Finding, Level
from verify_pdf import (
    _boxes_unavailable,
    compile_pdf,
    count_pages,
    ensure_icons,
    extract_text,
    family_from_path,
    render_pngs,
    word_boxes,
)
from verify_source import _drawn_fill, _fill_args_ok, check_forced_linebreak, check_literal_tilde, check_no_split
from verify_text import check_bullet_chars, check_facts_coverage, check_hidden_text
from verify_typst import _doc_body_size, _doc_par_list, _strip_typst_comments


def run_hidden_gate(pdf: str) -> int:
    """Print the hidden-text gate's lines; return 1 if any FAIL."""
    det: list[HiddenStat] = []
    fail = 0
    msgs = check_hidden_text(pdf, detail=det)
    for lvl, msg in msgs:
        print(f"{lvl:<5} {msg}")
        fail |= lvl == Level.FAIL
    if det and not msgs:
        print(f"OK    hidden text: {len(det)} words, each visibly inked (weakest contrast "
              f"{min(d[4] for d in det if d[4] is not None):.1f}:1, smallest box {min(d[3] for d in det):.1f}pt)")
    return fail


def run_new_gates(typ: str, pdf: str, txt: str, src: str, root: str | None = None,
                  detail: list[DetailRow] | None = None) -> int:
    """Print the gates that need `typst query` and word positions (hidden text, font fallback,
    group proximity, date adjacency, forced breaks and `~`, duplicate names); return 1 if any
    FAIL. Shared by a normal run and `--gates`, so the two cannot drift apart."""
    fail = run_hidden_gate(pdf)
    for lvl, msg in check_font_fallback(typ, pdf, root=root):
        print(f"{lvl:<5} {msg}")
        fail |= lvl == Level.FAIL
    for lvl, msg in check_group_proximity(typ, pdf, root=root, detail=detail):
        print(f"{lvl:<5} {msg}")
        fail |= lvl == Level.FAIL
    marks = _typst_query(typ, ENTRY_MARKS, root)
    heads = None if marks is None else [m for m in marks if m.get("kind") in ("entry", "skill")]
    if heads is not None and not any(h.get("kind") == "entry" for h in heads):
        print("WARN  date adjacency not measured: no lib entry()/srow() heads")
    dwarn: list[str] = []
    dst: dict[str, int] = {}
    for msg in check_date_adjacency(typ, pdf, marks=marks or [], warns=dwarn, stats=dst):
        print("FAIL  date adjacency: " + msg)
        fail = 1
    if marks is not None:
        _n = dst.get("measured", 0)
        print(f"INFO  date adjacency: {_n} lib entr{'y' if _n == 1 else 'ies'} measured, "
              f"{dst.get('undated', 0)} undated, {dst.get('unmeasured', 0)} not measured "
              "(a dated entry not built with lib entry() is not counted)")
    if dwarn:
        print(f"WARN  date adjacency not measured: {len(dwarn)} entr{'y' if len(dwarn) == 1 else 'ies'} "
              f"({'; '.join(dwarn[:3])})")
    if marks is None:
        print("WARN  date adjacency not measured: typst query unavailable")
    for msg in check_forced_linebreak(src) + check_literal_tilde(src):
        print("FAIL  " + msg)
        fail = 1
    secs = _typst_query(typ, "<vitae-sec>", root)
    if not secs:   # no <vitae-sec> marks (a CV that never wrapped `section` in wd-section(), or no query): read the #section("...") calls instead
        secs = [{"text": t} for t in re.findall(r'#section\(\s*"((?:[^"\\]|\\.)*)"', src)]
    for msg in check_duplicate_names(secs, heads):
        print("FAIL  duplicate name: " + msg)
        fail = 1
    return fail


# ---------- main gate ----------

HEADER_RE = re.compile(r"^//\s*vitae:\s*pages=(\d+)(?:\s+fill=(\d+)-(\d+))?",
                       re.M)


def pages_from_name(typ: str) -> str:
    """The page count a headerless deliverable declares in its own file name."""
    return "2" if re.search(r"[-_]2\s*p(?:ages?)?(?![a-z])",
                            os.path.basename(typ), re.I) else "1"


# Whole-word stems of non-CV companion deliverables (step 7 application guide, cover letter, readme)
# that `verify.py --all` skips when they carry no `// vitae:` header (step 6).
NON_CV_RE = re.compile(
    r"(?<![^\W\d_])(?:guide|lettre|letter|cover|lisez-moi|readme)(?![^\W\d_])",
    re.I)


def is_gated(typ: str) -> bool:
    """--all's rule: gate every .typ except known non-CV deliverables (guide,
    letter, cover, lisez-moi, readme by name); a `// vitae:` header opts in."""
    if not NON_CV_RE.search(os.path.basename(typ)):
        return True
    try:
        with open(typ, encoding="utf-8") as fh:
            return bool(HEADER_RE.search(fh.read(4096)))
    except OSError:
        return False


# Both markers (and HEADER_RE in is_gated/check_all) are looked for in the first 4096 bytes:
# they sit on line 1 (or in the opening comment block) so reading 4 KiB avoids loading large files.
ACADEMIC_MARKER = "// vitae-academic:"
LETTER_MARKER = "// vitae letter template"


def is_academic(path: str) -> bool:
    """True for an academic CV, which this gate must NOT judge.

    An academic CV is a different genre: the atom is the ENTRY, not the
    section, there is no fill target at all, and its length is whatever the
    record is — 13 pages is ordinary. This gate is calibrated on one- and
    two-page industry resumes, and `check_all` guesses a headerless file's
    page count from its NAME (defaulting to 1), so a sweep would fail an
    academic CV for being itself. It carries its own gate:
    `scripts/verify_academic.py`. The marker is a line-1 comment the academic
    template emits (templates/academic/cv.typ).
    """
    try:
        with open(path, encoding="utf-8") as fh:
            return ACADEMIC_MARKER in fh.read(4096)
    except OSError:
        return False


def is_letter(path: str) -> bool:
    """True for a cover letter, which this gate must NOT judge either.

    A letter is prose with a letterhead, not a sectioned resume: it has ONE
    rule, by design (templates/letter.typ: « one thin rule in the CV's accent
    colour »), so the section-device quorum — which asks for a boundary
    SYSTEM, two devices minimum — is asking a letter for sections it does not
    have. It carries its own gate, `scripts/verify_letter.py`.

    It only surfaced on 2026-09-13, when the furniture/ink dedupe was moved
    into one coordinate frame: until then the letterhead rule was counted
    TWICE, once by each detector, and the letter cleared a quorum of 2 on a
    single device. The letter was never right; the double count hid it.

    The marker is the template's own line 1 — nothing new to emit, and it
    travels with a delivered copy the way the family banner does.
    """
    try:
        with open(path, encoding="utf-8") as fh:
            return LETTER_MARKER in fh.read(4096)
    except OSError:
        return False


def check_all(directory: str) -> int:
    """Run the single-file gate over every .typ under `directory`.

    Re-invokes this script per file rather than refactoring main() apart: the
    point is that each deliverable gets EXACTLY the check it would get alone,
    and a subprocess guarantees that for free (including its exit code and its footer).
    lib*.typ and icons*.typ are shared code, not deliverables; academic CVs and letters carry
    their own gates (`is_academic`, `is_letter`).
    """
    typs = sorted(f for f in glob.glob(os.path.join(directory, "**", "*.typ"),
                                       recursive=True)
                  if not os.path.basename(f).startswith(("lib", "icons"))
                  and not is_academic(f) and not is_letter(f))
    for t in [t for t in typs if not is_gated(t)]:
        print(f"SKIP  {t}  (name matches a non-CV deliverable, no `// vitae:` header)")
    skipped = len(typs) - len([t for t in typs if is_gated(t)])
    typs = [t for t in typs if is_gated(t)]
    if not typs:
        print(f"{skipped} skipped, 0 checked" if skipped
              else f"no .typ found under {directory}")
        return 1
    fail, unchecked = 0, []
    for typ in typs:
        with open(typ, encoding="utf-8") as fh:
            m = HEADER_RE.search(fh.read(4096))
        if m:
            args = [m.group(1)] + ([m.group(2), m.group(3)] if m.group(2) else [])
        else:
            # No header: take the page count from the FILE NAME, which is the one expectation
            # this repo already states out loud (`*-2page.typ` is two pages, every other
            # deliverable is one; SKILL.md step 4 and the read-me sweep are written that way).
            # Not one of the repo's own 30 .typ files carries the header, so demanding it made
            # --all return 30 UNCHECKED and exit 1 on the very corpus it exists to guard. Fill
            # stays undeclared and is reported, not failed: a page count is inferable from a
            # name, a fill target is not, and inventing one would be the fitted-curve mistake
            # again. A `// vitae:` header on a deliverable whose fill matters wins over the name.
            args = [pages_from_name(typ)]
            unchecked.append(typ)
        print(f"\n=== {typ}  (expects {' '.join(args)}"
              f"{'' if m else ' — inferred from the file name, no header'})")
        r = subprocess.run([sys.executable,
                            os.path.join(os.path.dirname(os.path.abspath(__file__)), "verify.py"), typ]
                           + args)
        fail |= bool(r.returncode)
    if unchecked:
        print("\nNOTE — page count inferred from the file name, fill not "
              "checked (add `// vitae: pages=N fill=A-B` to pin either):")
        for t in unchecked:
            print(f"  {t}")
    print("\n" + ("FAIL — see above" if fail else
                  f"PASS — {len(typs)} deliverable(s), "
                  f"all siblings checked together"))
    return fail


def digest_of(f: str) -> str:
    """sha256 of a lib file, BOM and CRLF normalised, so a copy re-saved on Windows still matches."""
    with open(f, "rb") as fh:
        data = fh.read()
    if data.startswith(b"\xef\xbb\xbf"):
        data = data[3:]
    return hashlib.sha256(data.replace(b"\r\n", b"\n")).hexdigest()


def check_lib_integrity(typ_path: str, skill_dir: str | None = None) -> list[Finding]:
    """Return [(level, msg)] for the lib.typ the CV imports (Level.FAIL/Level.WARN);
    empty when it is the skill's own lib or the CV imports none. Runs before
    compilation so the message survives a Typst error.

    FAIL for a lib whose content differs from the skill's (older release or edited: a model once
    rewrote it from memory, dropped `derive()` and looped; BOM and CRLF are ignored); WARN, not FAIL,
    when a lib.typ sits beside the CV but no import resolves to it (integrity unchecked)."""
    skill_dir = skill_dir or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ref = os.path.join(skill_dir, "templates", "lib.typ")
    # Follow local #import "x.typ" chains (cv.typ -> family.typ -> lib.typ).
    lib, shown, seen, todo = None, None, set(), [os.path.abspath(typ_path)]
    direct = False   # the CV's own file imports lib.typ (not a family file)
    while todo and lib is None:
        f = todo.pop(0)
        if f in seen:
            continue
        seen.add(f)
        try:
            with open(f, encoding="utf-8-sig", errors="replace") as fh:
                src = fh.read()
        except OSError:
            continue
        src = _strip_typst_comments(src)
        for imp in re.findall(r'\bimport\s*\(?\s*"([^"]+\.typ)"', src):
            base = os.path.dirname(os.path.abspath(typ_path)) if imp.startswith("/") else os.path.dirname(f)
            path = os.path.normpath(os.path.join(base, imp.lstrip("/") if imp.startswith("/") else imp))
            if os.path.basename(imp) == "lib.typ":
                lib, shown = path, imp
                direct = f == os.path.abspath(typ_path)
                break
            todo.append(path)
    if lib is None and os.path.isfile(ref) and os.path.isfile(
            os.path.join(os.path.dirname(os.path.abspath(typ_path)), "lib.typ")):
        return [(Level.WARN, "lib import not recognised: a lib.typ sits next to the CV but no #import "
                         "resolves to it, so its integrity was NOT checked")]
    if lib is None or not os.path.isfile(ref):
        return []
    cv_dir = os.path.dirname(lib)
    import shlex
    cp = f"cp {shlex.quote(ref)} {shlex.quote(cv_dir + '/')}"
    here = os.path.dirname(os.path.abspath(typ_path))
    if direct and os.path.normpath(cv_dir) != os.path.normpath(here):
        # A family template copied without its "change the import" step: the
        # import still climbs out of the CV folder. Copy lib.typ NEXT TO cv.typ.
        cp = f"cp {shlex.quote(ref)} {shlex.quote(here + '/')}"
        if not os.path.isfile(lib) or digest_of(lib) != digest_of(ref):
            return [(Level.FAIL, f'cv.typ imports "{shown}" (outside this folder): change the import to '
                             f'`#import "lib.typ": *` and copy lib.typ next to cv.typ: {cp}')]
    if not os.path.isfile(lib):
        return [(Level.FAIL, f"{shown} is imported but missing — copy it: {cp}")]
    if digest_of(lib) == digest_of(ref):
        return []
    return [(Level.FAIL, "lib.typ differs from the skill's (older release or edited): "
                     f"copy it again: {cp}")]


_LOWERED_WARN = ("WARN  fill target lowered below drawn target {a} — allowed ONLY if "
                 "the facts are exhausted; tell the user the page is under-filled and which "
                 "facts would fill it; never pad or invent to reach it (rule 1)")
_LOWERED_FAIL = ("FAIL  fill target lowered to {lo}-{hi}% is below the lowered-target floor "
                 "({fl}%, drawn target {a}) — an exhausted fact sheet lowers the target by a "
                 "few points, never below {fl}%; ask the user for more facts, drop to fewer "
                 "pages, or raise FILL_MIN")


_LEADING_WARN = ("WARN  leading {l:.3f}em reads as DOUBLE-SPACED on multi-line paragraphs "
                 "(shipped templates stay <= 0.96em; warns above {t:.2f}em) — the page is "
                 "padded with air, not content. Prefer adding a real fact (a bullet, a "
                 "result, a project) over leading; if the facts are exhausted, accept the "
                 "lower fill and tell the user")


# Relative twin of LEADING_WARN: prose leading against bullet spacing.
LEADING_RATIO_WARN = 1.95   # leading / list spacing; strictly above it the WARN fires (a real 1.0em/0.5em run, ratio 2.00, read double-spaced; highest shipped template is 1.89)
_LEADING_RATIO_WARN = ("WARN  leading {l:.3f}em vs bullet spacing {s:.3f}em (ratio {r:.2f}, warns above "
                       "{t:.2f}) — wrapped prose reads DOUBLE-SPACED next to the bullets. Lower the "
                       "leading (`--tune` downward, or reduce `#set par(leading:)`) or raise the "
                       "`#set list(spacing:)` so prose and bullets read with the same rhythm")


def _leading_warn(typ: str) -> str:
    """The WARN line when cv.typ's document leading is above LEADING_WARN (absolute check), or above
    LEADING_RATIO_WARN times the explicit top-level list spacing (relative check; the absolute one
    takes precedence), else ''. A WARN, never a FAIL: the page may be honestly full; the
    message points at the facts to add instead."""
    try:
        lead, lsp = _doc_par_list(open(typ, encoding="utf-8").read())
    except OSError:
        return ""
    if lead is None:
        return ""
    if lead > LEADING_WARN + 1e-9:
        return _LEADING_WARN.format(l=lead, t=LEADING_WARN)
    # Relative check: only when the list spacing is explicit (a list with no
    # `spacing:` follows Typst's own defaults, so the ratio is unknown: silent).
    if lsp and lsp > 0 and lead / lsp > LEADING_RATIO_WARN + 1e-9:
        return _LEADING_RATIO_WARN.format(l=lead, s=lsp, r=lead / lsp, t=LEADING_RATIO_WARN)
    return ""


# Type size is the other way to pad a page: LEADING_WARN's twin for the body size.
BODY_SIZE_WARN = 11.0   # pt; strictly above it the WARN fires (shipped templates: 10.5pt, margin-index and letter 11pt)
_BODY_SIZE_WARN = ("WARN  body text {z:g}pt (shipped templates stay at 10.5-11pt; warns above {t:g}pt) — "
                   "the page is padded with type size, not content, and the heading/role/meta "
                   "hierarchy inverts because the template sizes are absolute pt. Bring the body "
                   "back to the template size and add a real fact (a bullet, a result, a project) "
                   "instead; if the facts are exhausted, accept the lower fill and tell the user")


def _body_size_warn(typ: str) -> str:
    """The WARN line when cv.typ's top-level body text size is above BODY_SIZE_WARN, else ''."""
    try:
        size = _doc_body_size(open(typ, encoding="utf-8").read())
    except OSError:
        return ""
    if size is not None and size > BODY_SIZE_WARN + 1e-9:
        return _BODY_SIZE_WARN.format(z=size, t=BODY_SIZE_WARN)
    return ""


def _check_cv(typ: str, expected: str, fmin: str | None, fmax: str | None,
              facts: str | None = None) -> NoReturn:
    """The one-file gate: cv.typ PAGES [FILL_MIN FILL_MAX] [--facts facts.md]. Never returns:
    it exits 0 on PASS and 1 on any FAIL, after printing every line so one run lists every fix.
    The order of the gates is the one documented in the module docstring."""
    pdf = re.sub(r"\.typ$", "", typ) + ".pdf"
    fail = 0
    # The drawn fill target lives in the cv.typ header; the command line may
    # not quietly lower it (a lowered target is a WARN carried to the PASS line).
    # The leading and body-size WARNs print up front and again after PASS, where they are read.
    if not _fill_args_ok(fmin, fmax):
        sys.exit(1)
    drawn, drawn_warns = _drawn_fill(typ)
    for w in drawn_warns:
        print(w)
    lead_warn = _leading_warn(typ)
    if lead_warn:
        print(lead_warn)
    size_warn = _body_size_warn(typ)
    if size_warn:
        print(size_warn)
    lowered = ""
    if drawn:
        if not (fmin and fmax):
            fmin, fmax = str(drawn[0]), str(drawn[1])
            print(f"INFO  fill target {fmin}-{fmax}% drawn for this CV (family table / cv.typ header)")
        elif int(fmin) < min(drawn[0], LOWERED_FILL_FLOOR):
            print(_LOWERED_FAIL.format(lo=fmin, hi=fmax, fl=LOWERED_FILL_FLOOR,
                                       a=f"{drawn[0]}-{drawn[1]}"))
            fail = 1
        elif int(fmin) < drawn[0]:
            lowered = f"{drawn[0]}-{drawn[1]} → {fmin}-{fmax}"
            print(_LOWERED_WARN.format(a=f"{drawn[0]}-{drawn[1]}"))

    deps_ok, use_cli, backend = preflight()
    if not deps_ok:
        sys.exit(1)
    STATE.footer = _FOOTER_GATE     # armed only now: before this, a FAIL is not about cv.typ

    for level, msg in check_lib_integrity(typ):
        print(f"{level}  {msg}")
        fail |= level == Level.FAIL

    ensure_icons(typ)     # the icons file the CV imports must exist before it compiles
    ok, err = compile_pdf(typ, pdf, use_cli)
    if not ok:
        print("FAIL  compile")
        print(err)
        sys.exit(1)
    if "did not converge" in err:
        print("FAIL  compile: Typst warns the layout did not converge, so the PDF depends on "
              "which iteration it stopped at — either the CV's lib.typ is an older copy (recopy "
              "the skill's lib.typ next to it) or a construct in cv.typ reads its own layout "
              "(context / query / locate / measure) and changes it; remove that construct "
              "(the shipped lib converges)")
        fail = 1
    if err.strip():
        print("WARN  compile stderr (a missing font only warns and falls back):")
        print(err)

    pages = count_pages(pdf, backend)
    if pages == expected:
        print(f"OK    pages: {pages}")
    else:
        print(f"FAIL  pages: {pages} (expected {expected}) — cut or add real content in cv.typ "
              f"(or, if {expected} was the wrong target, re-run with the right page count)")
        fail = 1

    family = family_from_path(typ)
    pages_text = word_boxes(pdf, with_text=True)  # None => no word boxes: the dependent gates degrade to a WARN
    pages_boxes = [[b for b, _ in pg] for pg in pages_text] if pages_text is not None else None

    with tempfile.TemporaryDirectory() as tmp:
        pngs = render_pngs(typ, tmp, use_cli)
        if not pngs:
            # No PNG => measure_fill never ran => the fill target is UNTESTED.
            # Silently passing here is how a broken render reads as a PASS: this is a FAIL
            # because the tool is required (preflight), so a missing render is a fault.
            print("FAIL  no PNG rendered — fill unmeasured")
            fail = 1
        if not (fmin and fmax):
            print("WARN  fill NOT checked (no FILL_MIN FILL_MAX given) — rerun "
                  f"as scripts/verify.py {shlex.quote(typ)} {expected} FILL_MIN FILL_MAX; "
                  "the targets come from the pick_design.py report "
                  '("fill target : NN-NN%") and differ per family')
        under_fills: list[int] = []
        for i, path in enumerate(pngs):
            result = measure_fill.measure(path)
            if "blank page" in result:
                print(f"FAIL  fill: {path}: {result}")
                fail = 1
                continue
            if fmin and fmax:
                m = re.search(r"to (\d+)%", result)
                if not m:
                    continue
                y = int(m.group(1))
                if y < int(fmin) or y > int(fmax):
                    print(f"FAIL  fill: {path}: {result} (target {fmin}-{fmax}%) — "
                          f"run `scripts/verify.py --tune {shlex.quote(typ)} {expected} {fmin} {fmax}` "
                          "(adjusts leading), or add/cut real content")
                    if y < int(fmin):
                        under_fills.append(y)
                    fail = 1
                else:
                    print(f"OK    fill: {path}: {result}")
            else:
                print(f"INFO  fill: {path}: {result} (target = (100 - bottom-margin%) - 0..2%)")
            boxes = pages_boxes[i] if pages_boxes and i < len(pages_boxes) else None
            if pages_text is None and i == 0:
                print(f"WARN  text-clip gate skipped: {_boxes_unavailable()}")
            for msg in check_text_clip(path, pages_text[i] if pages_text and i < len(pages_text) else None):
                print("FAIL  " + msg)
                fail = 1
            for is_fail, msg in check_whitespace(path, boxes=boxes, family=family,
                                                 degraded=boxes is None):
                print(f"{'FAIL' if is_fail else 'OK  '}  {msg}")
                fail = fail or int(is_fail)

    if under_fills:
        lowest = min(under_fills)    # FILL_MIN applies to every page: the lowest page decides
        if lowest < LOWERED_FILL_FLOOR:
            print(f"NEXT  fill {lowest}% is below the {LOWERED_FILL_FLOOR}% floor, so a lowered target "
                  "cannot pass: a fact is missing — add real facts or ask the user"
                  + (", or drop to fewer pages" if int(expected) > 1 else ""))
        else:
            print("NEXT  if --tune already reported UNDER-FILLED, a fact is missing: add one, or — only "
                  "if the facts are exhausted — pass a lowered target: "
                  f"`scripts/verify.py {shlex.quote(typ)} {expected} {lowest} {fmax}` (FILL_MIN = the "
                  f"lowest fill the gate prints, not below {LOWERED_FILL_FLOOR}) and tell the user")
    # Clone markers: the template's own accent and its "Category: items" skills block, left in
    # place, make every CV from the skill look alike (references/design/core.md, three clone markers).
    typ_text = open(typ, encoding="utf-8").read()
    if "7d2231" in typ_text.lower():
        print("WARN  template default accent (#7d2231) — run scripts/pick_design.py and apply the family it draws (references/design/families/<family>.md)")
    if "[#cat:]" in typ_text:
        print("WARN  template skills block (\"Category: items\") — clone marker #2; use the chosen family's skills shape")

    if backend == "pypdf":     # the fallback extractor: say so once, `bad()` below then downgrades to WARN
        print("WARN  pypdf extraction is indicative only (spurious spaces inside words, e.g. \"FORMA TION\") — poppler's pdftotext is the reference extractor (references/ats.md)")

    txt = extract_text(pdf, backend)

    def bad(msg: str) -> None:
        """FAIL on the reference extractor, WARN on the pypdf fallback: pypdf's
        extraction is indicative only (this script says so above), so a hard
        FAIL on it would be a verdict the evidence does not support."""
        nonlocal fail
        if backend != "pypdf":
            print("FAIL  " + msg)
            fail = 1
        else:
            print("WARN  " + msg + " — pypdf extraction is indicative; confirm with pdftotext before believing it")

    if not txt.strip():
        bad("extraction empty")
    # Letterspaced capitals break keyword matching in an ATS. First pattern: 4+ STANDALONE
    # capitals (the \b anchors keep "B.Sc. C S M Sc", dotted abbreviations, out). Second
    # pattern: tracking's real pdftotext shape, chunked rather than fully spaced
    # ("S O F T WA RE"). Known limit: a space injected INSIDE a word ("FORMA TION") is not
    # detectable here: it is a pypdf extraction artefact, not a layout bug, and only the
    # pypdf path (WARN-only above) produces it.
    spaced: str | re.Match[str] | None = re.search(r"\b(?:[A-Z] ){3,}[A-Z]\b", txt)
    if not spaced:
        for line in txt.split("\n"):
            tok = line.split()
            if (len(tok) >= 4 and all(re.fullmatch(r"[A-Z]{1,2}", t) for t in tok)
                    and sum(len(t) == 1 for t in tok) >= 2):
                spaced = line
                break
    if spaced:
        bad("spaced-out text in extraction (letterspacing/tracking?)")
    # Per PAGE: a date alone at the foot of a page is read by an ATS as belonging to no entry;
    # it lands at the end of its own page, not only at the end of the document.
    for pageno, page in enumerate(txt.split("\f"), 1):
        non_blank = [l for l in page.split("\n") if l.strip()]
        last = non_blank[-1] if non_blank else ""
        if len(last) <= 25 and re.search(r"[0-9]{4}\s*$", last):
            bad(f'orphaned date at end of page {pageno} of the extraction ("{last}") — bullet-less grid entry; see the trap in references/ats.md')
    for is_fail, msg in check_no_split(typ_text, txt.split("\f")):
        if is_fail:
            bad(msg)
        else:
            print("OK    " + msg)

    if facts:
        try:
            facts_text = open(facts, encoding="utf-8").read()
        except OSError as e:
            print(f"FAIL  --facts: cannot read {facts} ({e.strerror})")
            fail = 1
        else:
            for w in check_facts_coverage(txt, facts_text):
                print(w)
    bullets = check_bullet_chars(txt)
    if bullets:
        print(f'WARN  {len(bullets)} line(s) start with a bullet character in the extraction (e.g. "{bullets[0][:30]}") — ATS prints it or puts it alone on a line; draw list markers as vector shapes (references/ats.md)')

    if use_cli or typst_can_query():
        fail |= run_new_gates(typ, pdf, txt, typ_text)
    else:
        # No `typst query`: say which gates are skipped, then run the ones that need only the
        # PDF or the source text, so the degraded run still covers as much as it can.
        print("WARN  grouping / date-adjacency / duplicate-name gates NOT checked (need the typst CLI or typst-py with query)")
        fail |= run_hidden_gate(pdf)
        for lvl, msg in check_font_fallback(typ, pdf):
            print(f"{lvl:<5} {msg}")
            fail |= lvl == Level.FAIL
        for msg in check_forced_linebreak(typ_text) + check_literal_tilde(typ_text):
            print("FAIL  " + msg)
            fail = 1

    # The extraction is printed last, whatever the verdict: the reading-order check is the
    # agent's, by hand (references/steps/6-verify.md), and needs the text next to the PASS/FAIL.
    print("──── extraction (check reading order, orphaned dates, intact skill lines) ────")
    print(txt)

    if fail == 0:
        if lowered:
            print(f"PASS (fill target lowered: {lowered}) all mechanical checks — now LOOK at the PNGs")
            print(_LOWERED_WARN.format(a=lowered.split(" ")[0]))
        elif fmin and fmax:
            print("PASS  all mechanical checks — now LOOK at the PNGs")
        else:
            print("PASS  mechanical checks except fill (no FILL_MIN FILL_MAX "
                  "given) — rerun with the fill targets from the pick_design.py "
                  "report, then LOOK at the PNGs")
        if lead_warn:        # repeated after PASS so a green run does not bury them
            print(lead_warn)
        if size_warn:
            print(size_warn)

    sys.exit(fail)

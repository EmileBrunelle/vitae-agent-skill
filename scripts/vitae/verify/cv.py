"""The per-CV gate: header parsing, file classification, check_all, lib integrity, the new-gate runner and check_cv.

No `import verify`.
"""
from __future__ import annotations

import functools
import glob
import os
import re
import shlex
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

import vitae.fill as measure_fill
from vitae.core import proc
from vitae.core.base import (
    FOOTER_GATE,
    LEADING_ABS_RATIO_WARN,
    LEADING_FAMILY_RATIO_WARN,
    LEADING_WARN,
    LOWERED_FILL_FLOOR,
)
from vitae.core.env import preflight, typst_can_query
from vitae.core.level import Finding, Level
from vitae.core.typst_source import strip_typst_comments
from vitae.design.libapi import OLD_LIB_NOTE, is_old_lib
from vitae.verify import placeholders
from vitae.verify.bounds import too_many_pages
from vitae.verify.gates import GATES, make_context
from vitae.verify.layout import check_text_clip, check_whitespace
from vitae.verify.pdf import (
    boxes_unavailable,
    compile_or_messages,
    count_pages,
    ensure_icons,
    extract_text,
    family_from_path,
    render_pngs,
    run_memo,
    word_boxes,
)
from vitae.verify.registry import note_extraction, run_gates
from vitae.verify.review_record import check_review_record, layout_report_line
from vitae.verify.source import drawn_fill, fill_args_ok
from vitae.verify.typst import doc_body_size, doc_par_list

# ---------- main gate ----------

HEADER_RE = re.compile(r"^//\s*vitae:\s*pages=(\d+)(?:\s+fill=(\d+)-(\d+))?",
                       re.MULTILINE)


def pages_from_name(typ: str) -> str:
    """The page count a headerless deliverable declares in its own file name."""
    return "2" if re.search(r"[-_]2\s*p(?:ages?)?(?![a-z])",
                            os.path.basename(typ), re.IGNORECASE) else "1"


# Whole-word stems of non-CV companion deliverables (step 7 application guide, cover letter, readme)
# that `verify.py --all` skips when they carry no `// vitae:` header (step 6).
NON_CV_RE = re.compile(
    r"(?<![^\W\d_])(?:guide|lettre|letter|cover|lisez-moi|readme)(?![^\W\d_])",
    re.IGNORECASE)


def read_head(path: str) -> str | None:
    """The first 4096 characters of a file (the window every marker and header is looked for in), or None when it cannot be read as UTF-8 text."""
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read(4096)
    except (OSError, UnicodeDecodeError):
        return None


def is_gated_head(typ: str, head: str | None) -> bool:
    """--all's rule: gate every .typ except known non-CV deliverables (guide,
    letter, cover, lisez-moi, readme by name); a `// vitae:` header opts in.
    `head` is the file's `read_head` (None: unreadable), only consulted for a companion name."""
    if not NON_CV_RE.search(os.path.basename(typ)):
        return True
    return head is not None and bool(HEADER_RE.search(head))


def is_gated(typ: str) -> bool:
    """`is_gated_head` on a path; an ordinary name never opens the file."""
    if not NON_CV_RE.search(os.path.basename(typ)):
        return True
    return is_gated_head(typ, read_head(typ))


# Both markers (and HEADER_RE in is_gated/check_all) are looked for in the first 4096 bytes:
# they sit on line 1 (or in the opening comment block) so reading 4 KiB avoids loading large files.
ACADEMIC_MARKER = "// vitae-academic:"
LETTER_MARKER = "// vitae letter template"


def is_academic_head(head: str | None) -> bool:
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
    return head is not None and ACADEMIC_MARKER in head


def is_academic(path: str) -> bool:
    """`is_academic_head` on a path."""
    return is_academic_head(read_head(path))


def refuse_academic(typ: str) -> None:
    """Exit 2 (wrong invocation) with ONE stderr line when `typ` is an academic CV: the standard gate would print
    FAILs about a genre it is not calibrated for, and a weaker agent would "fix" a correct CV. Called at the entry
    of `check_cv` (every one-file gate run) and by `--tune` (which compiles without `check_cv`)."""
    if is_academic(typ):
        print(f"{typ}: academic CV — run scripts/verify_academic.py {typ} instead; "
              "the standard gate does not judge this genre", file=sys.stderr)
        sys.exit(2)


def is_letter_head(head: str | None) -> bool:
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
    return head is not None and LETTER_MARKER in head


def is_letter(path: str) -> bool:
    """`is_letter_head` on a path."""
    return is_letter_head(read_head(path))


def placeholders_allowed(typ: str) -> bool:
    """`--allow-placeholders` is honoured only for a file under this skill's own templates/ folder (the shipped
    templates, and the scratch copies the test runs make inside it), never for a CV the user is delivering."""
    return Path(typ).resolve().is_relative_to(placeholders.TEMPLATES.resolve())


ALLOW_REFUSED = "FAIL  --allow-placeholders is only for the shipped templates (a file under the skill's templates/ folder)"


def check_all(directory: str, allow_placeholders: bool = False, rebuild: bool = False) -> int:
    """Run the single-file gate over every .typ under `directory`.

    Re-invokes this script per file rather than refactoring main() apart: the
    point is that each deliverable gets EXACTLY the check it would get alone,
    and a subprocess guarantees that for free (including its exit code and its footer).
    lib*.typ and icons*.typ are shared code, not deliverables; academic CVs and letters carry
    their own gates (`is_academic`, `is_letter`).
    """
    heads: dict[str, str | None] = {}
    for f in sorted(glob.glob(os.path.join(directory, "**", "*.typ"), recursive=True)):
        if os.path.basename(f).startswith(("lib", "icons")):
            continue
        head = read_head(f)
        if not is_academic_head(head) and not is_letter_head(head):
            heads[f] = head
    gated = {f: is_gated_head(f, h) for f, h in heads.items()}
    for t in [t for t in heads if not gated[t]]:
        print(f"SKIP  {t}  (name matches a non-CV deliverable, no `// vitae:` header)")
    typs = [t for t in heads if gated[t]]
    skipped = len(heads) - len(typs)
    if not typs:
        print(f"{skipped} skipped, 0 checked" if skipped
              else f"no .typ found under {directory}")
        return 1
    fail = 0
    unchecked: list[str] = []
    for typ in typs:
        head = heads[typ]
        if head is None:
            print(f"\n=== {typ}\nFAIL  unreadable: the file could not be read as UTF-8 text")
            fail = 1
            continue
        m = HEADER_RE.search(head)
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
        try:
            r = proc.run([sys.executable,
                                os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "verify.py"), typ]
                               + args + (["--allow-placeholders"] if allow_placeholders else [])
                               + (["--rebuild"] if rebuild else []), proc.RERUN_S, name="verify.py", capture=False)
        except proc.ToolTimeout as e:   # one hung deliverable is its own FAIL; the sweep goes on with the next file
            print(f"FAIL  {typ}: verify timed out after {e.limit:g} s")
            fail = 1
            continue
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


def lib_text(path: str) -> str:
    """The text of a lib file."""
    return _normalised(path).decode("utf-8", errors="replace")


def _normalised(f: str) -> bytes:
    """A lib file's bytes, BOM and CRLF normalised, so a copy re-saved on Windows still compares equal."""
    with open(f, "rb") as fh:
        return fh.read().removeprefix(b"\xef\xbb\xbf").replace(b"\r\n", b"\n")


def check_lib_integrity(typ_path: str, skill_dir: str | None = None) -> list[Finding]:
    """Return [(level, msg)] for the lib.typ the CV imports (Level.FAIL/Level.WARN);
    empty when it is the skill's own lib or the CV imports none. Runs before
    compilation so the message survives a Typst error.

    FAIL for a lib whose content differs from the skill's (older release or edited: a model once
    rewrote it from memory, dropped `derive()` and looped; BOM and CRLF are ignored); WARN, not FAIL,
    when a lib.typ sits beside the CV but no import resolves to it (integrity unchecked)."""
    skill_dir = skill_dir or os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    ref = os.path.join(skill_dir, "templates", "lib.typ")
    # Follow local #import "x.typ" chains (cv.typ -> family.typ -> lib.typ).
    lib, shown, todo = None, None, [os.path.abspath(typ_path)]
    seen: set[str] = set()
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
        src = strip_typst_comments(src)
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
        if not os.path.isfile(lib) or _normalised(lib) != _normalised(ref):
            return [(Level.FAIL, f'cv.typ imports "{shown}" (outside this folder): change the import to '
                             f'`#import "lib.typ": *` and copy lib.typ next to cv.typ: {cp}')]
    if not os.path.isfile(lib):
        return [(Level.FAIL, f"{shown} is imported but missing — copy it: {cp}")]
    if _normalised(lib) == _normalised(ref):
        return []
    old = OLD_LIB_NOTE + "; " if is_old_lib(lib_text(lib)) else ""
    return [(Level.FAIL, f"lib.typ differs from the skill's (older release or edited): {old}"
                     f"copy it again: {cp}")]


_LOOK_CUE = "now LOOK at the PNGs (Visual pass:), then step 7"
_LOWERED_WARN = ("WARN  fill target lowered below drawn target {a} — allowed ONLY if "
                 "the facts are exhausted; tell the user the page is under-filled and which "
                 "facts would fill it; never pad or invent to reach it (rule 1)")
_LOWERED_FAIL = ("FAIL  fill target lowered to {lo}-{hi}% is below the lowered-target floor "
                 "({fl}%, drawn target {a}) — an exhausted fact sheet lowers the target by a "
                 "few points, never below {fl}%; ask the user for more facts, drop to fewer "
                 "pages, or raise FILL_MIN")


_LEADING_WARN = ("WARN  leading {l:.3f}em reads as DOUBLE-SPACED on multi-line paragraphs "
                 "(the gate warns above {t:.2f}em; the shipped templates stay well below) — the page is "
                 "padded with air, not content. Prefer adding a real fact (a bullet, a "
                 "result, a project) over leading; if the facts are exhausted, accept the "
                 "lower fill and tell the user")


_LEADING_ABS_RATIO_WARN = ("WARN  leading {l:.3f}em vs bullet spacing {s:.3f}em (ratio {r:.2f}, warns above "
                           "{t:.2f}) — wrapped prose reads DOUBLE-SPACED next to the bullets. Lower the "
                           "leading (`--tune` downward, or reduce `#set par(leading:)`) or raise the "
                           "`#set list(spacing:)` so prose and bullets read with the same rhythm")
_LEADING_FAMILY_WARN = ("WARN  the list rhythm no longer matches the paragraph rhythm: leading {l:.3f}em vs "
                        "bullet spacing {s:.3f}em is {r:.2f}x the ratio of the {f} template "
                        "({fl:.3f}em / {fs:.3f}em); warns above {t:.2f}x — wrapped prose reads looser than "
                        "the bullets. Re-run `--tune` (its rhythm phase scales list spacing with the rhythm and keeps leading; its leading phase scales list spacing with leading), or raise "
                        "`#set list(spacing:)` / lower `#set par(leading:)` to restore the family ratio. "
                        "Type size and leading are not padding")


@functools.cache
def _family_default(family: str, pages: int) -> tuple[float, float] | None:
    """(leading, list spacing) in em shipped by templates/families/<family>: resume-2page.typ for
    pages >= 2 when it exists, else resume.typ; None when unknown or either value is not numeric."""
    d = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "templates", "families", family)
    for name in (("resume-2page.typ",) if pages >= 2 else ()) + ("resume.typ",):
        try:
            lead, lsp = doc_par_list(Path(os.path.join(d, name)).read_text(encoding="utf-8"))
        except OSError:
            continue
        if lead and lsp:
            return lead, lsp
    return None


def _leading_warn(typ: str, pages: int = 1) -> str:
    """The WARN line when cv.typ's document leading is above LEADING_WARN (absolute check), or when its
    leading / explicit list spacing ratio is above LEADING_FAMILY_RATIO_WARN times its family's shipped
    ratio (relative check; LEADING_ABS_RATIO_WARN absolute when the family is unknown; the absolute
    leading check takes precedence), else ''. A WARN, never a FAIL: the page may be honestly full; the
    message points at the facts to add instead."""
    try:
        lead, lsp = doc_par_list(Path(typ).read_text(encoding="utf-8"))
    except OSError:
        return ""
    if lead is None:
        return ""
    if lead > LEADING_WARN + 1e-9:
        return _LEADING_WARN.format(l=lead, t=LEADING_WARN)
    # Relative check: only when the list spacing is explicit (a list with no
    # `spacing:` follows Typst's own defaults, so the ratio is unknown: silent).
    if not (lsp and lsp > 0):
        return ""
    family = family_from_path(typ)
    ref = _family_default(family, pages) if family else None
    if ref is None:
        if lead / lsp > LEADING_ABS_RATIO_WARN + 1e-9:
            return _LEADING_ABS_RATIO_WARN.format(l=lead, s=lsp, r=lead / lsp, t=LEADING_ABS_RATIO_WARN)
        return ""
    rel = (lead / lsp) / (ref[0] / ref[1])
    if rel > LEADING_FAMILY_RATIO_WARN + 1e-9:
        return _LEADING_FAMILY_WARN.format(l=lead, s=lsp, r=rel, f=family, fl=ref[0], fs=ref[1],
                                           t=LEADING_FAMILY_RATIO_WARN)
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
        size = doc_body_size(Path(typ).read_text(encoding="utf-8"))
    except OSError:
        return ""
    if size is not None and size > BODY_SIZE_WARN + 1e-9:
        return _BODY_SIZE_WARN.format(z=size, t=BODY_SIZE_WARN)
    return ""


@dataclass(frozen=True)
class PageTarget:
    """The command-line page target, as typed: `expected` pages and the optional FILL_MIN / FILL_MAX percentages."""
    expected: str
    fmin: str | None = None
    fmax: str | None = None


def check_cv(typ: str, target: PageTarget, *, facts: str | None = None, allow_placeholders: bool = False,
              rebuild: bool = False) -> tuple[int, str | None]:
    """`_check_cv` in its own memo scope: each tool runs once per file state in this gate run and never across runs.
    An academic CV is refused first (`refuse_academic`): this is the one door every one-file CV run passes through."""
    refuse_academic(typ)
    with run_memo():
        return _check_cv(typ, target, facts=facts, allow_placeholders=allow_placeholders, rebuild=rebuild)


def _check_cv(typ: str, target: PageTarget, *, facts: str | None = None, allow_placeholders: bool = False,
              rebuild: bool = False) -> tuple[int, str | None]:
    """The one-file gate: cv.typ PAGES [FILL_MIN FILL_MAX] [--facts facts.md]. Returns (exit code,
    footer): 0 on PASS and 1 on any FAIL, after printing every line so one run lists every fix; the
    footer is the NEXT line the CLI prints last on a failure, None until preflight passed.
    The order of the gates is the one documented in the module docstring."""
    expected, fmin, fmax = target.expected, target.fmin, target.fmax
    pdf = re.sub(r"\.typ$", "", typ) + ".pdf"
    fail = 0
    footer: str | None = None
    if allow_placeholders and not placeholders_allowed(typ):
        print(ALLOW_REFUSED)
        allow_placeholders, fail = False, 1
    allow = " --allow-placeholders" if allow_placeholders else ""
    # The drawn fill target lives in the cv.typ header; the command line may
    # not quietly lower it (a lowered target is a WARN carried to the PASS line).
    # The leading and body-size WARNs print up front and again after PASS, where they are read.
    if not fill_args_ok(fmin, fmax):
        return 1, footer
    drawn, drawn_warns = drawn_fill(typ)
    for w in drawn_warns:
        print(w)
    lead_warn = _leading_warn(typ, int(expected) if str(expected).isdigit() else 1)
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

    pf = preflight()
    backend = pf.backend
    if not pf.ok:
        return 1, footer
    footer = FOOTER_GATE     # armed only now: before this, a FAIL is not about cv.typ

    for level, msg in check_lib_integrity(typ):
        print(f"{level}  {msg}")
        fail |= level == Level.FAIL

    ensure_icons(typ)     # the icons file the CV imports must exist before it compiles
    err, failed = compile_or_messages(typ, pdf)
    if failed:
        for msg in failed:
            print(f"FAIL  {msg}")
        return 1, footer
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
    too_long = too_many_pages(os.path.basename(pdf), pages)
    if too_long:
        print(f"FAIL  {too_long}")
        return 1, footer
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
        pngs = render_pngs(typ, tmp)
        if not pngs:
            # No PNG => measure_fill never ran => the fill target is UNTESTED.
            # Silently passing here is how a broken render reads as a PASS: this is a FAIL
            # because the tool is required (preflight), so a missing render is a fault.
            print("FAIL  no PNG rendered — fill unmeasured")
            fail = 1
        if not (fmin and fmax):
            print("WARN  fill NOT checked (no FILL_MIN FILL_MAX given) — rerun "
                  f"as scripts/verify.py {shlex.quote(typ)} {expected} FILL_MIN FILL_MAX{allow}; "
                  "the targets come from the pick_design.py report "
                  '("fill target : NN-NN%") and differ per family')
        under_fills: list[int] = []
        fills: list[str] = []
        for i, path in enumerate(pngs):
            result = measure_fill.measure(path)
            if "blank page" in result:
                print(f"FAIL  fill: {os.path.basename(path)}: {result}")
                fail = 1
                continue
            m = re.search(r"to (\d+)%", result)
            if m:
                fills.append(m.group(1))
            if fmin and fmax:
                if not m:
                    continue
                y = int(m.group(1))
                if y < int(fmin) or y > int(fmax):
                    print(f"FAIL  fill: {os.path.basename(path)}: {result} (target {fmin}-{fmax}%) — "
                          f"run `scripts/verify.py --tune {shlex.quote(typ)} {expected} {fmin} {fmax}{allow}` "
                          "(adjusts leading), or add/cut real content")
                    if y < int(fmin):
                        under_fills.append(y)
                    fail = 1
                else:
                    print(f"OK    fill: {os.path.basename(path)}: {result}")
            else:
                print(f"INFO  fill: {os.path.basename(path)}: {result} (target = (100 - bottom-margin%) - 0..2%)")
            boxes = pages_boxes[i] if pages_boxes and i < len(pages_boxes) else None
            if pages_text is None and i == 0:
                print(f"WARN  text-clip gate skipped: {boxes_unavailable(pdf)}")
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
                  f"`scripts/verify.py {shlex.quote(typ)} {expected} {lowest} {fmax}{allow}` (FILL_MIN = the "
                  f"lowest fill the gate prints, not below {LOWERED_FILL_FLOOR}) and tell the user")
    # Clone markers: the template's own accent and its "Category: items" skills block, left in
    # place, make every CV from the skill look alike (references/design/draw-rules.md, three clone markers).
    typ_text = Path(typ).read_text(encoding="utf-8")
    if "7d2231" in typ_text.lower():
        print("WARN  template default accent (#7d2231) — run scripts/pick_design.py and apply the family it draws (references/design/families/<family>.md)")
    if "[#cat:]" in typ_text:
        print("WARN  template skills block (\"Category: items\") — clone marker #2; use the chosen family's skills shape")

    if backend == "pypdf":     # the fallback extractor: say so once, the extraction gates then downgrade to WARN
        print("WARN  pypdf extraction is indicative only (spurious spaces inside words, e.g. \"FORMA TION\") — poppler's pdftotext is the reference extractor (references/ats.md)")

    txt = extract_text(pdf, backend)
    ctx = make_context(typ, pdf, txt, typ_text, backend, facts=facts, can_query=typst_can_query())
    # No `typst query`: the layout gates that need it are skipped with a notice, the rest still run.
    gates = tuple(g for g in GATES if not (allow_placeholders and g.name == "placeholders"))
    if allow_placeholders:
        print("WARN  placeholder gate skipped (--allow-placeholders): only for the shipped templates, never a real CV")
    fail |= run_gates(gates, ctx)

    # The extraction is printed last, whatever the verdict: the reading-order check is the
    # agent's, by hand (references/steps/6-verify.md), and needs the text next to the PASS/FAIL.
    print("──── extraction (check reading order, orphaned dates, intact skill lines) ────")
    note_extraction(txt)
    print(txt)

    if fail == 0:
        # Delivery needs the step-7 review record; the shipped templates, --allow-placeholders runs and --rebuild
        # (a candidate re-tailoring the .typ, never the agent's final verify) are not checked.
        record = [] if allow_placeholders or rebuild else check_review_record(typ)
        record_fail = any(lvl == Level.FAIL for lvl, _ in record)
        notes = (["placeholder gate skipped"] if allow_placeholders else []) \
            + (["review record skipped: --rebuild, candidate rebuild"] if rebuild else [])
        skip = "".join(f"; {n}" for n in notes)
        tag = f"({'; '.join(notes)}) " if notes else " "
        if record_fail:
            if fmin and fmax:
                shown = "/".join(fills)
                print(f"mechanical gates: PASS{f' (fill {shown}%)' if fills else ''}"
                      f"{f' (fill target lowered: {lowered})' if lowered else ''} — {_LOOK_CUE}")
            else:
                print(f"mechanical gates: PASS except fill (no FILL_MIN FILL_MAX given) — {_LOOK_CUE}")
            if lowered:
                print(_LOWERED_WARN.format(a=lowered.split(" ")[0]))
            for lvl, msg in record:
                print(f"{lvl}  {msg}")
            if lead_warn:
                print(lead_warn)
            if size_warn:
                print(size_warn)
            print("FAIL  not deliverable: the review record is missing or incomplete (step 7)")
            return 1, None
        for lvl, msg in record:
            print(f"{lvl}  {msg}")
        if lowered:
            print(f"PASS (fill target lowered: {lowered}{skip}) all mechanical checks — now LOOK at the PNGs")
            print(_LOWERED_WARN.format(a=lowered.split(" ")[0]))
        elif fmin and fmax:
            print(f"PASS {tag}all mechanical checks — now LOOK at the PNGs")
        else:
            print(f"PASS {tag}mechanical checks except fill (no FILL_MIN FILL_MAX "
                  "given) — rerun with the fill targets from the pick_design.py "
                  "report, then LOOK at the PNGs")
        layout = layout_report_line(typ) if record else None   # step-7 report line from review.md: pasted, never retyped
        if layout:
            print(layout)
        if lead_warn:        # repeated after PASS so a green run does not bury them
            print(lead_warn)
        if size_warn:
            print(size_warn)

    return int(fail), footer

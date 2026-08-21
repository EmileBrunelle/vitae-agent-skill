#!/usr/bin/env python3
"""One-command gate for the MECHANICAL subset of SKILL.md step 6 (any
platform with Python 3 -- Linux, macOS, Windows). Exits non-zero if any
check fails. Left to do by hand: the visual PNG inspection, recomputing
the accent's contrast, the date-order check, and re-diffing bullets
against the fact sheet.

Usage:
    verify.py cv.typ EXPECTED_PAGES [FILL_MIN FILL_MAX]
    verify.py --tune cv.typ PAGES FILL_MIN FILL_MAX [LEADING_LO LEADING_HI]
    verify.py --doctor

    e.g. verify.py cv.typ 1 94 96
         verify.py --tune cv.typ 1 94 96

--tune runs the page-fill loop BY BISECTION instead of by hand: it moves the
`#set par(leading:, spacing:)` declaration (keeping the family's own delta
between the two) to the largest rhythm that still holds the expected page
count, writes the winning values into the file, and reports whether the
resulting fill lands in the target. It replaces the compile-measure-adjust
loop an agent would otherwise run a dozen times per family. It tunes NOTHING
else: the section gap, the margins and the type sizes are recipe decisions.
When no value in range reaches the target, it says so rather than inventing
one — that is the anti-filler clause (SKILL.md rule 5), and the fix is the
section gap, real content, or a different page count. But check the RANGE
first: the default search is 0.80-1.30x the current leading, and a font swap
can need a bigger move than that. Pass LEADING_LO/LEADING_HI and re-run before
you touch a device — one family's second font pair looked unreachable, got its
section gap cut by 6pt to compensate, and landed with its boundary sitting
exactly on the separation floor; a wider search range was the real fix.

--doctor runs only the dependency preflight (no cv.typ required), exit
0 if everything needed is present, 1 otherwise -- replaces the old
check_env.sh / check_env.ps1 doctors.

Exit codes: 0 PASS, 1 FAIL (or missing dependency with no fallback),
2 usage error.

Prefers native tools (typst CLI, poppler pdfinfo/pdftotext) but falls
back automatically to their Python equivalents when only those are
installed: the `typst` Python package (compiles via its API, no CLI
needed) and `pypdf` (page count + indicative-only text extraction --
see references/ats.md for the caveat). No functional --install flag:
that meant fetching a binary over HTTPS with no checksum verification;
print the install commands instead and let the user choose.
"""
import glob
import os
import re
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import measure_fill  # noqa: E402


# ---------- dependency preflight ("doctor") ----------

def check_pillow():
    try:
        import PIL  # noqa: F401
        print(f"OK    Pillow {PIL.__version__}")
        return True
    except ImportError:
        print("MISSING  Pillow -- needed for the page-fill measurement:")
        print("  sudo dnf install python3-pillow | sudo apt install python3-pil   # distro Python: official repos first (PEP 668)")
        print("  uv pip install Pillow | pip3 install --user Pillow               # venvs / pip-only environments")
        return False


def check_typst():
    """Returns (available, use_cli)."""
    if shutil.which("typst"):
        try:
            ver = subprocess.run(["typst", "--version"], capture_output=True, text=True).stdout.split()[1]
        except Exception:
            ver = "?"
        print(f"OK    typst {ver} (CLI)")
        return True, True
    try:
        import typst  # noqa: F401
        print("OK    typst (Python API, no CLI)")
        return True, False
    except ImportError:
        print("MISSING  typst -- install with ONE of:")
        print("  brew install typst                          # macOS")
        print("  sudo dnf install typst                      # Fedora")
        print("  sudo apt install typst                      # Debian/Ubuntu (24.04+)")
        print("  sudo pacman -S typst                        # Arch")
        print("  winget install --id Typst.Typst             # Windows")
        print("  choco install typst | scoop install typst   # Windows, if you already use them")
        print("  cargo install typst-cli                      # any, via Rust")
        print("  pip install typst                            # no CLI: compiles via Python API (used automatically if present)")
        return False, False


def check_pdf_tools():
    """Returns (available, use_poppler)."""
    if shutil.which("pdfinfo") and shutil.which("pdftotext"):
        print("OK    poppler-utils (pdftotext, pdfinfo)")
        return True, True
    try:
        import pypdf  # noqa: F401
        print("OK    pypdf (Python fallback -- exact page count, indicative-only extraction)")
        return True, False
    except ImportError:
        print("MISSING  poppler-utils -- needed for page-count and ATS extraction checks:")
        print("  brew install poppler | sudo dnf install poppler-utils | sudo apt install poppler-utils")
        print("  choco install poppler | scoop install poppler          # Windows")
        print("  pip install pypdf                                      # fallback: exact page count, indicative extraction only (used automatically if present)")
        return False, False


def preflight():
    """Prints doctor output; returns (all_ok, use_cli_typst, use_poppler)."""
    pillow_ok = check_pillow()
    typst_ok, use_cli = check_typst()
    pdf_ok, use_poppler = check_pdf_tools()
    return (pillow_ok and typst_ok and pdf_ok), use_cli, use_poppler


# ---------- compile / page-count / extraction, native or fallback ----------

def compile_pdf(typ, pdf, use_cli):
    """Returns (ok, stderr_text)."""
    if use_cli:
        r = subprocess.run(["typst", "compile", typ, pdf], capture_output=True, text=True)
        return r.returncode == 0, (r.stdout + r.stderr)
    try:
        import typst
        typst.compile(typ, output=pdf)
        return True, ""
    except Exception as e:
        return False, str(e)


def render_pngs(typ, tmp_dir, use_cli):
    pattern = os.path.join(tmp_dir, "p{p}.png")
    if use_cli:
        subprocess.run(["typst", "compile", typ, pattern, "--format", "png", "--ppi", "90"],
                        capture_output=True, text=True)
    else:
        import typst
        try:
            typst.compile(typ, output=pattern, format="png", ppi=90)
        except TypeError:
            typst.compile(typ, output=pattern, format="png")
    return sorted(glob.glob(os.path.join(tmp_dir, "p*.png")))


def count_pages(pdf, use_poppler):
    if use_poppler:
        out = subprocess.run(["pdfinfo", pdf], capture_output=True, text=True).stdout
        for line in out.splitlines():
            if line.startswith("Pages:"):
                return line.split()[1]
        return None
    import pypdf
    return str(len(pypdf.PdfReader(pdf).pages))


def extract_text(pdf, use_poppler):
    if use_poppler:
        return subprocess.run(["pdftotext", pdf, "-"], capture_output=True, text=True).stdout
    import pypdf
    reader = pypdf.PdfReader(pdf)
    return "\n".join(page.extract_text() or "" for page in reader.pages)


# ---------- whitespace structure: section boundaries + canyons ----------

# The section boundary must read as a break at arm's length, and that is
# measurable: the boundary gaps are the tallest white runs on the page and they
# stand clear of the intra-section rhythm. Calibrated on the four families
# whose separation reads best (measured max-gap / median-gap at 90 ppi:
# color-band 2.33, hard-edge 3.12, swiss-grid 3.40, bold-display 3.60 — the
# same Verified figures as references/design.md § Invariants, which is the one
# source of truth for them) — the floor sits just under the lowest of them.
# NOTE the counter-intuitive measured fact: the two
# families with the LOWEST white ratio are among the best-separated, because
# their boundary is carried by INK (a 2.5pt rule, a filled bar). White alone is
# therefore a floor, not a quality score; a device-less family needs far more
# than the floor (references/design.md § Rules common to every family).
BOUNDARY_RATIO = 2.0
CANYON = 0.035          # a hole this tall (fraction of page height) is a defect
BOUNDARY_CEILING = 0.05  # …unless it is a section boundary, which may run this tall


def check_whitespace(path):
    """Yield (is_fail, message) for one rendered page."""
    import statistics
    h, runs = measure_fill.gaps(path)
    if len(runs) < 6:
        return                              # not a text page: nothing to judge
    med = statistics.median(runs)
    top = max(runs)
    if med <= 0:
        return
    ratio = top / med
    if ratio < BOUNDARY_RATIO:
        yield True, (f"section separation: biggest internal gap {top}px is only "
                     f"{ratio:.2f}x the median {med}px (need >= {BOUNDARY_RATIO}) — "
                     f"sections do not detach from the intra-section rhythm")
    else:
        yield False, (f"section separation: biggest gap {top}px = {ratio:.2f}x "
                      f"median {med}px")
    for g in sorted(set(runs), reverse=True):
        if g > BOUNDARY_CEILING * h:
            yield True, (f"canyon: {g}px white run = {g / h * 100:.1f}% of page "
                         f"height (max {BOUNDARY_CEILING * 100:.0f}% even at a "
                         f"section boundary) — take the space out of the "
                         f"intra-section rhythm instead")
        elif g > CANYON * h and g < BOUNDARY_RATIO * med:
            yield True, (f"hole: {g}px white run = {g / h * 100:.1f}% of page "
                         f"height inside a section (max {CANYON * 100:.1f}%; only "
                         f"a section boundary may exceed it)")


# ---------- auto-tuner: the fill loop, run by bisection instead of by hand ----------

# What is being searched, and why a bisection is valid here: raising `leading`
# pushes every line further down, so the last ink row rises monotonically with
# it — until the last unbreakable section no longer fits and the page count
# jumps. The set of leading values that keep the expected page count is
# therefore an interval [lo, L*], and the best fill is at its top end. So:
# bisect for L*, then check the fill it produces.
#
# `spacing` moves WITH `leading`, keeping the family's own delta between the
# two: that delta is part of the recipe (a family with a wide paragraph
# spacing relative to its leading has a different rhythm, not just a different
# density), and tuning them independently would silently redesign the family.
#
# If the fill at L* is still under the target, no leading value reaches it:
# that is the anti-filler clause (SKILL.md rule 5) speaking — the content does
# not honestly fill that pagination. The tuner says so instead of inventing a
# value; the fix is the section gap, real content, or a different page count.

PAR_RE = re.compile(r"(#set\s+par\([^)]*?leading:\s*)([0-9.]+)(em[^)]*?spacing:\s*)([0-9.]+)(em)")


def _read_par(text):
    m = PAR_RE.search(text)
    if not m:
        return None
    return float(m.group(2)), float(m.group(4))


def _write_par(text, leading, spacing):
    return PAR_RE.sub(
        lambda m: "%s%.3f%s%.3f%s" % (m.group(1), leading, m.group(3), spacing,
                                      m.group(5)), text, count=1)


def _probe(typ, text, leading, spacing, expected, use_cli, use_poppler):
    """Compile at (leading, spacing); return (pages_ok, fill_pct or None)."""
    open(typ, "w", encoding="utf-8").write(_write_par(text, leading, spacing))
    with tempfile.TemporaryDirectory() as tmp:
        pdf = os.path.join(tmp, "t.pdf")
        ok, _ = compile_pdf(typ, pdf, use_cli)
        if not ok:
            return False, None
        if count_pages(pdf, use_poppler) != str(expected):
            return False, None
        pngs = render_pngs(typ, tmp, use_cli)
        if not pngs:
            return False, None
        m = re.search(r"to (\d+)%", measure_fill.measure(pngs[-1]))
        return True, (int(m.group(1)) if m else None)


def tune(typ, expected, fmin, fmax, lo=None, hi=None, step=0.005):
    deps_ok, use_cli, use_poppler = preflight()
    if not deps_ok:
        return 1
    original = open(typ, encoding="utf-8").read()
    cur = _read_par(original)
    if cur is None:
        print("FAIL  no `#set par(... leading: Xem, spacing: Yem)` line to tune "
              "— the tuner edits that one declaration and nothing else")
        return 2
    l0, s0 = cur
    delta = s0 - l0                       # the family's own rhythm, preserved
    lo = l0 * 0.80 if lo is None else lo
    # The default ceiling is relative, but a family with an already-tight
    # leading gets a range too narrow to ever reach the fill target, so the
    # ceiling never sits below 1.10em.
    hi = max(l0 * 1.30, 1.10) if hi is None else hi
    print("tuning %s: leading %.3fem (spacing %+.3fem), searching [%.3f, %.3f], "
          "target %s pages / fill %s-%s%%"
          % (typ, l0, delta, lo, hi, expected, fmin, fmax))
    try:
        ok_lo, fill_lo = _probe(typ, original, lo, lo + delta, expected,
                                use_cli, use_poppler)
        if not ok_lo:
            open(typ, "w", encoding="utf-8").write(original)   # undo the probe
            print("FAIL  even the floor leading %.3fem does not give %s page(s) "
                  "— this is a content/section-gap problem, not a rhythm one"
                  % (lo, expected))
            return 1
        best, best_fill = lo, fill_lo
        # The top of the feasible interval is not always the ANSWER: the last
        # value before the page breaks can overshoot fmax (the fill target has
        # a ceiling too — ink is not supposed to reach into the bottom margin).
        # So remember the largest probe that landed INSIDE the target and
        # prefer it over the interval's top end.
        in_target = None
        while hi - lo > step:             # bisect for the top of the interval
            mid = (lo + hi) / 2
            ok, fill = _probe(typ, original, mid, mid + delta, expected,
                              use_cli, use_poppler)
            print("  leading %.3fem -> %s" % (
                mid, ("fill %s%%" % fill) if ok else "page count off"))
            if ok:
                lo, best, best_fill = mid, mid, fill
                if fill is not None and fmin <= fill <= fmax:
                    in_target = (mid, fill)
            else:
                hi = mid
        if in_target and not (best_fill is not None and fmin <= best_fill <= fmax):
            best, best_fill = in_target
        won = best_fill is not None and fmin <= best_fill <= fmax
        if not won:
            # A losing value is worse than no value: it silently replaces a
            # rhythm the family was designed with. Put the original back and
            # let the caller decide.
            open(typ, "w", encoding="utf-8").write(original)
            print("FAIL  best leading %.3fem / spacing %.3fem -> fill %s%% "
                  "(target %s-%s%%); restored the original %.3fem/%.3fem"
                  % (best, best + delta, best_fill, fmin, fmax, l0, s0))
            print("      no leading in the searched range reaches the target at "
                  "%s page(s). Widen the range by passing the bounds "
                  "positionally after FILL_MAX, e.g.\n"
                  "        verify.py --tune %s %s %s %s %.2f %.2f\n"
                  "      or take the space out of the section gap / add real "
                  "content / change the page count (anti-filler clause, "
                  "SKILL.md rule 5)."
                  % (expected, typ, expected, fmin, fmax,
                     max(0.40, l0 * 0.65), max(1.40, l0 * 1.60)))
            return 1
        open(typ, "w", encoding="utf-8").write(
            _write_par(original, best, best + delta))
        print("OK    wrote leading %.3fem / spacing %.3fem -> fill %s%% "
              "(target %s-%s%%)" % (best, best + delta, best_fill, fmin, fmax))
        print("      now run the gate itself: verify.py %s %s %s %s"
              % (typ, expected, fmin, fmax))
        return 0
    except BaseException:
        open(typ, "w", encoding="utf-8").write(original)   # never leave a probe
        raise


# ---------- main gate ----------

def main():
    argv = sys.argv[1:]

    if argv and argv[0] == "--doctor":
        ok, _, _ = preflight()
        sys.exit(0 if ok else 1)

    if argv and argv[0] == "--selftest":
        # The one piece of non-trivial logic here that can break silently: the
        # regex the tuner edits with. A miss makes --tune a no-op that still
        # reports success, so it gets a check.
        src = ('#set page(paper: "us-letter")\n'
               '#set par(justify: false, leading: 0.555em, spacing: 0.615em)\n'
               'body 0.999em\n')
        assert _read_par(src) == (0.555, 0.615), _read_par(src)
        out = _write_par(src, 0.61, 0.7)
        assert "leading: 0.610em, spacing: 0.700em" in out, out
        assert "body 0.999em" in out, "edited past the par declaration"
        assert _read_par(out) == (0.610, 0.700)
        # a file with no par declaration must be reported, never guessed at
        assert _read_par("#set text(size: 10.5pt)\n") is None
        # spacing-before-leading is not the template's order and must not match
        # silently in a way that swaps the two values
        alt = "#set par(spacing: 0.7em, leading: 0.6em)\n"
        assert _read_par(alt) is None, "would write the two values swapped"
        print("selftest OK — tuner regex reads, writes and round-trips; "
              "an unrecognised par declaration is reported, not guessed")
        sys.exit(0)

    if argv and argv[0] == "--tune":
        # verify.py --tune cv.typ PAGES FILL_MIN FILL_MAX [LO HI]
        if len(argv) < 5:
            print("usage: verify.py --tune cv.typ PAGES FILL_MIN FILL_MAX "
                  "[LEADING_LO LEADING_HI]", file=sys.stderr)
            sys.exit(2)
        bounds = (float(argv[5]), float(argv[6])) if len(argv) >= 7 else (None, None)
        sys.exit(tune(argv[1], int(argv[2]), int(argv[3]), int(argv[4]),
                      lo=bounds[0], hi=bounds[1]))

    if len(argv) < 2:
        print(f"usage: {os.path.basename(sys.argv[0])} cv.typ EXPECTED_PAGES [FILL_MIN FILL_MAX]\n"
              f"       {os.path.basename(sys.argv[0])} --tune cv.typ PAGES FILL_MIN FILL_MAX [LO HI]\n"
              f"       {os.path.basename(sys.argv[0])} --doctor\n"
              f"       {os.path.basename(sys.argv[0])} --selftest", file=sys.stderr)
        sys.exit(2)

    typ, expected = argv[0], argv[1]
    fmin = argv[2] if len(argv) >= 3 else None
    fmax = argv[3] if len(argv) >= 4 else None
    pdf = re.sub(r"\.typ$", "", typ) + ".pdf"
    fail = 0

    deps_ok, use_cli, use_poppler = preflight()
    if not deps_ok:
        sys.exit(1)

    ok, err = compile_pdf(typ, pdf, use_cli)
    if not ok:
        print("FAIL  compile")
        print(err)
        sys.exit(1)
    if err.strip():
        print("WARN  compile stderr (a missing font only warns and falls back):")
        print(err)

    pages = count_pages(pdf, use_poppler)
    if pages == expected:
        print(f"OK    pages: {pages}")
    else:
        print(f"FAIL  pages: {pages} (expected {expected})")
        fail = 1

    with tempfile.TemporaryDirectory() as tmp:
        pngs = render_pngs(typ, tmp, use_cli)
        if not pngs:
            # No PNG => measure_fill never ran => the fill target is UNTESTED.
            # Silently passing here is how a broken render reads as a PASS.
            print("FAIL  no PNG rendered — fill unmeasured")
            fail = 1
        for path in pngs:
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
                    print(f"FAIL  fill: {path}: {result} (target {fmin}-{fmax}%)")
                    fail = 1
                else:
                    print(f"OK    fill: {path}: {result}")
            else:
                print(f"INFO  fill: {path}: {result} (target = (100 - bottom-margin%) - 0..2%)")
            for is_fail, msg in check_whitespace(path):
                print(f"{'FAIL' if is_fail else 'OK  '}  {msg}")
                fail = fail or int(is_fail)

    typ_text = open(typ, encoding="utf-8").read()
    if "7d2231" in typ_text.lower():
        print("WARN  template default accent (#7d2231) — run scripts/pick_design.py and apply the family it draws (references/design.md § Design families)")
    if "[#cat:]" in typ_text:
        print("WARN  template skills block (\"Category: items\") — clone marker #2; use the chosen family's skills shape")

    if not use_poppler:
        print("WARN  pypdf extraction is indicative only (spurious spaces inside words, e.g. \"FORMA TION\") — poppler's pdftotext is the reference extractor (references/ats.md)")

    txt = extract_text(pdf, use_poppler)

    def bad(msg):
        """FAIL on the reference extractor, WARN on the pypdf fallback: pypdf's
        extraction is indicative only (this script says so above), so a hard
        FAIL on it would be a verdict the evidence does not support."""
        nonlocal fail
        if use_poppler:
            print("FAIL  " + msg)
            fail = 1
        else:
            print("WARN  " + msg + " — pypdf extraction is indicative; confirm with pdftotext before believing it")

    if not txt.strip():
        bad("extraction empty")
    # ≥4 STANDALONE capitals: the \b anchors keep "B.Sc. C S M Sc" (dotted
    # abbreviations) out. Second pattern catches tracking's real pdftotext
    # shape, which is chunked rather than fully spaced ("S O F T WA RE").
    # Known limit: a space injected INSIDE a word ("FORMA TION") is not
    # detectable here — it is a pypdf extraction artefact, not a layout bug,
    # and only the pypdf path (WARN-only above) produces it.
    spaced = re.search(r"\b(?:[A-Z] ){3,}[A-Z]\b", txt)
    if not spaced:
        for line in txt.split("\n"):
            tok = line.split()
            if (len(tok) >= 4 and all(re.fullmatch(r"[A-Z]{1,2}", t) for t in tok)
                    and sum(len(t) == 1 for t in tok) >= 2):
                spaced = line
                break
    if spaced:
        bad("spaced-out text in extraction (letterspacing/tracking?)")
    # Per PAGE: the orphaned date lands at the end of the page it belongs to,
    # not only at the end of the document.
    for pageno, page in enumerate(txt.split("\f"), 1):
        non_blank = [l for l in page.split("\n") if l.strip()]
        last = non_blank[-1] if non_blank else ""
        if len(last) <= 25 and re.search(r"[0-9]{4}\s*$", last):
            bad(f'orphaned date at end of page {pageno} of the extraction ("{last}") — bullet-less grid entry; see the trap in references/ats.md')
    print("──── extraction (check reading order, orphaned dates, intact skill lines) ────")
    print(txt)

    if fail == 0:
        print("PASS  all mechanical checks — now LOOK at the PNGs")

    sys.exit(fail)


if __name__ == "__main__":
    main()

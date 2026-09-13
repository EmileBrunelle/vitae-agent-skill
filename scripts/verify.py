#!/usr/bin/env python3
"""One-command gate for the MECHANICAL subset of SKILL.md step 6 (any
platform with Python 3 -- Linux, macOS, Windows). Exits non-zero if any
check fails. Left to do by hand: the visual PNG inspection, recomputing
the accent's contrast, the date-order check, and re-diffing bullets
against the fact sheet.

Usage:
    verify.py cv.typ EXPECTED_PAGES [FILL_MIN FILL_MAX]
    verify.py --all DIR
    verify.py --tune cv.typ PAGES FILL_MIN FILL_MAX [LEADING_LO LEADING_HI]
    verify.py --doctor

    e.g. verify.py cv.typ 1 94 96
         verify.py --tune cv.typ 1 94 96

--all checks EVERY deliverable in a directory instead of the one file just
edited. This exists because of a real regression: a padding tweak was verified
on the 2-page CV while it silently pushed the 1-page CV onto two pages
("T'as fait ça en voulant modifier le padding"). The deliverables share
lib.typ, so touching it invalidates the whole family, not the file in hand.

Each .typ declares its own expectations in a header comment, so there is no
manifest to keep in sync with the files:

    // vitae: pages=1 fill=94-96

A file without that line is still checked: its page count comes from its name
(`*-2page.typ` is two pages, anything else is one) and its fill is reported
instead of gated. Not one .typ in this repo carries the header, so demanding
it made `--all` return 30 UNCHECKED and exit 1 on its own corpus.

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

def ensure_icons(typ):
    """Guarantee an `icons.typ` beside the file being compiled.

    `lib.typ` does `#import "icons.typ": *`, and Typst resolves that against
    the importing file, so the deliverable folder needs one. Step 4 of
    SKILL.md copies the repo's EMPTY fallback there along with `lib.typ`, and
    `harvest_icons.py <folder>` overwrites it with the fetched path data. This
    covers the one case those two miss: a folder where the copy was forgotten
    — copy the empty fallback instead of failing the compile with a Typst
    import error. No network here; fetching stays harvest_icons.py's job.
    """
    d = os.path.dirname(os.path.abspath(typ))
    dst = os.path.join(d, "icons.typ")
    if not os.path.exists(dst):        # a broken symlink counts as missing
        src = os.path.join(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__))), "templates", "icons.typ")
        if not os.path.exists(src):    # no repo fallback (nothing to copy)
            return
        shutil.copyfile(src, dst)
        print(f"NOTE  copied the empty fallback icons.typ into {d} — run "
              f"scripts/harvest_icons.py there for the real marks")


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

# BOUNDARY_RATIO is a LOCATOR, not a grade. It answers "is this white run tall
# enough to be a section boundary rather than a line gap", which is all that
# `boundary_ink` and the hole check need from it, and it is the only job the
# number survives.
#
# It used to also FAIL a page whose tallest run fell under it. That is gone,
# measured out on 2026-09-13 over the 30 rendered pages of the 29-deliverable
# corpus, under the CURRENT instrument (see measure_fill.gaps — the sampling
# changed at 42049f6 and nothing downstream was re-measured until now):
#
#   max-gap / median-gap, all 30 pages, sorted:
#     1.89 2.00 2.00 2.12 2.15 2.21 2.27 2.31 2.38 2.40 2.56 2.62 2.73 2.78
#     2.86 2.86 2.90 3.00 3.25 3.29 3.50 3.57 3.60 3.60 3.86 4.00 4.17 5.00
#     5.14 5.14
#
# One continuum, no void anywhere: the widest step in the whole range is 0.83
# (4.17 → 5.00) and the rest are 0.01-0.4. A floor placed in it is a curve
# fitted to the corpus, which is exactly what 2.0 was — it sat one hundredth
# under two deliverables and failed a third at 1.89.
#
# Two further measurements say the statistic is not measuring separation at
# all, so no value would have worked:
#   * A synthetic page whose section gap EQUALS its line gap — no section
#     separation whatsoever — scores 2.69, above 10 of the 30 real pages,
#     which do separate. The ranking is inverted, not merely noisy.
#   * `max` is one run and `median` is a small set of quantized small
#     integers, so the ratio is noise at ±0.3: excluding the header block at
#     8 / 10 / 12 / 15% of the text span moves swiss-grid/resume through
#     1.70, 1.89, 2.00, 1.78 non-monotonically, and the 12% cut stacks five
#     deliverables on exactly 2.00. Taking the mean of the top 5 runs instead
#     of the max smooths it and still yields a continuum (1.64 … 4.91).
# Same conclusion as d7f67da reached for page-wide ink: the number is a
# prefilter, the verdict comes from LOCATION (boundary_ink) — and the white
# ratio is now reported, never failed.
BOUNDARY_RATIO = 2.0
# …and the ceiling, which is a SMOKE ALARM, not a grade either. Whitespace is
# the WEAK separator: piling it on is what an agent does when the boundary does
# not read and it has no device to reach for, and the page that carries no
# device at all AND a gap unlike anything the roster produces is the
# « séparateurs, pas des espaces vides » defect this catches.
# It cannot be calibrated between populations, because there is only one: the
# device-less pages run 2.38 2.56 2.86 2.86 3.29 3.57 3.86 4.00 4.17 5.00,
# continuously, and the roster's highest page of any kind is margin-index at
# 5.14 (a deliberately device-less family, which design.md says legitimately
# owes a HIGH ratio — failing it for that would contradict the rule it serves).
# So the ceiling is placed ABOVE the entire roster and BELOW the no-boundary-
# system pages the selftest draws (6.77 for one lone flourish, 7.92 for none at
# all). 5.0 kept the corpus green only by an exact tie (humanist-quiet/resume
# measures 5.00), which is not a calibration.
SEPARATION_CEILING = 6.0
# …and a device is a REPEATED element: one mark on the page is an ornament,
# typically the flourish under the name. Two families passed the ink check on
# exactly that — `gutter-rail` on its header bar, `engraved-card` on the 56pt
# rule under the name — with nothing at any section boundary below.
# ponytail: a flat count, not a per-boundary tally; a page carrying a single
# section boundary (the tail of a 2-pager) would read as ornament-only. No such
# page exists in the corpus — the thinnest is page 2 of swiss-grid's 2-pager
# with 5 — so a per-boundary pairing is not worth its code yet.
DEVICE_QUORUM = 2
CANYON = 0.035          # a hole this tall (fraction of page height) is a defect
BOUNDARY_CEILING = 0.05  # …unless it is a section boundary, which may run this tall


def boundary_ink(white, ink, med):
    """The ink bands that sit AT a section boundary, not just anywhere.

    "Longest dark run on the page" cannot tell a rule from an underline: a
    `#show link: underline` on the contact line scores 21.8% of page width and
    a two-column table rule 86.4%, both wider than three of the corpus's real
    devices, while those devices sit at 5.65-7.61%. The clusters overlap
    INVERTED, so no threshold can separate them. Location can: there is no text
    inside a boundary, so ink found there is furniture by construction.

    A device at a boundary shows up four ways, all covered by the same sum:
    it caps the gap (white above it, text below), it sits under the gap, it
    SPLITS the gap in two, or it lies WHOLLY INSIDE it — the last one because
    the two scans read different thresholds: `keyline-corporate`'s 0.6pt `soft`
    hairline is too pale to count as dark for the white scan, so its rows stay
    inside the white run while still spanning 100% of the measure. So walk out
    from the band through whatever white touches or contains it, and ask whether
    that span reads as a boundary by the BOUNDARY_RATIO the white scan already
    uses. A thick band clears it on its own thickness, which is right: a
    knockout slab IS the boundary.
    """
    def span(a, b):
        up = next((a - x for x, y in white if x <= a <= y), 0)
        dn = next((y - b for x, y in white if x <= b <= y), 0)
        return up + (b - a) + dn

    return [(a, b) for a, b in ink if span(a, b) >= BOUNDARY_RATIO * med]


def check_whitespace(path):
    """Yield (is_fail, message) for one rendered page."""
    import statistics
    h, white, all_ink = measure_fill.bands(path)
    runs = [b - a for a, b in white]
    if len(runs) < 6:
        return                              # not a text page: nothing to judge
    med = statistics.median(runs)
    top = max(runs)
    if med <= 0:
        return
    ratio = top / med
    ink = boundary_ink(white, all_ink, med)
    if ratio < BOUNDARY_RATIO:
        yield False, (f"section separation: biggest internal gap {top}px is "
                      f"{ratio:.2f}x the median {med}px — under the "
                      f"{BOUNDARY_RATIO}x a boundary is located by, so the ink "
                      f"check below may see fewer devices than the page "
                      f"carries. REPORTED, NOT FAILED: the ratio does not rank "
                      f"separation (see BOUNDARY_RATIO). Look at the page")
    # The half of the invariant the white scan alone could never check. A
    # boundary is supposed to carry INK by default (design.md § Invariants);
    # with no device AT A BOUNDARY, whitespace is the whole separator,
    # and a WIDE boundary on top of that is the failure this gate exists to
    # catch: separators are wanted, not empty space.
    if len(ink) < DEVICE_QUORUM:
        yield ratio > SEPARATION_CEILING, (
            f"boundaries carry no ink: {len(ink)} rule/bar/slab AT a section "
            f"boundary, need {DEVICE_QUORUM} ({len(all_ink)} wide dark run(s) "
            f"on the page — an underline, a table rule or a single flourish "
            f"under the name is not a boundary system)"
            + (f", and the boundary gap is {ratio:.2f}x the median — empty "
               f"space is doing the whole job. Add the family's device, or a "
               f"thin `soft` hairline above each section, and give the gap "
               f"back to body leading"
               if ratio > SEPARATION_CEILING else
               " — legitimate only for a deliberately device-less family, "
               "which then needs a HIGH white ratio to compensate"))
    else:
        yield False, (f"boundary devices: {len(ink)} ink band(s) at a section "
                      f"boundary, of {len(all_ink)} on the page "
                      f"({', '.join(str(b - a) + 'px' for a, b in ink[:6])})")
    if ratio > SEPARATION_CEILING:
        yield False, (f"section separation: biggest gap {top}px = {ratio:.2f}x "
                      f"median {med}px — OVER {SEPARATION_CEILING}x. Legitimate "
                      f"only for a device-less family (whitespace is then the "
                      f"whole boundary). If the boundary carries ink, the gap is "
                      f"compensating for nothing: cut it and give the space back "
                      f"to body leading")
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

HEADER_RE = re.compile(r"^//\s*vitae:\s*pages=(\d+)(?:\s+fill=(\d+)-(\d+))?",
                       re.M)


def pages_from_name(typ):
    """The page count a headerless deliverable declares in its own file name."""
    return "2" if re.search(r"-2\s*page", os.path.basename(typ), re.I) else "1"


def check_all(directory):
    """Run the single-file gate over every .typ under `directory`.

    Re-invokes this script per file rather than refactoring main() apart: the
    point is that each deliverable gets EXACTLY the check it would get alone,
    and a subprocess guarantees that for free.
    """
    typs = sorted(f for f in glob.glob(os.path.join(directory, "**", "*.typ"),
                                       recursive=True)
                  if not os.path.basename(f).startswith(("lib", "icons")))
    if not typs:
        print(f"no .typ found under {directory}")
        return 1
    fail, unchecked = 0, []
    for typ in typs:
        with open(typ, encoding="utf-8") as fh:
            m = HEADER_RE.search(fh.read(4096))
        if m:
            args = [m.group(1)] + ([m.group(2), m.group(3)] if m.group(2) else [])
        else:
            # No header: take the page count from the FILE NAME, which is the
            # one expectation this repo already states out loud — `*-2page.typ`
            # is two pages, every other deliverable is one (SKILL.md step 4,
            # and the reference sweep in the read-me is written exactly that
            # way). This is the smallest thing that makes --all useful: not one
            # of the repo's own 30 .typ files carries the header, so the
            # command returned 30 UNCHECKED and exit 1 on the very corpus it
            # exists to guard. Fill stays undeclared and is reported, not
            # failed — a page count is inferable from a name, a fill target is
            # not, and inventing one would be the fitted-curve mistake again.
            # Add the header to a deliverable whose fill matters; it wins.
            args = [pages_from_name(typ)]
            unchecked.append(typ)
        print(f"\n=== {typ}  (expects {' '.join(args)}"
              f"{'' if m else ' — inferred from the file name, no header'})")
        r = subprocess.run([sys.executable, os.path.abspath(__file__), typ]
                           + args)
        fail |= bool(r.returncode)
    if unchecked:
        print(f"\nNOTE — page count inferred from the file name, fill not "
              f"checked (add `// vitae: pages=N fill=A-B` to pin either):")
        for t in unchecked:
            print(f"  {t}")
    print("\n" + ("FAIL — see above" if fail else
                  f"PASS — {len(typs)} deliverable(s), "
                  f"all siblings checked together"))
    return fail


def main():
    argv = sys.argv[1:]

    if argv and argv[0] == "--all":
        if len(argv) < 2:
            sys.exit("usage: verify.py --all DIR")
        sys.exit(check_all(argv[1]))
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
        # --all's headerless fallback: the page count read off the name. Wrong
        # here and every 2-page deliverable is silently gated as a 1-pager.
        assert pages_from_name("a/resume-2page.typ") == "2"
        assert pages_from_name("a/resume.typ") == "1"
        assert pages_from_name("a/resume-pair-b.typ") == "1"
        assert pages_from_name("a/CV-2 page.typ") == "2"  # a space still counts
        assert pages_from_name("2page/resume.typ") == "1", "directory, not file"
        # The other piece that can break silently: the ink-band detector. If
        # it stopped seeing devices, every CV would pass the "carries ink"
        # check by accident, which is the exact rule that kept regressing.
        # Two synthetic pages, drawn with PIL so the check needs no Typst.
        from PIL import Image, ImageDraw

        def _page(rule_luma=None, gap=45, rule_len=975, underline=False, rules=4):
            im = Image.new("L", (1275, 1650), 255)
            d = ImageDraw.Draw(im)
            y = 200
            for s in range(4):
                if rule_luma is not None and s < rules:  # a hairline AT the boundary
                    d.line([(150, y), (150 + rule_len, y)], fill=rule_luma, width=2)
                y += gap                        # …or nothing but empty space
                for i in range(6):              # body text: short dark runs
                    for x in range(150, 1100, 60):
                        d.rectangle([x, y, x + 44, y + 8], fill=30)
                    y += 22
                    if underline and s == 1 and i == 2:
                        # an underlined link mid-section: a 24%-of-width
                        # unbroken run, wider than any real device on the
                        # roster, but nowhere near a boundary
                        d.line([(150, y - 6), (450, y - 6)], fill=30, width=2)
            f = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
            im.save(f.name)
            return f.name

        # inked: a tight page whose boundaries are pale full-measure hairlines.
        # thin: the same, with a device deliberately SHORTER than the text
        # column (5.5% of page width — `quiet-luxury`'s tick is 5.65%); it must
        # still pass, which is what breaks if RULE_FLOOR is raised back to 0.08.
        # linked: the false positive the old page-wide scan could not see — no
        # device at all, but an underlined link supplying a wide dark run. bare:
        # the same defect without even that.
        inked, bare = _page(rule_luma=180), _page(rule_luma=None, gap=90)
        # gap=75 puts this page's white ratio OVER SEPARATION_CEILING, so it
        # passes only while the short rule is seen: miss the device and the
        # same page is the "empty space is doing the whole job" failure.
        thin = _page(rule_luma=30, rule_len=70, gap=75)
        linked = _page(rule_luma=None, gap=90, underline=True)
        # one rule at the top and nothing below it: the `engraved-card` /
        # `gutter-rail` case, a flourish under the name and bare space after
        lone = _page(rule_luma=30, gap=75, rules=1)
        assert measure_fill.bands(inked)[2], "a pale hairline must read as ink"
        assert not measure_fill.bands(bare)[2], "body text must not read as ink"
        assert measure_fill.bands(linked)[2], \
            "the underline must register as a wide dark run (else the next " \
            "assert passes for the wrong reason)"
        for p in (inked, thin):
            msgs = list(check_whitespace(p))
            assert not any(f for f, _ in msgs), \
                "a page whose boundaries carry a hairline must not FAIL"
            # …and POSITIVELY, that the device was seen. Asserting only "does
            # not FAIL" stopped proving that once SEPARATION_CEILING rose
            # above `thin`'s 5.62x ratio: miss the short rule and the page
            # merely reports "carries no ink" and still passes. This is the
            # assertion RULE_FLOOR = 0.08 has to break (a 5.5%-of-width rule
            # falls under an 8% floor), and the ceiling can no longer stand in
            # for it.
            assert any("boundary devices:" in m for _, m in msgs), \
                "a pale or short hairline AT a boundary must be COUNTED as a " \
                "device, not merely fail to trigger a failure"
        for p in (bare, linked, lone):
            assert any(f and "no ink" in m for f, m in check_whitespace(p)), \
                "empty-space-only separation must FAIL on the ink check, " \
                "whatever ink the page carries away from its boundaries"
        # --- the 2026-09-13 recalibration, pinned from both sides ---
        # tight: boundaries carry a hairline but the gap is only 1.77x the
        # median — BELOW the old 2.0 floor, which failed it. The corpus says
        # that ratio does not rank separation (a page with NO section gap at
        # all scores 2.69), so an inked page must pass at any ratio. This is
        # the `engraved-card/resume-pair-b` case, which measured 1.89.
        tight = _page(rule_luma=30, gap=10)
        assert not any(f for f, _ in check_whitespace(tight)), \
            "the white ratio must no longer FAIL a page whose boundaries " \
            "carry ink, however tight the gap"
        # airy: no device anywhere and a ratio of ~5.1 — the top of the real
        # roster (margin-index 5.14, a legitimately device-less family). It
        # must NOT fail: SEPARATION_CEILING sits above the whole corpus, and
        # dropping it back under 5.2 turns this into a failure.
        airy = _page(rule_luma=None, gap=53)
        assert not any(f for f, _ in check_whitespace(airy)), \
            "SEPARATION_CEILING must sit above the roster's highest page " \
            f"(5.14x); at {SEPARATION_CEILING} a device-less family that " \
            "compensates with white — which design.md requires of it — fails"
        for f in (inked, bare, thin, linked, lone, tight, airy):
            os.unlink(f)
        print("selftest OK — tuner regex reads, writes and round-trips; "
              "an unrecognised par declaration is reported, not guessed; "
              "a pale or short hairline AT a boundary reads as a device, while "
              "an underlined link away from one does not — empty-space-only "
              "separation FAILs either way; and the white ratio fails nothing "
              "on its own, at either end (tight-but-inked passes, and the "
              "ceiling clears the roster's highest page)")
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
              f"       {os.path.basename(sys.argv[0])} --all DIR\n"
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

    ensure_icons(typ)
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

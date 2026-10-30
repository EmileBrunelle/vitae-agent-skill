#!/usr/bin/env bash
# Run every check the repo has: self-tests, the 29 templates against their fill
# targets, the spacing fixtures and their gates. Keeps going after a failure.
# Usage: tests/run_all.sh [--quick] [outdir]
# Needs typst, poppler-utils (pdftotext) or pypdfium2, python3 + Pillow + pypdf.
# Works on a scratch copy: verify.py writes PDFs next to the .typ, and the
# repo must stay clean. PDFs/PNGs of the templates are left in <outdir>/pdf.
set -euo pipefail

quick=0; out=""
for a in "$@"; do
  case "$a" in
    --quick) quick=1 ;;
    -h|--help) sed -n 2,7p "$0"; exit 0 ;;
    *) out="$a" ;;
  esac
done
root="$(cd "$(dirname "$0")/.." && pwd)"
[ -n "$out" ] || out="$(mktemp -d)"
mkdir -p "$out"; out="$(cd "$out" && pwd)"
S="$out/work"; rm -rf "$S"; mkdir -p "$S" "$out/pdf" "$out/log"
start=$(date +%s); fails=0; total=0

# Scratch copy; cp -L turns the families' lib.typ symlinks into real files.
cp -rL "$root/templates" "$root/scripts" "$root/references" "$S"/
mkdir -p "$S/tests"; cp -rL "$root/tests/fixtures" "$root/tests/compare_backends.py" "$root/tests/test_look.py" "$S/tests/"
[ -f "$root/SKILL.md" ] && cp "$root/SKILL.md" "$S"/ || true
cd "$S"

# check <name> <cmd...>: log to $out/log/<name>.log, one PASS/FAIL line.
check() {
  local name="$1"; shift
  local log="$out/log/${name//\//_}.log" rc=0
  total=$((total + 1))
  "$@" >"$log" 2>&1 || rc=$?
  # verify.py's verdict is its last line; a run is only a PASS if it says so.
  if [ "$rc" -eq 0 ] && ! grep -q '^FAIL' "$log"; then
    echo "PASS $name"
  else
    echo "FAIL $name (exit $rc; see $log)"; tail -3 "$log" | sed 's/^/     /'
    fails=$((fails + 1))
  fi
}

# SKILL.md gates (v0.7 context diet). Run on the scratch copy; $1 = mode, $2 = root.
#  size:  SKILL.md must stay <= 13000 bytes.
#  steps: every steps file is cited (no orphans), starts with "# ", ends on punctuation/fence/list/table.
#  links: every references|scripts|templates path cited in SKILL.md and in the
#         step/academic/known-traps files must exist (paths with "<" are placeholders).
GATE_PY='
import os, re, sys, glob
mode, root = sys.argv[1], sys.argv[2]
LIMIT = 13000
skill = os.path.join(root, "SKILL.md")
if mode == "size":
    n = os.path.getsize(skill)
    if n > LIMIT:
        print(f"FAIL SKILL.md is {n} bytes, limit is {LIMIT} ({n - LIMIT} over)"); sys.exit(1)
    print(f"ok SKILL.md {n} bytes <= {LIMIT}"); sys.exit(0)
steps = sorted(glob.glob(os.path.join(root, "references/steps/*.md")))
if mode == "steps":
    bad = []
    texts = {f: open(f, encoding="utf-8").read() for f in [skill] + steps}
    for f in steps:
        b = os.path.basename(f)
        if not any(b in t for g, t in texts.items() if g != f):
            bad.append(f"FAIL orphan {b}: cited by neither SKILL.md nor another steps file")
        lines = [l for l in texts[f].split("\n") if l.strip()]
        if not lines or not lines[0].startswith("# "):
            bad.append(f"FAIL {b}: does not start with an H1 (\"# \")")
        elif not re.search(r"[.!?:;)\]`|*\"\u201d\u00bb>]$", lines[-1].rstrip()):
            bad.append(f"FAIL {b}: last line does not end like a sentence: ...{lines[-1].rstrip()[-40:]!r}")
    for m in bad: print(m)
    if bad: sys.exit(1)
    print(f"ok {len(steps)} steps files: none orphaned, all start with H1 and end cleanly"); sys.exit(0)
srcs = [skill] + sorted(glob.glob(os.path.join(root, "references/steps/*.md")))
srcs += [os.path.join(root, "references", f) for f in ("academic-mode.md", "known-traps.md")]
pat = re.compile(r"(?:references|scripts|templates)/[A-Za-z0-9_./<>-]+")
bad = []; seen = 0
for f in srcs:
    if not os.path.isfile(f): continue
    for m in pat.finditer(open(f, encoding="utf-8").read()):
        p = m.group(0).rstrip(".,;:`\x27)")
        if "<" in p or ">" in p: continue
        seen += 1
        full = os.path.join(root, p)
        ok = os.path.isdir(full) if p.endswith("/") else os.path.exists(full)
        if not ok: bad.append((p, os.path.relpath(f, root)))
for p, f in sorted(set(bad)): print(f"FAIL missing {p} (cited in {f})")
if bad: sys.exit(1)
print(f"ok {seen} path citations resolve")
'
[ -f SKILL.md ] && check skill-size python3 -I -c "$GATE_PY" size "$S" \
  && check skill-links python3 -I -c "$GATE_PY" links "$S" \
  && check skill-steps python3 -I -c "$GATE_PY" steps "$S" || true

check selftest-verify python3 -I scripts/verify.py --selftest
check selftest-pick_design python3 -I scripts/pick_design.py --selftest

# --doctor degraded paths, simulated with a PATH of symlinks (and shims). Each
# case asserts the DEGRADED label AND at least one named skipped check.
# verify.py imports Pillow at load, so without it the doctor cannot run: SKIP.
if python3 -c "import PIL" 2>/dev/null; then
# The interpreter is run by its own path: a `python3` symlink in the stripped PATH resolves
# out of a venv and loses its site-packages (typst, pypdfium2, Pillow).
PY="$(python3 -c 'import sys; print(sys.executable)')"
doctor_env() { # doctor_env <dir> <tools...>: symlink the host tools into <dir>/bin
  local d="$1"; shift; rm -rf "$d"; mkdir -p "$d/bin" "$d/py"
  local t; for t in "$@"; do ln -s "$(command -v "$t")" "$d/bin/$t"; done
}
shim_typst() { # shim_typst <dir> <families...>: fake `typst` (version $SHIM_VER, default 0.15.0) that lists only those families
  local d="$1"; shift
  { printf '#!/bin/sh\n[ "$1" = fonts ] && { '; for f in "$@"; do printf 'echo "%s"; ' "$f"; done; printf 'exit 0; }\necho "typst %s"\n' "${SHIM_VER:-0.15.0}"; } > "$d/bin/typst"
  chmod +x "$d/bin/typst"
}

# Fake `typst` Python modules (PYTHONPATH stub), by how much of the API works.
stub_typst() { # stub_typst <file> <kind>: broken | compile-only | working
  case "$2" in
    broken) : > "$1" ;;      # imports, has no Compiler: a broken install
    compile-only) printf 'class Compiler:\n    def __init__(self, *a, **k): pass\n    def compile_with_warnings(self, **k): return (b"%%PDF-1", [])\n__version__ = "9.9.9"\n' > "$1" ;;
    working) printf 'class Compiler:\n    def __init__(self, *a, **k): pass\n    def compile_with_warnings(self, **k): return (b"%%PDF-1", [])\n    def query(self, *a, **k): return "[]"\n    def eval(self, e, **k): return "\\"9.9.9\\""\nclass Fonts:\n    def __init__(self, *a, **k): pass\n    def families(self): return ["DejaVu Sans"]\n__version__ = "9.9.9"\n' > "$1" ;;
  esac
}

# no typst/poppler CLIs, and the `typst` module imports but does not work: BROKEN (exit 1),
# not a silent "Python API available" (an attribute check would have passed it).
doctor_pip_broken() {
  local d="$out/doctor-sim"; doctor_env "$d" python3; stub_typst "$d/py/typst.py" broken
  local txt rc=0
  txt="$(PATH="$d/bin" PYTHONPATH="$d/py" "$PY" scripts/verify.py --doctor 2>&1)" || rc=$?
  echo "$txt"
  [ "$rc" -eq 1 ] || { echo "doctor exit $rc, expected 1"; return 1; }
  echo "$txt" | grep -q '^BROKEN  typst' || { echo "no BROKEN typst line"; return 1; }
  echo "$txt" | grep -q '^OK    typst' && { echo "typst reported OK"; return 1; }
  return 0
}
check doctor-pip-broken doctor_pip_broken

# imports and runs, but its Compiler lacks compile_with_warnings (typst-py 0.11.x): "too old", not "reinstall".
doctor_pip_too_old() {
  local d="$out/doctor-sim-too-old"; doctor_env "$d" python3
  printf 'class Compiler:\n    def __init__(self, *a, **k): pass\n    def compile(self, **k): return b"%%PDF-1"\n__version__ = "0.11.1"\n' > "$d/py/typst.py"
  local txt rc=0
  txt="$(PATH="$d/bin" PYTHONPATH="$d/py" "$PY" scripts/verify.py --doctor 2>&1)" || rc=$?
  echo "$txt"
  [ "$rc" -eq 1 ] || { echo "doctor exit $rc, expected 1"; return 1; }
  echo "$txt" | grep -q '^BROKEN  typst.*too old' || { echo "no too-old line"; return 1; }
  echo "$txt" | grep -q 'pip install -U typst' || { echo "no upgrade advice"; return 1; }
  echo "$txt" | grep -q 'force-reinstall' && { echo "advises reinstall for an old wheel"; return 1; }
  return 0
}
check doctor-pip-too-old doctor_pip_too_old

# compiles but has no query/eval/Fonts (old typst-py): DEGRADED, and names the skipped checks.
doctor_pip_compile_only() {
  local d="$out/doctor-sim-c"; doctor_env "$d" python3; stub_typst "$d/py/typst.py" compile-only
  local txt rc=0
  txt="$(PATH="$d/bin" PYTHONPATH="$d/py" "$PY" scripts/verify.py --doctor 2>&1)" || rc=$?
  echo "$txt"
  [ "$rc" -eq 0 ] || { echo "doctor exit $rc, expected 0"; return 1; }
  echo "$txt" | grep -q '^DEGRADED  typst' || { echo "no DEGRADED typst line"; return 1; }
  echo "$txt" | grep -q 'date adjacency' || { echo "typst block names no skipped check"; return 1; }
  echo "$txt" | grep -q '^OK    typst' && { echo "typst reported OK"; return 1; }
  # pypdf may be absent on the host; with pypdfium2 present the backend is pdfium, not DEGRADED
  if python3 -c "import pypdf" 2>/dev/null && ! python3 -c "import pypdfium2" 2>/dev/null; then
    echo "$txt" | grep -q '^DEGRADED  pypdf' || { echo "no DEGRADED pypdf line"; return 1; }
    echo "$txt" | grep -q 'hidden-text gate' || { echo "pypdf block names no skipped check"; return 1; }
  fi
  return 0
}
check doctor-pip-compile-only doctor_pip_compile_only

# the stub works end to end (compile, query, eval, Fonts): typst is OK and names no skipped check.
doctor_pip_query() {
  local d="$out/doctor-sim-q"; doctor_env "$d" python3; stub_typst "$d/py/typst.py" working
  local txt; txt="$(PATH="$d/bin" PYTHONPATH="$d/py" "$PY" scripts/verify.py --doctor 2>&1)" || true
  echo "$txt" | grep -q '^OK    typst 9.9.9 (Python API: compile, query, fonts)' || { echo "$txt"; echo "no OK typst Python API line"; return 1; }
  echo "$txt" | grep -q '^DEGRADED  typst' && { echo "typst still DEGRADED"; return 1; }
  return 0
}
check doctor-pip-query doctor_pip_query

# typst older than 0.15 (CLI shim, then the Python stub): DEGRADED with the calibration reason.
doctor_old_typst() {
  local d="$out/doctor-sim-old"; doctor_env "$d" python3; SHIM_VER=0.14.0 shim_typst "$d" "DejaVu Sans"
  local txt; txt="$(PATH="$d/bin" "$PY" scripts/verify.py --doctor 2>&1)" || true
  echo "$txt"
  echo "$txt" | grep -q '^DEGRADED  typst 0.14.0 (CLI): fill targets are calibrated on typst 0.15' || { echo "no DEGRADED old CLI line"; return 1; }
  rm "$d/bin/typst"; stub_typst "$d/py/typst.py" working; sed -i 's/9\.9\.9/0.14.2/' "$d/py/typst.py"
  txt="$(PATH="$d/bin" PYTHONPATH="$d/py" "$PY" scripts/verify.py --doctor 2>&1)" || true
  echo "$txt"
  echo "$txt" | grep -q '^DEGRADED  typst 0.14.2 (Python API): fill targets are calibrated on typst 0.15' || { echo "no DEGRADED old Python line"; return 1; }
  echo "$txt" | grep -q 'apt install typst' && { echo "advises apt install typst"; return 1; }
  echo "$txt" | grep -q '^OK (Python)' && { echo "OK (Python) with an old typst"; return 1; }
  return 0
}
check doctor-old-typst doctor_old_typst

# the real pip-only environment: typst-py + pypdfium2 + Pillow, no typst CLI, no poppler.
# Needs them importable from "$PY" (a venv); SKIP on a bare host Python.
if "$PY" -c "import typst, pypdfium2" 2>/dev/null; then
  doctor_pip_full() {
    local d="$out/doctor-sim-full"; doctor_env "$d" python3
    local txt rc=0; txt="$(PATH="$d/bin" "$PY" scripts/verify.py --doctor 2>&1)" || rc=$?
    echo "$txt"
    [ "$rc" -eq 0 ] || { echo "doctor exit $rc, expected 0"; return 1; }
    echo "$txt" | grep -q '^OK    typst .* (Python API: compile, query, fonts)' || { echo "no OK typst Python API line"; return 1; }
    echo "$txt" | grep -q '^OK    pdf: pypdfium2' || { echo "no OK pypdfium2 line"; return 1; }
    echo "$txt" | grep -q '^OK (Python)' || { echo "no OK (Python) line"; return 1; }
    echo "$txt" | grep -q '^DEGRADED\|^MISSING\|^BROKEN' && { echo "unexpected DEGRADED/MISSING/BROKEN"; return 1; }
    echo "$txt" | grep -q -- '--font-path' && { echo "advises --font-path with no CLI"; return 1; }
    return 0
  }
  check doctor-pip-full doctor_pip_full
  # same environment without pypdf: OK (Python) must not hide the skipped tiny-text check
  if "$PY" -c "import pypdf" 2>/dev/null; then
    doctor_no_pypdf() {
      local d="$out/doctor-sim-nopypdf" txt rc=0; doctor_env "$d" python3
      txt="$(PATH="$d/bin" "$PY" -c "
import sys, runpy
sys.modules['pypdf'] = None
sys.argv = ['verify.py', '--doctor']
runpy.run_path('scripts/verify.py', run_name='__main__')" 2>&1)" || rc=$?
      echo "$txt"
      [ "$rc" -eq 0 ] || { echo "doctor exit $rc, expected 0"; return 1; }
      # the line names what the gate really skips on this backend (pdfium: tiny-text; poppler: off-page)
      if echo "$txt" | grep -q '^OK    pdf: pypdfium2'; then want='tiny-text'; else want='off-page'; fi
      echo "$txt" | grep -q "^DEGRADED  pypdf: not installed.*$want.*pip install pypdf" || { echo "no DEGRADED pypdf line naming $want"; return 1; }
      echo "$txt" | grep -q '^OK (Python)' && { echo "OK (Python) hides the missing pypdf"; return 1; }
      return 0
    }
    check doctor-no-pypdf doctor_no_pypdf
  fi
  # any DEGRADED line (here: fonts) withholds the OK (Python) summary
  doctor_degraded_no_ok() {
    local d="$out/doctor-sim-degfonts" txt rc=0; doctor_env "$d" python3
    txt="$(PATH="$d/bin" "$PY" -c "
import sys; sys.path.insert(0, 'scripts')
import verify, pick_design
pick_design._fonts_available = lambda: {'DejaVu Sans'}
verify.preflight()" 2>&1)" || rc=$?
    echo "$txt"
    echo "$txt" | grep -q '^DEGRADED  fonts' || { echo "no DEGRADED fonts line"; return 1; }
    echo "$txt" | grep -q '^OK (Python)' && { echo "OK (Python) after a DEGRADED line"; return 1; }
    return 0
  }
  check doctor-degraded-no-ok doctor_degraded_no_ok
else
  echo "SKIP doctor-pip-full (needs typst-py and pypdfium2 in $PY)"
fi

# pdfinfo + pdftotext but no pdftoppm: the poppler line is DEGRADED.
if command -v typst >/dev/null && command -v pdfinfo >/dev/null && command -v pdftotext >/dev/null; then
  doctor_no_pdftoppm() {
    local d="$out/doctor-sim2"; doctor_env "$d" python3 typst pdfinfo pdftotext
    local txt; txt="$(PATH="$d/bin" "$PY" scripts/verify.py --doctor 2>&1)" || { echo "$txt"; return 1; }
    echo "$txt"
    echo "$txt" | grep -q '^DEGRADED  poppler-utils' || { echo "no DEGRADED poppler line"; return 1; }
    echo "$txt" | grep -q 'hidden-text ink check' || { echo "no skipped check named"; return 1; }
  }
  check doctor-no-pdftoppm doctor_no_pdftoppm
else
  echo "SKIP doctor-no-pdftoppm (needs typst, pdfinfo, pdftotext on the host)"
fi

# no poppler on PATH, pypdfium2 importable: every poppler check runs on pdfium (OK line, no
# DEGRADED), and the doctor says academic mode still needs poppler.
if command -v typst >/dev/null && "$PY" -c "import pypdfium2" 2>/dev/null; then
  doctor_pdfium() {
    local d="$out/doctor-sim5"; doctor_env "$d" python3 typst
    local txt; txt="$(PATH="$d/bin" "$PY" scripts/verify.py --doctor 2>&1)" || { echo "$txt"; return 1; }
    echo "$txt"
    echo "$txt" | grep -q '^OK    pdf: pypdfium2 .* (Python: text, word boxes, raster, metadata, attachments)' || { echo "no OK pypdfium2 line"; return 1; }
    echo "$txt" | grep -q 'academic mode still needs poppler' || { echo "no academic-mode line"; return 1; }
    echo "$txt" | grep -q '^DEGRADED  pypdf\|^MISSING' && { echo "unexpected DEGRADED/MISSING"; return 1; }
    return 0
  }
  check doctor-pdfium doctor_pdfium
else
  echo "SKIP doctor-pdfium (needs typst and pypdfium2 on the host)"
fi

# typst CLI whose font list has only DejaVu: fonts line DEGRADED; with a font
# list covering >= MIN_POOL design families (every font pick_design knows): no
# DEGRADED line at all.
doctor_minimal_fonts() {
  local d="$out/doctor-sim3"; doctor_env "$d" python3; shim_typst "$d" "DejaVu Sans" "DejaVu Sans Mono"
  local txt; txt="$(PATH="$d/bin" "$PY" scripts/verify.py --doctor 2>&1)" || true
  echo "$txt"
  echo "$txt" | grep -q '^DEGRADED  fonts' || { echo "no DEGRADED fonts line"; return 1; }
  echo "$txt" | grep -q 'pick_design' || { echo "fonts block names no consequence"; return 1; }
}
check doctor-minimal-fonts doctor_minimal_fonts

doctor_full_fonts() {
  local d="$out/doctor-sim4"; doctor_env "$d" python3
  local fams; mapfile -t fams < <(python3 -I -c "
import sys; sys.path.insert(0, 'scripts'); import pick_design as p
for fp in p.FONTS.values():
    for role in ('display', 'body', 'mono'):
        for f in fp.get(role, []): print(f[0])" | sort -u)
  shim_typst "$d" "${fams[@]}"
  local txt; txt="$(PATH="$d/bin" "$PY" scripts/verify.py --doctor 2>&1)" || true
  echo "$txt"
  echo "$txt" | grep -q '^OK    fonts' || { echo "expected OK fonts line"; return 1; }
  echo "$txt" | grep -q '^DEGRADED  fonts' && { echo "unexpected DEGRADED fonts"; return 1; }
  return 0
}
check doctor-full-fonts doctor_full_fonts
else
  echo "SKIP doctor-* cases (Pillow not installed)"
fi

# Type check (config: mypy.ini). Optional locally: SKIP, not FAIL, without mypy.
if python3 -c "import mypy" 2>/dev/null; then
  cp "$root/mypy.ini" "$S"/
  check mypy python3 -m mypy
else
  echo "SKIP mypy (not installed: pip install mypy)"
fi

# Template targets come from pick_design.FAMILIES[f]['page']['fill'] ("A-B").
targets="$(python3 -I -c "
import sys; sys.path.insert(0, 'scripts'); import pick_design as p
for f in sorted(p.FAMILIES):
    print(f, p.FAMILIES[f]['page']['fill'].replace('-', ' '))")"

n=0
tpl() { # tpl <family> <file> <pages> <min> <max>
  local f="$1" t="$2" src
  src="templates/families/$f/$t.typ"
  check "template/$f/$t" python3 -I scripts/verify.py "$src" "$3" "$4" "$5"
  cp -f "templates/families/$f/$t.pdf" "$out/pdf/$f-$t.pdf" 2>/dev/null || true
  pdftoppm -r 60 -png -singlefile "templates/families/$f/$t.pdf" "$out/pdf/$f-$t" 2>/dev/null || true
}
while read -r f a b; do
  [ -n "$f" ] || continue
  for t in resume resume-pair-b; do
    n=$((n + 1))
    if [ "$quick" -eq 1 ] && [ "$n" -gt 3 ]; then break 2; fi
    tpl "$f" "$t" 1 "$a" "$b"
  done
done <<< "$targets"
if [ "$quick" -eq 0 ]; then tpl swiss-grid resume-2page 2 94 96; fi

# Drawn fill target (cv.typ header). pick_design --init writes it as line 1;
# verify.py then reads it, and lowered FILL_MIN args are a loud WARN (exit 0),
# never silent. The worked file stands in for the starter, whose filler may not fill.
drawn_header() {
  python3 -I scripts/pick_design.py --name "Jane Roe" --field accounting --market ca --init "$S/drawn" --no-font-check >/dev/null 2>&1 || return 1
  head -1 "$S/drawn/cv.typ" | grep -Eq '^// vitae: pages=1 fill=[0-9]+-[0-9]+$' || { echo "no header on line 1"; return 1; }
}
check drawn-header drawn_header
lowered_fill() {
  local f a b d
  read -r f a b <<< "$(echo "$targets" | head -1)"
  d="templates/families/$f"
  { printf '// vitae: pages=1 fill=%s-%s\n' "$a" "$b"; cat "$d/resume.typ"; } > "$d/_drawn.typ"
  python3 -I scripts/verify.py "$d/_drawn.typ" 1 "$a" "$b" | grep -q '^PASS ' || { echo "header target did not pass"; return 1; }
  local lo=$((a - 6)) log; log="$(mktemp)"
  python3 -I scripts/verify.py "$d/_drawn.typ" 1 "$lo" 100 >"$log" || { echo "exit non-zero"; cat "$log"; return 1; }
  grep -q '^WARN  fill target lowered below drawn target' "$log" || { echo "no WARN"; return 1; }
  grep -q '^PASS (fill target lowered: ' "$log" || { echo "no PASS summary"; return 1; }
}
check lowered-fill-warns lowered_fill

# --facts: a month range shares its year ("juillet – août 2019" covers "Jul 2019"); an invented month still WARNs.
# --text / --render: the interface the step docs promise, whatever backend is installed.
facts_month_range() {
  python3 -I - <<'PY' || return 1
import sys; sys.path.insert(0, "scripts")
import verify
f = "Stage, Acme, juillet – août 2019\n"
w = verify.check_facts_coverage("Intern, Acme  Jul 2019 – Aug 2019\n", f)
assert w == [], f"false positive: {w}"
w = verify.check_facts_coverage("Intern, Acme  Jun 2019\n", f)
assert len(w) == 1 and '"Jun 2019"' in w[0], f"invented month not flagged: {w}"
PY
}
check facts-month-range facts_month_range
# a year-crossing range with one closing year: the first month is the year before; FR abbreviations parse.
facts_year_cross() {
  python3 -I - <<'PY' || return 1
import sys; sys.path.insert(0, "scripts")
import verify
f = "Stage, Acme, déc. – janv. 2020\n"
for ok in ("Dec 2019", "Jan 2020"):
    w = verify.check_facts_coverage(f"Intern  {ok}\n", f)
    assert w == [], f"{ok}: false positive {w}"
w = verify.check_facts_coverage("Intern  Dec 2020\n", f)
assert len(w) == 1 and '"Dec 2020"' in w[0], f"Dec 2020 hidden: {w}"
for abbr in ("févr.", "janv.", "avr.", "juil.", "sept.", "oct.", "nov.", "déc."):
    w = verify.check_facts_coverage("Intern  %s 2021\n" % abbr, "Stage, Acme, %s 2021\n" % abbr)
    assert w == [], f"{abbr}: {w}"
PY
}
check facts-year-cross facts_year_cross
text_render() {
  local pdf r
  pdf="$(ls "$out"/pdf/*.pdf 2>/dev/null | head -1)"; [ -n "$pdf" ] || { echo "no PDF from the template runs"; return 1; }
  python3 -I scripts/verify.py --text "$pdf" | grep -q '[A-Za-z]' || { echo "--text printed nothing"; return 1; }
  r="$(python3 -I scripts/verify.py --render "$pdf" --out "$S/render" --ppi 72)" || return 1
  [ "$(basename "$r" | head -1)" = "$(basename "$pdf" .pdf)-p1.png" ] && [ -s "$(echo "$r" | head -1)" ] || { echo "bad --render output: $r"; return 1; }
}
check text-render text_render
# corrupt or non-PDF input: one FAIL line and exit 1, never silence, a traceback or "no rasterizer"; a re-render drops its stale pages.
text_render_bad() {
  local d="$S/bad" rc txt
  rm -rf "$d"; mkdir -p "$d"; printf 'this is not a pdf\n' > "$d/bad.pdf"
  for m in --text --render; do
    rc=0; txt="$(python3 -I scripts/verify.py $m "$d/bad.pdf" --out "$d/o" 2>&1)" || rc=$?
    [ "$rc" -eq 1 ] || { echo "$m exit $rc, expected 1: $txt"; return 1; }
    [ "$(echo "$txt" | wc -l)" -eq 1 ] && echo "$txt" | grep -q '^FAIL  .*not a readable PDF' || { echo "$m: bad message: $txt"; return 1; }
  done
  local pdf; pdf="$(ls "$out"/pdf/*.pdf 2>/dev/null | head -1)"; [ -n "$pdf" ] || return 1
  mkdir -p "$d/o"; local stem; stem="$(basename "$pdf" .pdf)"
  touch "$d/o/$stem-p9.png" "$d/o/keep.png" "$d/o/${stem}x-p9.png"
  python3 -I scripts/verify.py --render "$pdf" --out "$d/o" --ppi 40 >/dev/null || return 1
  [ ! -e "$d/o/$stem-p9.png" ] || { echo "stale page kept"; return 1; }
  [ -e "$d/o/keep.png" ] && [ -e "$d/o/${stem}x-p9.png" ] || { echo "removed an unrelated file"; return 1; }
}
check text-render-bad text_render_bad
# scripts/look.py: offline parser tests (no model endpoint needed)
check look-parser python3 -I tests/test_look.py
# --render --crops: a solid band and a vector mark each get a <stem>-p<N>-<band>.png; plain --render is unchanged.
render_crops() {
  local d="$S/crops" r
  rm -rf "$d"; mkdir -p "$d"
  cat > "$d/c.typ" <<'TYP'
#set page(width: 21cm, height: 29.7cm, margin: 2cm)
#set text(size: 11pt)
#block(fill: rgb("#1b4965"), width: 100%, inset: 12pt)[#text(fill: white)[Band title]]
#v(1cm)
#grid(columns: 2, gutter: 8pt, circle(radius: 5pt, fill: black), [mail\@example.org])
TYP
  if command -v typst >/dev/null; then typst compile "$d/c.typ" "$d/c.pdf"
  else python3 -I -c 'import sys, typst; typst.compile(sys.argv[1], output=sys.argv[2])' "$d/c.typ" "$d/c.pdf"; fi || return 1
  [ "$(python3 -I scripts/verify.py --render "$d/c.pdf" --out "$d/a" | wc -l)" -eq 1 ] || { echo "plain --render printed more than the page PNG"; return 1; }
  r="$(python3 -I scripts/verify.py --render "$d/c.pdf" --out "$d/b" --crops)" || return 1
  [ "$(echo "$r" | sed -n 1p | xargs basename)" = "c-p1.png" ] || { echo "page PNG not first: $r"; return 1; }
  echo "$r" | sed -n 2p | grep -q '/c-p1-fill1\.png$' || { echo "no fill1 crop: $r"; return 1; }
  echo "$r" | grep -q '/c-p1-icon1\.png$' || { echo "no icon1 crop: $r"; return 1; }
  echo "$r" | while read -r f; do [ -s "$f" ] || exit 1; done || { echo "empty or missing file in: $r"; return 1; }
  # Stale crops: recompile without the band, re-render into the same --out: the old -fill1/-icon1 go,
  # a sibling stem's crops (<stem>x-...) stay.
  touch "$d/b/cx-p1-fill1.png"
  cat > "$d/c.typ" <<'TYP'
#set page(width: 21cm, height: 29.7cm, margin: 2cm)
#set text(size: 11pt)
Plain text only.
TYP
  if command -v typst >/dev/null; then typst compile "$d/c.typ" "$d/c.pdf"
  else python3 -I -c 'import sys, typst; typst.compile(sys.argv[1], output=sys.argv[2])' "$d/c.typ" "$d/c.pdf"; fi || return 1
  python3 -I scripts/verify.py --render "$d/c.pdf" --out "$d/b" --crops >/dev/null || return 1
  ls "$d/b" | grep -Eq '^c-p1-(fill|icon)[0-9]+\.png$' && { echo "stale crop kept: $(ls "$d/b")"; return 1; }
  [ -e "$d/b/cx-p1-fill1.png" ] && [ -e "$d/b/c-p1.png" ] || { echo "removed too much: $(ls "$d/b")"; return 1; }
}
check render-crops render_crops

# A sidebar covering most of the page (70%) must not become the "paper": one fill of the sidebar's own
# width, not a whole-page fill.
render_crops_sidebar() {
  local d="$S/crops-sb"
  rm -rf "$d"; mkdir -p "$d"
  cat > "$d/s.typ" <<'TYP'
#set page(width: 21cm, height: 29.7cm, margin: 0pt, fill: white)
#set text(size: 11pt)
#place(top + left, rect(width: 70%, height: 100%, fill: rgb("#1e5631"), inset: 2cm)[#text(fill: white)[Sidebar text]])
#place(top + right, box(width: 30%, inset: 1cm)[Main column text])
TYP
  if command -v typst >/dev/null; then typst compile "$d/s.typ" "$d/s.pdf"
  else python3 -I -c 'import sys, typst; typst.compile(sys.argv[1], output=sys.argv[2])' "$d/s.typ" "$d/s.pdf"; fi || return 1
  python3 -I scripts/verify.py --render "$d/s.pdf" --out "$d/o" --crops >/dev/null || return 1
  python3 -I - "$d/o/s-p1-fill1.png" <<'PY' || return 1
import sys
from PIL import Image
w = Image.open(sys.argv[1]).size[0]
# 70% of 21 cm at 300 ppi = 1736 px (+ padding); a whole-page fill is 2480
sys.exit(0 if 1600 <= w <= 2000 else "sidebar fill is %d px wide" % w)
PY
}
check render-crops-sidebar render_crops_sidebar

# Contact marks vs decorations. A solid phone glyph and a mail mark one no-break space from its value are kept
# (all five marks in the fixture), the heading squares (the same shape 3+ times) are not; a dark page under a
# white card gives the card and the band, not one whole-page fill; a plain --render drops the stem's old crops.
render_crops_marks() {
  local d="$S/crops-marks" r
  rm -rf "$d"; mkdir -p "$d"
  cat > "$d/m.typ" <<'TYP'
#set page(width: 21cm, height: 29.7cm, margin: 2cm)
#set text(size: 11pt)
#let sq = box(width: 5pt, height: 5pt, fill: rgb("#1b4965"))
#let tel = box(width: 6pt, height: 10pt, fill: rgb("#1b4965"))
#let mail = box(width: 11pt, height: 8pt, stroke: 1pt + rgb("#1b4965"))
#let pin = circle(radius: 4pt, fill: rgb("#1b4965"))
#let web = circle(radius: 4.5pt, stroke: 1pt + rgb("#1b4965"))
#tel#sym.space.nobreak (555) 555-0100  #h(1em) #mail#sym.space.nobreak me\@example.com  #h(1em) #pin#sym.space.nobreak City  #h(1em) #web#sym.space.nobreak example.com
#for t in ("Skills", "Work", "Study", "Other") [
  #v(1cm) #sq #sym.space.nobreak *#t*
]
TYP
  typst compile "$d/m.typ" "$d/m.pdf" 2>/dev/null || python3 -I -c 'import sys, typst; typst.compile(sys.argv[1], output=sys.argv[2])' "$d/m.typ" "$d/m.pdf" || return 1
  r="$(python3 -I scripts/verify.py --render "$d/m.pdf" --out "$d/o" --crops)" || return 1
  [ "$(echo "$r" | grep -c -- '-icon[0-9]*\.png$')" -eq 4 ] || { echo "want exactly the 4 contact marks, got: $r"; return 1; }
  # stale crops: a plain --render into the same --out leaves only the page PNG
  python3 -I scripts/verify.py --render "$d/m.pdf" --out "$d/o" >/dev/null || return 1
  [ "$(ls "$d/o")" = "m-p1.png" ] || { echo "plain --render kept crops: $(ls "$d/o")"; return 1; }
  # dark page, white card
  cat > "$d/k.typ" <<'TYP'
#set page(width: 21cm, height: 29.7cm, margin: 0pt, fill: rgb("#14213d"))
#set text(size: 11pt, fill: white)
#place(top + left, dx: 2cm, dy: 6cm, rect(width: 17cm, height: 18cm, fill: white, inset: 1cm)[#text(fill: black)[Card text]])
#place(top + left, dx: 2cm, dy: 1cm, rect(width: 17cm, height: 2cm, fill: rgb("#e63946"), inset: 8pt)[Band])
TYP
  typst compile "$d/k.typ" "$d/k.pdf" 2>/dev/null || python3 -I -c 'import sys, typst; typst.compile(sys.argv[1], output=sys.argv[2])' "$d/k.typ" "$d/k.pdf" || return 1
  python3 -I scripts/verify.py --render "$d/k.pdf" --out "$d/ko" --crops >/dev/null || return 1
  python3 -I - "$d/ko" <<'PY' || return 1
import glob, sys
from PIL import Image
fills = sorted(glob.glob(sys.argv[1] + "/k-p1-fill*.png"))
sizes = [Image.open(f).size for f in fills]
sys.exit(0 if len(fills) == 2 and all(max(s) < 2300 for s in sizes) else "fills: %s" % sizes)
PY
}
check render-crops-marks render_crops_marks

# A filled LinkedIn square and a filled mail (both fill 0.87-0.90 of their box) beside their values at the
# default 7 pt are kept; a frame stroked at the page edge is not the paper: the marks inside are found and
# no whole-page fill comes out.
render_crops_solid() {
  local d="$S/crops-solid" r
  rm -rf "$d"; mkdir -p "$d"
  cat > "$d/s.typ" <<'TYP'
#set page(width: 21cm, height: 29.7cm, margin: 2cm)
#set text(size: 10pt)
#let svg(vb, p) = box(image(bytes("<svg xmlns='http://www.w3.org/2000/svg' viewBox='" + vb + "'><path fill='#1b4965' d='" + p + "'/></svg>"), format: "svg", height: 7pt))
#let li = svg("0 0 16 16", "M0 1.146C0 .513.526 0 1.175 0h13.65C15.474 0 16 .513 16 1.146v13.708c0 .633-.526 1.146-1.175 1.146H1.175C.526 16 0 15.487 0 14.854zm4.943 12.248V6.169H2.542v7.225zm-1.2-8.212c.837 0 1.358-.554 1.358-1.248c-.015-.709-.52-1.248-1.342-1.248S2.4 3.226 2.4 3.934c0 .694.521 1.248 1.327 1.248zm4.908 8.212V9.359c0-.216.016-.432.08-.586c.173-.431.568-.878 1.232-.878c.869 0 1.216.662 1.216 1.634v3.865h2.401V9.25c0-2.22-1.184-3.252-2.764-3.252c-1.274 0-1.845.7-2.165 1.193v.025h-.016l.016-.025V6.169h-2.4c.03.678 0 7.225 0 7.225z")
#let mail = svg("0 0 24 24", "M22 7.535V17a3 3 0 0 1-2.824 2.995L19 20H5a3 3 0 0 1-2.995-2.824L2 17V7.535l9.445 6.297l.116.066a1 1 0 0 0 .878 0l.116-.066z M19 4c1.08 0 2.027.57 2.555 1.427L12 11.797l-9.555-6.37a3 3 0 0 1 2.354-1.42L5 4z")
#align(center)[#li#sym.space.nobreak in/someone #h(14pt) #mail#sym.space.nobreak someone\@example.org]
TYP
  typst compile "$d/s.typ" "$d/s.pdf" 2>/dev/null || python3 -I -c 'import sys, typst; typst.compile(sys.argv[1], output=sys.argv[2])' "$d/s.typ" "$d/s.pdf" || return 1
  r="$(python3 -I scripts/verify.py --render "$d/s.pdf" --out "$d/o" --crops)" || return 1
  [ "$(echo "$r" | grep -c -- '-icon[0-9]*\.png$')" -eq 2 ] || { echo "want the filled LinkedIn and mail kept, got: $r"; return 1; }
  cat > "$d/f.typ" <<'TYP'
#set page(width: 21cm, height: 29.7cm, margin: 2cm)
#set text(size: 11pt)
#place(top + left, dx: -2cm, dy: -2cm, rect(width: 21cm, height: 29.7cm, stroke: 0.5cm + rgb("#1b4965")))
#let tel = box(width: 6pt, height: 10pt, fill: rgb("#1b4965"))
#let mail = box(width: 11pt, height: 8pt, stroke: 1pt + rgb("#1b4965"))
#let pin = circle(radius: 4pt, fill: rgb("#1b4965"))
#let web = circle(radius: 4.5pt, stroke: 1pt + rgb("#1b4965"))
#tel#sym.space.nobreak (555) 555-0100  #h(1em) #mail#sym.space.nobreak me\@example.com  #h(1em) #pin#sym.space.nobreak City  #h(1em) #web#sym.space.nobreak example.com
TYP
  typst compile "$d/f.typ" "$d/f.pdf" 2>/dev/null || python3 -I -c 'import sys, typst; typst.compile(sys.argv[1], output=sys.argv[2])' "$d/f.typ" "$d/f.pdf" || return 1
  r="$(python3 -I scripts/verify.py --render "$d/f.pdf" --out "$d/fo" --crops)" || return 1
  [ "$(echo "$r" | grep -c -- '-icon[0-9]*\.png$')" -eq 4 ] || { echo "frame at the page edge: want the 4 marks, got: $r"; return 1; }
  [ "$(echo "$r" | grep -c -- '-fill[0-9]*\.png$')" -eq 0 ] || { echo "frame at the page edge became a fill: $r"; return 1; }
}
check render-crops-solid render_crops_solid

if [ "$quick" -eq 0 ]; then
  fx="$out/fixtures"; mkdir -p "$fx"
  check fixtures-render tests/fixtures/render.sh "$fx"
  # poppler vs pypdfium2 line by line (SKIPs unless both are installed)
  if command -v pdftotext >/dev/null && python3 -c "import pypdfium2" 2>/dev/null; then
    check backends/lines python3 -I tests/compare_backends.py "$fx"/*.pdf
  else
    echo "SKIP backends/lines (needs pdftotext and pypdfium2)"
  fi
  for f in tests/fixtures/*.typ; do
    nm="$(basename "$f" .typ)"
    if [ -f "$fx/$nm.pdf" ]; then
      check "gates/$nm" python3 -I scripts/verify.py --gates "$f" "$fx/$nm.pdf" --root .
    else
      total=$((total + 1)); fails=$((fails + 1)); echo "FAIL gates/$nm (no PDF rendered)"
    fi
  done
fi

echo "---"
echo "$((total - fails))/$total passed, $fails failed, $(( $(date +%s) - start )) s; output: $out"
[ "$fails" -eq 0 ]

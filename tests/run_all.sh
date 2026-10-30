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
mkdir -p "$S/tests"; cp -rL "$root/tests/fixtures" "$root/tests/compare_backends.py" "$S/tests/"
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

#!/usr/bin/env bash
# Run every check the repo has: self-tests, the 29 templates against their fill
# targets, the spacing fixtures and their gates. Keeps going after a failure.
# Usage: tests/run_all.sh [--quick] [outdir]
# Needs typst, poppler-utils (pdftotext), python3 + Pillow + pypdf.
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
mkdir -p "$S/tests"; cp -rL "$root/tests/fixtures" "$S/tests/"
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

if [ "$quick" -eq 0 ]; then
  fx="$out/fixtures"; mkdir -p "$fx"
  check fixtures-render tests/fixtures/render.sh "$fx"
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

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

check selftest-verify python3 -I scripts/verify.py --selftest
check selftest-pick_design python3 -I scripts/pick_design.py --selftest

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

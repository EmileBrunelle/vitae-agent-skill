#!/usr/bin/env bash
# Compile every spacing fixture to PDF in a scratch dir; non-zero exit on any failure.
# Usage: tests/fixtures/render.sh [outdir]
# Uses the typst CLI; without it, typst-py (pip install typst) through the current python3.
set -u
here="$(cd "$(dirname "$0")" && pwd)"; root="$(cd "$here/../.." && pwd)"
compile() { # compile <src> <pdf>
  if command -v typst >/dev/null; then typst compile --root "$root" "$1" "$2"
  else python3 -I -c 'import os, sys, typst
fp = [p for p in os.environ.get("TYPST_FONT_PATHS", "").split(os.pathsep) if p]  # typst-py ignores the variable
typst.compile(sys.argv[1], output=sys.argv[2], root=sys.argv[3], **({"font_paths": fp} if fp else {}))' "$1" "$2" "$root"; fi
}
out="${1:-$(mktemp -d)}"; mkdir -p "$out"; fail=0
for f in "$here"/*.typ; do
  n="$(basename "$f" .typ)"
  if compile "$f" "$out/$n.pdf" 2>"$out/$n.err"; then echo "ok   $n"
  else echo "FAIL $n (see $out/$n.err)"; fail=1; fi
done
echo "output: $out"; exit $fail

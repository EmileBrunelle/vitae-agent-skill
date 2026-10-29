#!/usr/bin/env bash
# Compile every spacing fixture to PDF in a scratch dir; non-zero exit on any failure.
# Usage: tests/fixtures/render.sh [outdir]
set -u
here="$(cd "$(dirname "$0")" && pwd)"; root="$(cd "$here/../.." && pwd)"
out="${1:-$(mktemp -d)}"; mkdir -p "$out"; fail=0
for f in "$here"/*.typ; do
  n="$(basename "$f" .typ)"
  if typst compile --root "$root" "$f" "$out/$n.pdf" 2>"$out/$n.err"; then echo "ok   $n"
  else echo "FAIL $n (see $out/$n.err)"; fail=1; fi
done
echo "output: $out"; exit $fail

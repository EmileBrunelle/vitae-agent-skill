#!/usr/bin/env bash
# One-command verification gate for SKILL.md step 6 (any POSIX shell; on bare
# Windows run the individual commands from references/ats.md). Runs every
# mechanical check and exits non-zero if any fails — the visual PNG
# inspection is the only step it cannot do for you.
# Usage: verify.sh cv.typ EXPECTED_PAGES [FILL_MIN FILL_MAX]
#   e.g. verify.sh cv.typ 1 94 96
set -uo pipefail
[ $# -ge 2 ] || { echo "usage: $0 cv.typ EXPECTED_PAGES [FILL_MIN FILL_MAX]"; exit 2; }
typ="$1"; expected="$2"; fmin="${3:-}"; fmax="${4:-}"
pdf="${typ%.typ}.pdf"; fail=0
here="$(cd "$(dirname "$0")" && pwd)"

err="$(typst compile "$typ" "$pdf" 2>&1)" || { echo "FAIL  compile"; echo "$err"; exit 1; }
[ -z "$err" ] || { echo "WARN  compile stderr (a missing font only warns and falls back):"; echo "$err"; }

pages="$(pdfinfo "$pdf" | awk '/^Pages:/{print $2}')"
if [ "$pages" = "$expected" ]; then echo "OK    pages: $pages"
else echo "FAIL  pages: $pages (expected $expected)"; fail=1; fi

tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
typst compile "$typ" "$tmp/p{p}.png" --format png --ppi 90
fills="$(python3 "$here/measure_fill.py" "$tmp"/p*.png)"
while IFS= read -r line; do
  case "$line" in *"blank page"*) echo "FAIL  fill: $line"; fail=1; continue;; esac
  if [ -n "$fmin" ] && [ -n "$fmax" ]; then
    y="$(printf '%s\n' "$line" | grep -oE 'to [0-9]+%' | grep -oE '[0-9]+')" || continue
    if [ "$y" -lt "$fmin" ] || [ "$y" -gt "$fmax" ]; then
      echo "FAIL  fill: $line (target ${fmin}-${fmax}%)"; fail=1
    else
      echo "OK    fill: $line"
    fi
  else
    echo "INFO  fill: $line (target = (100 - bottom-margin%) - 0..2%)"
  fi
done <<< "$fills"

if grep -qi '7d2231' "$typ"; then
  echo "WARN  template default accent (#7d2231) — give the candidate their own combination (references/design.md free axes)"
fi

txt="$(pdftotext "$pdf" -)"
if [ -z "${txt//[[:space:]]/}" ]; then echo "FAIL  extraction empty"; fail=1; fi
if printf '%s' "$txt" | grep -qE '([A-Z] ){3,}[A-Z]'; then
  echo "FAIL  spaced-out text in extraction (letterspacing/tracking?)"; fail=1
fi
last="$(printf '%s\n' "$txt" | tr -d '\f' | awk 'NF{l=$0} END{print l}')"
if printf '%s' "$last" | grep -qE '^.{0,25}$' && printf '%s' "$last" | grep -qE '[0-9]{4}[[:space:]]*$'; then
  echo "FAIL  orphaned date at end of extraction (\"$last\") — bullet-less grid entry; see the trap in references/ats.md"; fail=1
fi
echo "──── extraction (check reading order, orphaned dates, intact skill lines) ────"
printf '%s\n' "$txt"

[ "$fail" -eq 0 ] && echo "PASS  all mechanical checks — now LOOK at the PNGs"
exit "$fail"

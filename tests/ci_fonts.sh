#!/usr/bin/env bash
# Run a command with only the fonts CI has, so fill-window results match CI.
#   tests/ci_fonts.sh python -m pytest -q -n auto tests/integration
# The host's fonts can differ from CI's (Fedora's Caladea is not Ubuntu's), which moves templates
# at the edge of the fill window. The set is the one .github/actions/fonts installs: both call
# tests/fetch_fonts.sh, the single source of the pinned upstream sources and checksums.
# Needs: bwrap, typst, curl, git, tar, xz, ar, sha256sum. The fonts are fetched once into $VITAE_CI_FONTS (default
# ~/.cache/vitae-ci-fonts) and refetched when fetch_fonts.sh changes.
set -euo pipefail

CACHE="${VITAE_CI_FONTS:-${XDG_CACHE_HOME:-$HOME/.cache}/vitae-ci-fonts}"
die() { echo "ci_fonts.sh: $*" >&2; exit 1; }

[ $# -gt 0 ] || die "usage: tests/ci_fonts.sh COMMAND [ARGS...]"
for t in bwrap typst; do command -v "$t" >/dev/null || die "$t not found (install it first)"; done

"$(dirname "${BASH_SOURCE[0]}")/fetch_fonts.sh" "$CACHE"
font_paths="$CACHE"

# Hide the host's font directories; tmpfs only on paths that exist (bwrap would create the rest).
# The cached set is mounted inside the first hidden directory, where CI has it (a system font directory),
# so typst-py, which ignores TYPST_FONT_PATHS, finds it too.
hide=(); mnt=
for d in /usr/share/fonts /usr/local/share/fonts "$HOME/.local/share/fonts" "$HOME/.fonts"; do
  if [ -d "$d" ]; then hide+=(--tmpfs "$d"); [ -n "$mnt" ] || mnt=$d; fi
done
[ -z "$mnt" ] || hide+=(--ro-bind "$CACHE" "$mnt/vitae")

exec bwrap --bind / / --dev-bind /dev /dev "${hide[@]}" \
  --setenv FONTCONFIG_FILE /dev/null \
  --setenv TYPST_FONT_PATHS "$font_paths" \
  --setenv TYPST_IGNORE_SYSTEM_FONTS true \
  "$@"

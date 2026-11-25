#!/usr/bin/env bash
# Local mutation testing (not run in CI): `tests/mutmut.sh run --max-children 4`, `tests/mutmut.sh results`, ...
# mutmut derives module names from file paths and only strips a leading `src.`, so it needs the package at
# src/vitae; the repo keeps it at scripts/vitae. A temporary symlink bridges the two (removed on exit: a root-level
# `src/` would change ruff's first-party detection).
set -euo pipefail
cd "$(dirname "$0")/.."
[ -e src ] && { echo "src/ exists; remove it first" >&2; exit 2; }
ln -s scripts src
trap 'rm -f src' EXIT
mutmut "$@"

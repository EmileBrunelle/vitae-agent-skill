#!/usr/bin/env bash
# Environment doctor for vitae. Read-only by default: diagnoses and PRINTS
# the exact install command per platform — it never runs sudo or mutates the
# system. Opt-in `--install` fetches only the typst binary into ~/.local/bin.
set -euo pipefail

have() { command -v "$1" >/dev/null 2>&1; }
missing=0

if have typst; then
  echo "OK  typst $(typst --version | awk '{print $2}')"
else
  missing=1
  echo "MISSING  typst — install with ONE of:"
  echo "  brew install typst                          # macOS"
  echo "  sudo dnf install typst                      # Fedora"
  echo "  sudo apt install typst                      # Debian/Ubuntu (24.04+)"
  echo "  sudo pacman -S typst                        # Arch"
  echo "  winget install --id Typst.Typst             # Windows"
  echo "  cargo install typst-cli                     # any, via Rust"
  echo "  pip install typst                           # no CLI: compiles via Python API — see references/ats.md"
  echo "  $0 --install                                # no-root: binary -> ~/.local/bin"
fi

if have pdftotext && have pdfinfo; then
  echo "OK  poppler-utils (pdftotext, pdfinfo)"
else
  missing=1
  echo "MISSING  poppler-utils — needed for page-count and ATS extraction checks:"
  echo "  brew install poppler | sudo dnf install poppler-utils | sudo apt install poppler-utils"
  echo "  choco install poppler | scoop install poppler          # Windows"
fi

if python3 -c "import PIL" 2>/dev/null; then
  echo "OK  Pillow (measure_fill.py)"
else
  missing=1
  echo "MISSING  Pillow — needed for the page-fill measurement:"
  echo "  uv pip install Pillow | pip3 install --user Pillow | sudo dnf install python3-pillow"
fi

if [ "${1:-}" = "--install" ] && ! have typst; then
  os="$(uname -s)"; arch="$(uname -m)"
  case "$os" in
    Linux)  target="${arch}-unknown-linux-musl" ;;
    Darwin) target="${arch}-apple-darwin" ;;
    *) echo "--install supports Linux/macOS only; see https://github.com/typst/typst/releases"; exit 1 ;;
  esac
  tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
  url="https://github.com/typst/typst/releases/latest/download/typst-${target}.tar.xz"
  echo "Downloading $url"
  curl -fsSL "$url" -o "$tmp/typst.tar.xz"
  tar -xf "$tmp/typst.tar.xz" -C "$tmp"
  mkdir -p "$HOME/.local/bin"
  mv "$tmp"/typst-*/typst "$HOME/.local/bin/typst"
  echo "Installed: $("$HOME/.local/bin/typst" --version) -> ~/.local/bin (ensure it is on PATH)"
  missing=0
fi

exit $missing

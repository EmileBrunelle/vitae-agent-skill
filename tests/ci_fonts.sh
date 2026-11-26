#!/usr/bin/env bash
# Run a command with only the fonts CI has, so fill-window results match CI.
#   tests/ci_fonts.sh python -m pytest -q -n auto tests/integration
# The host's fonts can differ from CI's (Fedora's Caladea is not Ubuntu's), which moves templates
# at the edge of the fill window. The set mirrors .github/actions/fonts/action.yml: Ubuntu 26.04
# font packages plus the pinned google/fonts, Adwaita, STIX Two and Source Code Pro downloads.
# Keep the pins below in sync with that action. Needs: bwrap, typst, curl, git, ar, tar, unzip.
# The fonts are fetched once into $VITAE_CI_FONTS (default ~/.cache/vitae-ci-fonts).
set -euo pipefail

CACHE="${VITAE_CI_FONTS:-${XDG_CACHE_HOME:-$HOME/.cache}/vitae-ci-fonts}"
GOOGLE_FONTS_SHA=6157dfaa640ca5738b4d1a7070fe389c3036d7fc
ADWAITA_FONTS_SHA=0c79765f2bef25b38902fd8497616ac28185254c # tag 51.0
STIX_SHA=744a22a4dd626cd14d75728aef34fc8ad7c85db0           # stipub/stixfonts v2.13b171
SCP_URL=https://github.com/adobe-fonts/source-code-pro/releases/download/2.042R-u/1.062R-i/1.026R-vf/OTF-source-code-pro-2.042R-u_1.062R-i.zip
SCP_SHA=754a2e3ebb945ae905d720ac5896b3b34acc9546dd6551ef9536869788629dae
# sha256 of the eight STIX Two Text otf files at STIX_SHA (raw.githubusercontent serves them by commit).
STIX_SUMS=(
  "Regular c4864ca6ec071c2d31d0d8309001faa1ee3517fffb53a31a405a697b71f52ca1"
  "Italic cd64481fd10b69469074a3a8172fb5a22cb4116941d8aceafb8c77756b563df8"
  "Medium 9cc9f870852a46d708907b96ed024b8d0067a05276d939bfe0b7e89752afc8d9"
  "MediumItalic cc6e00147828e7b1f1aeaae928cabdbf14f5bffefb4e19b0ba2c46ce56292f4e"
  "SemiBold 896d80fbfd67e86ead7e2d593d631eab9bb142ee96dcd8e7aa8dff95ddda0f2a"
  "SemiBoldItalic 93d337715289b8e3ba8757cff89d29ff95630a1d08581dd46123d4c1ad1a7e2c"
  "Bold 7ef76c666a6704f76ed3fa27bcdda55b36e558b5c2c93b49b03d854db96bdeb5"
  "BoldItalic 90e88f2ac79d6c00a5ce2d8446bfdf9457aed6afc1159cde33262979d82c8586"
)
CURL=(curl -fsSL --retry 3 --max-time 300)
UBUNTU=http://archive.ubuntu.com/ubuntu
# Ubuntu rotates its pool/: a 404 on a .deb below means the pinned version left the archive. Update the
# DEBS path and sha256 to what the fonts action installs now, and bump nothing else (the cache key follows).
# Ubuntu 26.04 (resolute) packages, the versions the ubuntu-latest runner installed (CI run 45889715936,
# apt log): pool path and sha256. fonts-liberation and fonts-dejavu-core are preinstalled on the runner.
DEBS=(
  "pool/universe/f/fonts-cantarell/fonts-cantarell_0.303.1-4_all.deb 0c2c78d3108c7426ecb2fba14f426d1717847cf8f76ad76e1fe85d479323df0f"
  "pool/universe/f/fonts-crosextra-caladea/fonts-crosextra-caladea_20200211-2_all.deb 1a85651d71331a0e07dafa5d54e9aa54b445c29ae0dacb8c7cd224b1b7baaf82"
  "pool/main/f/fonts-dejavu/fonts-dejavu-core_2.37-8build1_all.deb f4606b12eb41ddf7932d3a1ebc2019f9bbf90d0824943a2dc0c77a00f43019f2"
  "pool/main/f/fonts-liberation/fonts-liberation_2.1.5-3build1_all.deb 47f156bc945cfc69cf2f2a0c19b8c82b67a685738d3846673462de6a73266e1b"
  "pool/main/f/fonts-noto/fonts-noto-core_20201225-2build1_all.deb 25999af6e6665266b1f055d351fc5008534e65c9f7bdda1e7fb5a7574c42372f"
  # fonts-noto-core depends on it in CI (apt installs it too); it is where "Noto Sans Mono" comes from.
  "pool/main/f/fonts-noto/fonts-noto-mono_20201225-2build1_all.deb b9b3e49f6a6926e3be9817c39587a4eeff48d147cb21fdd799f89a045fe097c5"
  "pool/universe/f/fonts-open-sans/fonts-open-sans_1.11-2build1_all.deb d3848bfbec4883c58f324759d44f10f7b995b8f4b94f52ecf96571fe0488a32d"
  "pool/main/f/fonts-urw-base35/fonts-urw-base35_20200910-8build1_all.deb be59254289c670d5c6580ce381995292aa05c9dd4bc5fa65b9dbaa527b55adda"
  "pool/universe/f/fonts-vazirmatn/fonts-vazirmatn_33.003-0ubuntu1_all.deb 93671a36b008992eca0ccc8a6503352f43bf9a2d73eb9ab2f717fdedb7eb251b"
)

TMP_DIR=
trap '[ -z "$TMP_DIR" ] || rm -rf "$TMP_DIR"' EXIT
die() { echo "ci_fonts.sh: $*" >&2; exit 1; }

[ $# -gt 0 ] || die "usage: tests/ci_fonts.sh COMMAND [ARGS...]"
for t in bwrap typst; do command -v "$t" >/dev/null || die "$t not found (install it first)"; done

fetch() {
  for t in curl git ar tar unzip sha256sum; do command -v "$t" >/dev/null || die "$t not found"; done
  local tmp; tmp=$(mktemp -d "$CACHE.tmp.XXXXXX")
  TMP_DIR=$tmp   # removed by the EXIT trap, also after die or Ctrl-C
  mkdir -p "$tmp/fonts" "$tmp/x"

  local entry path sum deb w
  for entry in "${DEBS[@]}"; do
    read -r path sum <<<"$entry"
    deb="$tmp/$(basename "$path")"
    "${CURL[@]}" -o "$deb" "$UBUNTU/$path"
    echo "$sum  $deb" | sha256sum -c --quiet - || die "checksum mismatch: $path"
    (cd "$tmp/x" && ar x "$deb" && tar -xf data.tar.* && rm -f data.tar.* control.tar.* debian-binary)
  done

  # google/fonts, sparse and pinned (same family list as the CI action).
  git init -q "$tmp/gf"
  git -C "$tmp/gf" remote add origin https://github.com/google/fonts
  git -C "$tmp/gf" config core.sparseCheckout true
  printf 'ofl/%s\n' firasans firamono ptsans geist geistmono onest instrumentsans publicsans \
    schibstedgrotesk spacegrotesk hankengrotesk familjengrotesk chivo \
    bigshouldersdisplay redhatdisplay redhattext redhatmono > "$tmp/gf/.git/info/sparse-checkout"
  git -C "$tmp/gf" fetch -q --depth 1 origin "$GOOGLE_FONTS_SHA"
  git -C "$tmp/gf" checkout -q FETCH_HEAD
  find "$tmp/gf/ofl" -name '*.ttf' -exec cp {} "$tmp/fonts/" \;

  git init -q "$tmp/ad"
  git -C "$tmp/ad" remote add origin https://github.com/GNOME/adwaita-fonts
  git -C "$tmp/ad" fetch -q --depth 1 origin "$ADWAITA_FONTS_SHA"
  git -C "$tmp/ad" checkout -q FETCH_HEAD
  find "$tmp/ad/sans" "$tmp/ad/mono" -name '*.ttf' -exec cp {} "$tmp/fonts/" \;

  for entry in "${STIX_SUMS[@]}"; do
    read -r w sum <<<"$entry"
    "${CURL[@]}" -o "$tmp/fonts/STIXTwoText-$w.otf" \
      "https://raw.githubusercontent.com/stipub/stixfonts/$STIX_SHA/fonts/static_otf/STIXTwoText-$w.otf"
    echo "$sum  $tmp/fonts/STIXTwoText-$w.otf" | sha256sum -c --quiet - || die "checksum mismatch: STIX Two Text $w"
  done
  "${CURL[@]}" -o "$tmp/scp.zip" "$SCP_URL"
  echo "$SCP_SHA  $tmp/scp.zip" | sha256sum -c --quiet - || die "checksum mismatch: Source Code Pro zip"
  unzip -q -j "$tmp/scp.zip" 'OTF/*.otf' -d "$tmp/fonts"

  # Keep only what is needed; the marker is written last so a partial fetch is redone.
  mkdir -p "$tmp/out"
  mv "$tmp/fonts" "$tmp/out/fonts"
  mv "$tmp/x/usr/share/fonts" "$tmp/out/debs"
  echo "$PINS" > "$tmp/out/pins"
  rm -rf "$CACHE"
  mv "$tmp/out" "$CACHE"
  rm -rf "$tmp"; TMP_DIR=   # the script ends in exec, which skips the EXIT trap
}

# Cache key: the pins AND this script's own hash, so the family lists, the copy logic and any edit
# to fetch() refetch too (a pin-only key left a stale cache after a change to what is copied).
PINS=$(printf '%s\n' "$GOOGLE_FONTS_SHA" "$ADWAITA_FONTS_SHA" "$STIX_SHA" "$SCP_URL" "$SCP_SHA" "$UBUNTU" \
  "${DEBS[@]}" "${STIX_SUMS[@]}" "$(sha256sum < "${BASH_SOURCE[0]}")" | sha256sum | cut -d' ' -f1)
if [ "$(cat "$CACHE/pins" 2>/dev/null || true)" != "$PINS" ]; then
  echo "ci_fonts.sh: fetching the CI font set into $CACHE" >&2
  mkdir -p "$(dirname "$CACHE")"
  fetch
fi

font_paths="$CACHE/fonts"
while IFS= read -r d; do font_paths+=":$d"; done < <(find "$CACHE/debs" -type d)

# Hide the host's font directories; tmpfs only on paths that exist (bwrap would create the rest).
hide=()
for d in /usr/share/fonts /usr/local/share/fonts "$HOME/.local/share/fonts" "$HOME/.fonts"; do
  [ -d "$d" ] && hide+=(--tmpfs "$d")
done

exec bwrap --bind / / --dev-bind /dev /dev "${hide[@]}" \
  --setenv FONTCONFIG_FILE /dev/null \
  --setenv TYPST_FONT_PATHS "$font_paths" \
  --setenv TYPST_IGNORE_SYSTEM_FONTS true \
  "$@"

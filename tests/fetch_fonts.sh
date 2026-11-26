#!/usr/bin/env bash
# The CI font set, from pinned upstream sources only (no distro packages). The single source of
# the pins, shared by .github/actions/fonts (CI) and tests/ci_fonts.sh (local repro).
#   tests/fetch_fonts.sh DEST    fetch into DEST (flat), only when the pins changed
#   tests/fetch_fonts.sh --key   print the pin hash (the CI cache key)
# Sources: google/fonts (pinned commit, sparse), GNOME/adwaita-fonts, stipub/stixfonts,
# ArtifexSoftware/urw-base35-fonts (all pinned commits), the official Liberation 2.1.5 tarball, and
# Cantarell 0.303.1 (the GNOME one users have: Fedora, Ubuntu; google/fonts ships an older, taller
# Cantarell) from the Debian .deb on snapshot.debian.org (byte-stable URL; GNOME publishes no binaries).
# Every fetched file is covered by FONTS_DIGEST (sha256 over the sorted per-file sha256 list), and
# the tarball and STIX files by their own sha256. After changing a pin, run the script once: it
# prints the new digest on a mismatch; paste it below. Needs: curl, git, tar, sha256sum, ar.
# Typst embeds DejaVu Sans Mono and Libertinus Serif, so they are not fetched.
set -euo pipefail

GOOGLE_FONTS_SHA=6157dfaa640ca5738b4d1a7070fe389c3036d7fc
ADWAITA_FONTS_SHA=0c79765f2bef25b38902fd8497616ac28185254c  # tag 51.0
STIX_SHA=744a22a4dd626cd14d75728aef34fc8ad7c85db0           # stipub/stixfonts v2.13b171
URW_SHA=c15105598aa7eb256b1ebfcecd3d078801521e73            # urw-base35-fonts tag 20200910
LIBERATION_URL=https://github.com/liberationfonts/liberation-fonts/files/7261482/liberation-fonts-ttf-2.1.5.tar.gz
CANTARELL_URL=https://snapshot.debian.org/file/bfafc7565439c807b976439e6d16c37934efe73d  # fonts-cantarell 0.303.1-4 (Cantarell-VF.otf)
CANTARELL_SHA=21f8160696cd2b51ac104e735fd63d0e2245cd84cf75f17919f1425dce4ea258
LIBERATION_SHA=7191c669bf38899f73a2094ed00f7b800553364f90e2637010a69c0e268f25d0
# google/fonts ofl/ directories. Static families are copied whole; Montserrat, Noto, Open Sans,
# Source Code Pro and Vazirmatn are variable-only there (Typst instantiates the weight axis).
GOOGLE_FAMILIES=(
  firasans firamono ptsans geist geistmono onest instrumentsans publicsans
  schibstedgrotesk spacegrotesk hankengrotesk familjengrotesk chivo
  bigshouldersdisplay redhatdisplay redhattext redhatmono
  notosans notoserif notosansmono opensans caladea carlito vazirmatn montserrat
  sourcecodepro
)
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
FONTS_DIGEST=c96a0eb2ac0ae3884c8c4dd12da351ef548b161b0b5c73d1664377cea103816b

# Pin hash: the pins AND this script's own hash, so a change to the family lists or the copy logic
# refetches too.
pin_hash() {
  printf '%s\n' "$GOOGLE_FONTS_SHA" "$ADWAITA_FONTS_SHA" "$STIX_SHA" "$URW_SHA" "$LIBERATION_URL" \
    "$LIBERATION_SHA" "$CANTARELL_URL" "$CANTARELL_SHA" "${GOOGLE_FAMILIES[@]}" "${STIX_SUMS[@]}" "$FONTS_DIGEST" \
    "$(sha256sum < "${BASH_SOURCE[0]}")" | sha256sum | cut -d' ' -f1
}

die() { echo "fetch_fonts.sh: $*" >&2; exit 1; }
[ $# -eq 1 ] || die "usage: tests/fetch_fonts.sh DEST | --key"
if [ "$1" = --key ]; then pin_hash; exit 0; fi
DEST=$1
PINS=$(pin_hash)
if [ "$(cat "$DEST/.pins" 2>/dev/null || true)" = "$PINS" ]; then exit 0; fi

for t in curl git tar sha256sum ar; do command -v "$t" >/dev/null || die "$t not found"; done
CURL=(curl -fsSL --retry 3 --max-time 300)
mkdir -p "$(dirname "$DEST")"
tmp=$(mktemp -d "$DEST.tmp.XXXXXX")
trap 'rm -rf "$tmp"' EXIT
fonts="$tmp/fonts"; mkdir -p "$fonts"

# git_pin NAME URL SHA PATH...: sparse, shallow checkout of one pinned commit into $tmp/NAME.
git_pin() {
  local name=$1 url=$2 sha=$3; shift 3
  git init -q "$tmp/$name"
  git -C "$tmp/$name" remote add origin "$url"
  git -C "$tmp/$name" config core.sparseCheckout true
  printf '%s\n' "$@" > "$tmp/$name/.git/info/sparse-checkout"
  git -C "$tmp/$name" fetch -q --depth 1 origin "$sha"
  git -C "$tmp/$name" checkout -q FETCH_HEAD
}

paths=(); for f in "${GOOGLE_FAMILIES[@]}"; do paths+=("ofl/$f"); done
git_pin gf https://github.com/google/fonts "$GOOGLE_FONTS_SHA" "${paths[@]}"
find "$tmp/gf/ofl" -name '*.ttf' -exec cp {} "$fonts/" \;

git_pin ad https://github.com/GNOME/adwaita-fonts "$ADWAITA_FONTS_SHA" sans mono
find "$tmp/ad/sans" "$tmp/ad/mono" -name '*.ttf' -exec cp {} "$fonts/" \;

git_pin urw https://github.com/ArtifexSoftware/urw-base35-fonts "$URW_SHA" fonts
for f in C059 P052 NimbusSans NimbusRoman; do cp "$tmp"/urw/fonts/"$f"-*.otf "$fonts/"; done

"${CURL[@]}" -o "$tmp/liberation.tar.gz" "$LIBERATION_URL"
echo "$LIBERATION_SHA  $tmp/liberation.tar.gz" | sha256sum -c --quiet - || die "checksum mismatch: Liberation tarball"
tar -xzf "$tmp/liberation.tar.gz" -C "$tmp" --wildcards '*/LiberationSans-*.ttf' '*/LiberationSerif-*.ttf'
cp "$tmp"/liberation-fonts-ttf-*/*.ttf "$fonts/"

# Cantarell: the .deb is an ar archive; only its variable OTF is kept.
"${CURL[@]}" -o "$tmp/cantarell.deb" "$CANTARELL_URL"
echo "$CANTARELL_SHA  $tmp/cantarell.deb" | sha256sum -c --quiet - || die "checksum mismatch: Cantarell .deb"
(cd "$tmp" && ar x cantarell.deb data.tar.xz && tar -xJf data.tar.xz --wildcards '*/Cantarell-VF.otf')
cp "$tmp"/usr/share/fonts/opentype/cantarell/Cantarell-VF.otf "$fonts/"

for entry in "${STIX_SUMS[@]}"; do
  read -r w sum <<<"$entry"
  "${CURL[@]}" -o "$fonts/STIXTwoText-$w.otf" \
    "https://raw.githubusercontent.com/stipub/stixfonts/$STIX_SHA/fonts/static_otf/STIXTwoText-$w.otf"
  echo "$sum  $fonts/STIXTwoText-$w.otf" | sha256sum -c --quiet - || die "checksum mismatch: STIX Two Text $w"
done

got=$(cd "$fonts" && LC_ALL=C find . -type f -print0 | LC_ALL=C sort -z | xargs -0 sha256sum | sha256sum | cut -d' ' -f1)
[ "$got" = "$FONTS_DIGEST" ] || die "FONTS_DIGEST mismatch: fetched files hash to $got (pinned: $FONTS_DIGEST)"

# The marker is written last so a partial fetch is redone.
echo "$PINS" > "$fonts/.pins"
rm -rf "$DEST"
mv "$fonts" "$DEST"

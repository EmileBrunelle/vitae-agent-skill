#!/usr/bin/env python3
# AGENT: do not read this file — run it. Its printed output is the instruction.
# Usage: python3 scripts/harvest_icons.py <cv folder>   (writes <cv folder>/icons.typ)
# (Reading it wastes context: a small model read a sibling script 3 times and never wrote the CV.)
"""Fetch the contact/platform mark path data into a generated `icons.typ`.

Run this at CV-BUILD time, in the folder that holds the `.typ` and its
`lib.typ` copy, just before `typst compile`:

    python3 scripts/harvest_icons.py <folder>      # writes <folder>/icons.typ

Why fetch instead of vendoring: the path data is third-party artwork (Bootstrap
Icons, Tabler, Phosphor — all MIT). This repo ships none of it; it ships the
address. `lib.typ` does `#import "icons.typ": *`, so the generated file must
sit beside the `lib.typ` that imports it — Typst resolves an import relative to
the importing file, symlinks included. Never point this at `templates/`: the
`icons.typ` committed there is the EMPTY fallback that makes that import
resolve with no network and no script run, and overwriting it would put
third-party artwork in the repo and noise in `git status`.

The file is ALWAYS written, including when the API is unreachable — then with
empty strings. Typst has no "if this file exists", so unconditional generation
is what makes graceful degradation possible without conditional logic in the
document: an empty body makes `pmark` render nothing, the contact line keeps
its URL in plain text, and the CV stays valid and ATS-readable. A failure is
loud on stderr but never fails the build (exit status stays 0).

Adding a kit: add its vars to ICONS below and teach `marks()` in lib.typ about
them. Prefer FILL-based sets (Tabler *-filled, Phosphor *-fill, Bootstrap
*-fill): a stroke icon is REFUSED here (it renders as a solid blob through
`pmark`, which substitutes the colour into `currentColor` and fills).
"""
import json
import os
import re
import sys
import unicodedata
import urllib.request

API = "https://api.iconify.design"

# Typst variable name -> "<iconify prefix>:<icon name>". lib.typ reads
# `<var>-body` and `<var>-vb`.
ICONS = {
    # default kit: Bootstrap brand marks + Tabler filled generics
    "li": "bi:linkedin",
    "gh": "bi:github",
    "mail": "tabler:mail-filled",
    "web": "tabler:world-filled",
    "phone": "tabler:phone-filled",
    "pin": "tabler:map-pin-filled",
    # phosphor kit
    "ph-envelope_simple_fill": "ph:envelope-simple-fill",
    "ph-globe_fill": "ph:globe-fill",
    "ph-phone_fill": "ph:phone-fill",
    "ph-map_pin_fill": "ph:map-pin-fill",
    # bootstrap kit
    "bi-envelope_fill": "bi:envelope-fill",
    "bi-globe": "bi:globe",
    "bi-telephone_fill": "bi:telephone-fill",
    "bi-geo_alt_fill": "bi:geo-alt-fill",
}


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "vitae-harvest/2.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        raw = r.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError(f"response over {MAX_BYTES} bytes")
    return json.loads(raw)


MAX_BYTES = 2_000_000


def clean(v, cap=80):
    """A fetched value made safe for a `//` comment: every whitespace, control,
    format and separator char (any Unicode line break included) becomes one
    space; capped in length."""
    s = "".join(" " if unicodedata.category(c)[0] in "CZ" else c
                for c in str(v))
    return " ".join(s.split())[:cap]
NUM = re.compile(r"\d{1,6}(?:\.\d{1,6})?\Z")


def typst_str(s):
    """A Typst string literal for `s`: backslash and quote escaped first, every
    control char / line separator as \\u{..}, so no content can leave the string."""
    out = []
    for ch in s:
        if ch == "\\":
            out.append("\\\\")
        elif ch == '"':
            out.append('\\"')
        elif ord(ch) < 32 or ord(ch) in (0x7f, 0x2028, 0x2029, 0x85):
            out.append("\\u{%x}" % ord(ch))
        else:
            out.append(ch)
    return '"' + "".join(out) + '"'


def fetch_set(prefix, names):
    """(icons dict, collection meta) for one set; ({}, {}) on any failure."""
    try:
        coll = fetch(f"{API}/collections?prefix={prefix}").get(prefix, {})
        data = fetch(f"{API}/{prefix}.json?icons={','.join(names)}")
        if not isinstance(data, dict) or not isinstance(coll, dict):
            raise ValueError("unexpected reply shape")
    except Exception as e:                      # network, DNS, HTTP, bad JSON
        print(f"ICONS: {prefix} unreachable ({e}) — marks will be omitted, "
              f"contact lines keep their URLs as text", file=sys.stderr)
        return {}, {}
    if data.get("not_found"):
        print(f"ICONS: {prefix}: not in set: {data['not_found']}", file=sys.stderr)
    return data, coll


def usable(var, name, icon):
    """Body of a fill-based icon, or None with a reason on stderr."""
    body = icon.get("body") if isinstance(icon, dict) else None
    if not isinstance(body, str) or not body.strip():
        print(f"ICONS: {var} ('{name}') has no usable body; omitted",
              file=sys.stderr)
        return None
    try:
        body.encode("utf-8")
    except UnicodeEncodeError:
        print(f"ICONS: {var} ('{name}') body is not valid text; omitted",
              file=sys.stderr)
        return None
    if "<" not in body or len(body) > 50_000:
        print(f"ICONS: {var} ('{name}') body is not SVG markup; omitted",
              file=sys.stderr)
        return None
    if 'fill="none"' in body or re.search(r'\bstroke="(?!none)', body):
        print(f"ICONS: {var} ('{name}') is stroke-based — pmark fills the "
              f"path, so it would render as a blob; omitted", file=sys.stderr)
        return None
    if icon.get("hidden"):
        # Withdrawn-but-served marks (LinkedIn's, pulled over brand-guideline
        # enforcement): the licence grant holds, but the path stops tracking
        # the logo and may be purged. Say so rather than degrade silently.
        print(f"ICONS: {var} ('{name}') is hidden/deprecated upstream — "
              f"served for compatibility, no longer maintained", file=sys.stderr)
    return body


# ponytail: no cache — every CV build spends 3 API round trips (one per set)
# and a build with no network gets no marks at all. Ceiling: fine at one CV per
# session. If builds get frequent or offline-first matters, cache the last good
# icons.typ under ~/.cache/vitae/ and copy it in when the fetch fails.
def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    out = sys.argv[1].rstrip("/") + "/icons.typ"

    by_prefix = {}
    for var, ref in ICONS.items():
        prefix, name = ref.split(":", 1)
        by_prefix.setdefault(prefix, []).append((var, name))

    lines = ["// GENERATED by scripts/harvest_icons.py — do not edit, do not",
             "// commit. Icon path data fetched from the Iconify API",
             f"// ({API}) when this CV was built; the same data the npm icon",
             "// packages publish. An empty value means the fetch failed: the",
             "// mark is then simply not drawn.", ""]
    got = 0
    for prefix, wanted in by_prefix.items():
        data, coll = fetch_set(prefix, [n for _, n in wanted])
        icons = data.get("icons", {}) if isinstance(data, dict) else {}
        if not isinstance(icons, dict):
            icons = {}
        dw, dh = data.get("width", 16), data.get("height", 16)
        lic = coll.get("license", {})
        if not isinstance(lic, dict):
            lic = {}
        lines.append(f"// {clean(coll.get('name', prefix))} — "
                     f"{clean(lic.get('title', '?'))} "
                     f"({clean(lic.get('url', '?'))}), set version "
                     f"{clean(coll.get('version', '?'))}")
        for var, name in wanted:
            icon = icons.get(name)
            body = usable(var, name, icon) if icon else None
            if body is None:
                lines += [f'#let {var}-body = ""', f'#let {var}-vb = ""']
                continue
            w, h = str(icon.get("width", dw)), str(icon.get("height", dh))
            if not (NUM.match(w) and NUM.match(h)):
                print(f"ICONS: {var} ('{name}') has a non-numeric size; omitted",
                      file=sys.stderr)
                lines += [f'#let {var}-body = ""', f'#let {var}-vb = ""']
                continue
            got += 1
            lines += [f'#let {var}-body = {typst_str(body)}',
                      f'#let {var}-vb = {typst_str(f"0 0 {w} {h}")}']
        lines.append("")

    if os.path.islink(out):
        sys.exit(f"ICONS: {out} is a symlink — refusing to write through it")
    text = "\n".join(lines) + "\n"
    try:
        data_b = text.encode("utf-8")
    except UnicodeEncodeError as e:
        sys.exit(f"ICONS: unencodable fetched text ({e}); {out} left untouched")
    tmp = f"{out}.tmp{os.getpid()}"
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL
                 | getattr(os, "O_NOFOLLOW", 0), 0o644)
    with os.fdopen(fd, "wb") as fh:
        fh.write(data_b)
    os.replace(tmp, out)
    print(f"{out}: {got}/{len(ICONS)} marks"
          + ("" if got == len(ICONS) else " — the rest render as no mark"))


if __name__ == "__main__":
    main()

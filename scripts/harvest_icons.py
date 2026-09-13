#!/usr/bin/env python3
"""Harvest icon path data from the icon-set ecosystem into inline Typst code.

The deliverable (.typ + lib.typ) must compile on typst.app with zero installs,
so icons are INLINED — but they don't have to be hand-copied: this script pulls
any set's SVG bodies from the Iconify API (https://iconify.design), which
mirrors the icon packages published on npm (Tabler, Phosphor, Bootstrap,
Lucide, …), and emits ready-to-paste Typst `#let` definitions with the
provenance and licence documented. An npm-based fetch of the same package is an
equivalent alternative for a machine that already has node; this script only
needs the Python stdlib.

Run it AT AUTHORING TIME (adding a set to lib.typ), never at CV-build time.

`--update` closes the copy-paste loop: it rewrites the `#let <var>-path` /
`#let <var>-vb` pairs in lib.typ in place from the live API, so refreshing a
brand mark whose logo changed is one command and NOT an edit to the skill:

    python3 harvest_icons.py bi li=linkedin,gh=github \
        --update ../templates/lib.typ

Why the data still has to be inlined rather than fetched: Typst makes no
network request at compile time, and the deliverable must build on typst.app
with no assets directory. So the freshness lives in this script, not in the
document. Re-run it when a brand refreshes its mark, then LOOK at the render —
a new path can change the mark's optical weight at 7pt even when the URL,
the licence and the gate all stay identical.

Usage:
    python3 harvest_icons.py <prefix> <icon,icon,...> [--var-prefix name]
    python3 harvest_icons.py <prefix> <var=icon,var=icon> --update <lib.typ>
    python3 harvest_icons.py ph envelope-simple-fill,globe-fill,phone-fill,map-pin-fill --var-prefix ph
    python3 harvest_icons.py bi envelope-fill,globe,telephone-fill,geo-alt-fill --var-prefix bi

Notes:
- Prefer FILL-based sets (Tabler filled, Phosphor *-fill, Bootstrap *-fill):
  they colour reliably. Stroke-based sets (Lucide, Feather) render through
  currentColor substitution in `pmarkb` but hairline strokes can disappear at
  7pt — eyeball the render before adopting one.
- The emitted body is the icon's inner SVG with its viewBox; `lib.typ`'s
  `pmarkb` wraps it and substitutes currentColor with the family's colour.
- ALWAYS re-run the extraction gate after adding a set: an icon must emit NO
  text (the pmark/pmarkb image mechanism guarantees it, but verify anyway).
"""
import json
import re
import sys
import urllib.request

API = "https://api.iconify.design"


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "vitae-harvest/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def main():
    argv = sys.argv[1:]
    out = None
    if "--update" in argv:
        i = argv.index("--update")
        out = argv[i + 1]
        del argv[i:i + 2]
    var = None
    if "--var-prefix" in argv:
        i = argv.index("--var-prefix")
        var = argv[i + 1]
        del argv[i:i + 2]
    if len(argv) != 2:
        sys.exit(__doc__)
    prefix, names = argv
    var = var or prefix
    # --update takes `var=icon` pairs: the lib.typ variable is `li`, the icon
    # upstream is `linkedin`, and nothing in the API knows about that mapping.
    mapping = dict(p.split("=", 1) for p in names.split(",")) if out else {}
    if out:
        names = ",".join(mapping.values())

    coll = fetch(f"{API}/collections?prefix={prefix}").get(prefix, {})
    data = fetch(f"{API}/{prefix}.json?icons={names}")
    w, h = data.get("width", 16), data.get("height", 16)
    lic = coll.get("license", {})
    print(f"// {coll.get('name', prefix)} — {lic.get('title', '?')} "
          f"({lic.get('url', '?')})")
    print(f"// harvested via Iconify API ({API}), set version "
          f"{coll.get('version', '?')} — same data as the npm package")
    missing = data.get("not_found", [])
    if missing:
        print(f"// NOT FOUND in set: {missing}", file=sys.stderr)
    if out:
        return update(out, data, coll, mapping, w, h)
    for name, icon in data.get("icons", {}).items():
        iw, ih = icon.get("width", w), icon.get("height", h)
        body = icon["body"].replace('"', '\\"')
        slug = name.replace("-", "_")
        print(f'#let {var}-{slug}-body = "{body}"')
        print(f'#let {var}-{slug}-vb = "0 0 {iw} {ih}"')


def one_path(body):
    """Return the concatenated `d` of a body made ONLY of <path> elements.

    `pmark` renders a single `d` string, so a body carrying a <circle>, <rect>
    or <g transform> would silently lose that geometry. Refuse instead: the
    caller keeps the old mark and a human picks a different icon.
    """
    tags = set(re.findall(r"<(\w+)", body))
    if tags - {"path"}:
        return None, f"body is not path-only ({', '.join(sorted(tags))})"
    # A stroke icon is path-only too, but `pmark` FILLS the path: harvesting
    # tabler:brand-github (one path, fill="none" stroke-width="2") renders a
    # blob, not a logo. Reject it here rather than leaving it to the eye.
    if 'fill="none"' in body or re.search(r'\bstroke="(?!none)', body):
        return None, ("body is stroke-based, not fill-based — pmark fills the "
                      "path, so a stroke icon renders as a solid blob; use the "
                      "set's filled variant (ph:*-fill, bi:*-fill, tabler *-filled)")
    ds = re.findall(r'\bd="([^"]+)"', body)
    return ("".join(ds), None) if ds else (None, "no path data")


def update(path, data, coll, mapping, w, h):
    """Rewrite the `#let <var>-path` / `-vb` pairs in lib.typ, in place."""
    src = open(path).read()
    icons, changed, kept = data.get("icons", {}), [], []
    for var, name in mapping.items():
        icon = icons.get(name)
        if icon is None:
            print(f"SKIP {var}: '{name}' not in {coll.get('name', '?')} "
                  f"— nothing written", file=sys.stderr)
            continue
        if icon.get("hidden"):
            # Simple Icons keeps withdrawn brand marks served-but-hidden
            # (LinkedIn, after its brand-guideline enforcement). Still CC0 and
            # still fetchable, but it will not track future logo changes and
            # may be purged: say so rather than refresh it silently.
            print(f"NOTE {var}: '{name}' is marked hidden/deprecated upstream "
                  f"— served for compatibility, no longer maintained",
                  file=sys.stderr)
        d, why = one_path(icon["body"])
        if d is None:
            print(f"SKIP {var}: {why} — nothing written", file=sys.stderr)
            continue
        vb = f"0 0 {icon.get('width', w)} {icon.get('height', h)}"
        new = (f'#let {var}-path = "{d}"\n#let {var}-vb = "{vb}"')
        pat = re.compile(rf'^#let {re.escape(var)}-path = ".*"\n'
                         rf'#let {re.escape(var)}-vb = ".*"$', re.M)
        if not pat.search(src):
            print(f"SKIP {var}: no `#let {var}-path` + `-vb` pair in {path}",
                  file=sys.stderr)
            continue
        (changed if pat.search(src).group(0) != new else kept).append(var)
        src = pat.sub(lambda _m: new, src, count=1)
    open(path, "w").write(src)
    v = coll.get("version", "?")
    print(f"{path}: updated {changed or 'nothing'} "
          f"(unchanged: {kept or 'none'}) from {coll.get('name','?')} {v}")
    if changed:
        print("Re-render and LOOK at the marks, then re-run the extraction "
              "gate — a refreshed path can shift optical weight at 7pt.")


if __name__ == "__main__":
    main()

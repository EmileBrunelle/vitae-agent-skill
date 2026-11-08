"""Design init: the compiling starting folder (--init) for a drawn recipe."""
from __future__ import annotations

import os
import re
import sys
from collections.abc import Callable, Mapping
from typing import cast

from vitae.design.emit import _chain, _vitae_header, lang_arg
from vitae.design.pick import Pick
from vitae.design.tables import FONTS


def _sub1(src: str, pat: str, repl: str | Callable[[re.Match[str]], str],
          what: str, family: str, required: bool = True) -> str:
    """Replace exactly one match of `pat` (MULTILINE) in `src`."""
    new, n = re.subn(pat, repl, src, count=0, flags=re.M)
    if n != 1:
        if n == 0 and not required:
            return src
        raise SystemExit("--init: %s: %d match(es) for %s (need exactly 1) — "
                         "the family file changed shape; fall back to the "
                         "manual route (cp + --emit-typ)" % (family, n, what))
    return new


def _write_nofollow(path: str, data: bytes) -> None:
    """Write bytes to `path`, refusing to follow a symlink at the final component."""
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(path, flags, 0o644)
    except OSError as e:
        raise SystemExit("--init: cannot write %s (%s)" % (path, e.strerror)) from e
    with os.fdopen(fd, "wb") as fh:
        fh.write(data)


def _apply_labels(src: str, default: Mapping[str, object],
                  drawn: Mapping[str, object], family: str) -> str:
    """Make the starter's section headings the DRAWN labels. The family file
    ships with the family's default names; a drawn variant renames the heading,
    a drawn None drops the whole soft-skills section (its leading comment
    line included)."""
    for role in ("profile", "skills", "soft"):
        _o, _n = default.get(role), drawn.get(role)
        old = _o if isinstance(_o, str) else None
        new = _n if isinstance(_n, str) else None
        if old is None or old == new:
            continue
        if new is None:
            src = _sub1(src, r'(?s)(?:^// -[^\n]*\n)?^#section\("%s"\)\[\n.*?^\]\n\n?'
                        % re.escape(old), "", "soft section", family)
        else:
            label: str = new

            def _rename(mm: re.Match[str], label: str = label) -> str:
                return mm.group(1) + '"%s"' % label
            src = _sub1(src, r'^(#section\()"%s"' % re.escape(old),
                        _rename, "#section(%r)" % old, family)
    return src


def init_folder(p: Pick, folder: str, force: bool = False, lang: str = "en",
                region: str | None = None) -> None:
    """One executed command -> a compiling starting point in `folder`.

    lib.typ / icons.typ are copied byte for byte. cv.typ is the drawn family's
    worked file with the drawn recipe's VALUES substituted line by line on the
    preamble's known `#let` / `#set par` lines (the family's own icon helpers,
    selective imports and devices are untouched — a wholesale preamble swap
    would drop them: color-band keeps its own ic-* defs, avant-poster its `mx`)."""
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    fam, d, fp = p["family"], p["recipe"], FONTS[p["family"]]
    fdir = os.path.join(root, "templates", "families", fam)
    out = os.path.join(folder, "cv.typ")
    for _n in ("cv.typ", "lib.typ", "icons.typ"):
        _d = os.path.join(folder, _n)
        if os.path.islink(_d):
            raise SystemExit("--init: %s is a symlink — refusing to write "
                             "through it (replace it with a regular file or "
                             "remove it first)" % _d)
    if os.path.exists(out) and not force:
        raise SystemExit("--init: %s exists — refusing to overwrite (re-run "
                         "with --force to replace it)" % out)
    import shlex
    q = shlex.quote
    body_c = _chain(fp["body"], p["body"], "body", p["have"])
    disp_c = _chain(fp["display"], p["display"], "display", p["have"])

    def head_names(src: str) -> tuple[re.Match[str] | None, re.Match[str] | None]:
        g: Callable[[str], re.Match[str] | None] = lambda k: re.search(r'^#let %s = \("([^"]+)"' % k, src, re.M)
        return g("bodyf"), g("dispf")
    # pair B iff the drawn faces are the second pair's lead faces
    pick_file, best = "resume.typ", -1
    for fn in ("resume.typ", "resume-pair-b.typ"):
        fpth = os.path.join(fdir, fn)
        if not os.path.exists(fpth):
            continue
        b, ds = head_names(open(fpth, encoding="utf-8").read())
        score = (b is not None and b.group(1) == p["body"][0]) + \
                (ds is not None and ds.group(1) == p["display"][0])
        if score > best or (score == best and fn == "resume.typ"):
            pick_file, best = fn, score
    src = open(os.path.join(fdir, pick_file), encoding="utf-8").read()
    # family files import the shared lib by repo-relative path; the starter has
    # lib.typ/icons.typ copied beside it, so point the import there.
    src = src.replace('#import "../../lib.typ"', '#import "lib.typ"')

    def lead(name: str) -> str:                       # keep `#let name = ` + trailing // note
        return r'^(#let %s = )[^\n]*?(\s*//[^\n]*)?$' % name

    def accent_line(name: str, val: str) -> tuple[str, Callable[[re.Match[str]], str]]:
        # gutter-rail: `if screen { rgb(A) } else { rgb(B) }` — drawn value is
        # the print branch; keep the screen branch as shipped.
        m = re.search(r'^#let %s = if screen \{ (rgb\("[^"]+"\)) \} else '
                      r'\{ rgb\("[^"]+"\) \}' % name, src, re.M)
        if m:
            return (r'^(#let %s = if screen \{ rgb\("[^"]+"\) \} else \{ )'
                    r'rgb\("[^"]+"\)( \}.*)$' % name,
                    lambda mm: mm.group(1) + 'rgb("%s")' % val + mm.group(2))
        return (lead(name),
                lambda mm: mm.group(1) + 'rgb("%s")' % val + (mm.group(2) or ""))
    pat, afn = accent_line("accent", p["accent"])
    src = _sub1(src, pat, afn, "#let accent", fam)
    if p["accent2"]:
        pat, afn = accent_line("accent2", p["accent2"])
        src = _sub1(src, pat, afn, "#let accent2", fam)
    sub: Callable[[str], Callable[[re.Match[str]], str]] = lambda v: (lambda mm: mm.group(1) + v + (mm.group(2) or ""))
    src = _sub1(src, lead("bodyf"), sub(body_c), "#let bodyf", fam)
    if re.search(r'^#let dispf = monof\b', src, re.M):
        # mono-technical: the display face IS the mono face
        src = _sub1(src, lead("monof"), sub(disp_c), "#let monof", fam)
    else:
        src = _sub1(src, lead("dispf"), sub(disp_c), "#let dispf", fam)
        if p["mono"]:
            src = _sub1(src, lead("monof"), sub(
                _chain(fp["mono"], p["mono"], "mono", p["have"])),
                "#let monof", fam)
    if lang != "en" or region:            # worked files ship lang: "en"
        src, n_lang = re.subn(r'(#set text\([^\n]*?)lang: "en"',
                     lambda mm: mm.group(1) + lang_arg(lang, region), src,
                     count=1)
        if n_lang != 1:
            raise SystemExit("--init: %s: no `lang: \"en\"` in its `#set text(` line to rewrite "
                             "— the family file changed shape; fall back to the manual route "
                             "(cp + --emit-typ)" % fam)
    src = _sub1(src, r'^(#set par\(justify: false, )leading: [^,]+, spacing: '
                r'[^)]+(\).*)$',
                lambda mm: mm.group(1) + "leading: %s, spacing: %s" % (
                    d["leading"], d["spacing"]) + mm.group(2),
                "#set par", fam)
    src = _sub1(src, r'^(#let mk = marks\(ic-col)(\).*)$',
                lambda mm: mm.group(1) + ', kit: "%s"' % p["markset"][0]
                + mm.group(2), "#let mk", fam)
    if p["variant"]:                      # gutter-rail's square/pill axis
        r = "2.5pt" if "pill" in p["variant"] else "0pt"
        src = _sub1(src, r'^(#let seg-radius = )\S+', lambda mm: mm.group(1) + r,
                    "#let seg-radius", fam)
    src = _apply_labels(src, d["labels"], p["labels"], fam)
    pg = d["page"]
    for k, v in (("margin", pg["margin"]), ("body", pg["body"])):
        if k == "margin" and "(%s)" % v not in src and v not in src:
            sys.stderr.write("note: %s's own page margin differs from the "
                             "recipe's (%s) — kept the family file's\n"
                             % (fam, v))
    os.makedirs(folder, exist_ok=True)
    kept = []
    for f in ("lib.typ", "icons.typ"):
        srcf, dst = os.path.join(root, "templates", f), os.path.join(folder, f)
        if os.path.exists(dst):
            if f == "lib.typ" and open(dst, "rb").read() != open(srcf, "rb").read():
                kept.append("kept existing %s (differs from the skill's) — a lib "
                            "update is deliberate: cp %s %s"
                            % (q(dst), q(srcf), q(dst)))
                continue
            if f == "icons.typ" and os.path.getsize(dst) > 0:
                kept.append("kept existing %s (harvested icons)" % q(dst))
                continue
        _write_nofollow(dst, open(srcf, "rb").read())
    # one comment line: the full call form of the family's entry wrapper
    src = re.sub(r'^(#job\()', r'// job(role, org, dates, note) - 4 positional args, "note" required; '
                 r'bullets follow as "- ..." lines\n\1', src, count=1, flags=re.M)
    _write_nofollow(out, (_vitae_header(pg) + "\n" + src).encode("utf-8"))
    lo, hi = pg["fill"].split("-")
    if any((cast(str, p.get(k)) or "").startswith("NO pool member")
           for k in ("display_note", "body_note", "mono_note")):
        kept.append("at least one font role of %s has NO pool member installed "
                    "locally — install the face above before verifying%s"
                    % (fam, "" if p["offline"] else
                       ", or in an offline sandbox re-run pick_design.py "
                       "with --offline --force"))
    print("wrote %s  (%s from families/%s/%s; lib.typ + icons.typ copied "
          "byte-for-byte)" % (out, fam, fam, pick_file))
    for k in kept:
        print("note: " + k)
    vf = q(os.path.join(root, "scripts", "verify.py"))
    print("next, run these (do not read the scripts, their output is the "
          "instruction):")
    print("  python3 %s %s" % (q(os.path.join(root, "scripts", "harvest_icons.py")), q(folder)))
    print("  python3 %s --tune %s 1 %s %s" % (vf, q(out), lo, hi))
    print("  python3 %s %s 1 %s %s" % (vf, q(out), lo, hi))
    print("The filler starter may overflow/underfill with the drawn fonts: expected. "
          "Replace the filler with the candidate's facts first, then --tune, then verify.")

#!/usr/bin/env python3
"""Measure the vertical rhythm of a rendered family: wrapped-line pitch < bullet pitch < entry pitch < section pitch.

    python tests/rhythm_measure.py templates/families/<f>/resume.typ     # compiles a copy with lengthened bullets
    python tests/rhythm_measure.py some.pdf                              # measures the PDF as it is

Pitch = distance between the bottoms (yMax) of two consecutive text lines, in pt, read from
`pdftotext -bbox-layout`. For a .typ the first two bullets of the first job get a long tail so they wrap
(the template's own bullets are placeholders, one line each); the copy is written next to the original
(its `#import "../../lib.typ"` must resolve) and removed afterwards. Rows are keyed on the placeholder
text "[Action verb]" / "[Role" (bullets and role lines of a shipped template); a PDF of a real CV needs
--bullet / --role regexes. The main column is the x-range of the bullet lines, so sidebars and 2-column
layouts do not leak in. Prints one line; exit 1 when the order wrap < bullet < entry < section (by >= STEP pt)
is not met, 2 when the document has no recognisable rows. Stdlib + typst + pdftotext only."""
import argparse
import os
import re
import subprocess
import sys
import tempfile

STEP = 1.5
TAIL = " — extended so that this bullet runs on to a second line of the same paragraph, with enough extra words to wrap on any measure"
LINE = re.compile(r'<line xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="([\d.]+)">(.*?)</line>', re.S)


def lengthen(src: str, bullet: str) -> str:
    out, n = [], 0
    for ln in src.split("\n"):
        if n < 2 and re.match(r"-\s+" + bullet, ln):
            ln = ln.rstrip() + TAIL
            n += 1
        out.append(ln)
    return "\n".join(out)


def to_pdf(path: str, bullet: str, work: str) -> str:
    if path.endswith(".pdf"):
        return path
    d = os.path.dirname(os.path.abspath(path))
    tmp = os.path.join(d, ".rhythm-measure-tmp.typ")
    pdf = os.path.join(work, "m.pdf")
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(lengthen(open(path, encoding="utf-8").read(), bullet))
        root = d
        while root != os.path.dirname(root) and not os.path.exists(os.path.join(root, "templates", "lib.typ")):
            root = os.path.dirname(root)
        r = subprocess.run(["typst", "compile", "--root", root, tmp, pdf], capture_output=True, text=True)
        if r.returncode:
            sys.exit("typst compile failed:\n" + r.stderr)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)
    return pdf


def lines_of(pdf: str, work: str):
    html = os.path.join(work, "m.html")
    subprocess.run(["pdftotext", "-bbox-layout", pdf, html], check=True)
    pages = open(html, encoding="utf-8").read().split("<page ")[1:]
    out = []
    for pi, p in enumerate(pages):
        for m in LINE.finditer(p):
            words = re.findall(r">([^<]+)</word>", m.group(5))
            out.append((pi, float(m.group(4)), float(m.group(1)), float(m.group(3)), " ".join(words)))
    return out


def measure(L, bullet: str, role: str):
    isb = lambda t: re.match(bullet, t) is not None
    bl = [l for l in L if isb(l[4])]
    if not bl:
        return None
    bx = min(l[2] for l in bl)
    bxmax = max(l[3] for l in bl)
    col = sorted((l for l in L if bx - 30 <= l[2] < bxmax and l[3] <= bxmax + 40), key=lambda l: (l[0], l[1]))
    rows: list[tuple[int, float, float, float, str]] = []     # one row per baseline: role + date, number + title
    for l in col:
        if rows and rows[-1][0] == l[0] and abs(rows[-1][1] - l[1]) < 2.0:
            r = rows[-1]
            rows[-1] = (r[0], r[1], min(r[2], l[2]), max(r[3], l[3]), r[4] + " " + l[4] if l[2] > r[2] else l[4] + " " + r[4])
        else:
            rows.append(l)
    col = rows
    ib = [k for k, l in enumerate(col) if isb(l[4])]
    k0 = ib[0]
    wrap = col[k0 + 1][1] - col[k0][1]
    pairs = [k for k in range(len(col) - 1) if isb(col[k][4]) and isb(col[k + 1][4]) and col[k][0] == col[k + 1][0]
             and k > k0 + 1]
    bul = col[pairs[0] + 1][1] - col[pairs[0]][1] if pairs else float("nan")
    rk = [k for k in range(k0, len(col)) if re.match(role, col[k][4])]
    ent = col[rk[0]][1] - col[rk[0] - 1][1] if rk else float("nan")
    sec, head = float("nan"), ""
    for k in reversed(ib):
        if k + 1 < len(col) and col[k + 1][0] == col[k][0] and not isb(col[k + 1][4]):
            sec, head = col[k + 1][1] - col[k][1], col[k + 1][4][:24]
            break
    return wrap, bul, ent, sec, head


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("file", help=".typ template or .pdf")
    ap.add_argument("--bullet", default=r"\[Action verb\]", help="regex a bullet line starts with")
    ap.add_argument("--role", default=r"\[Role", help="regex a job role line starts with")
    a = ap.parse_args()
    with tempfile.TemporaryDirectory() as work:
        m = measure(lines_of(to_pdf(a.file, a.bullet, work), work), a.bullet, a.role)
    if m is None:
        print("no bullet lines matched --bullet", file=sys.stderr)
        return 2
    w, b, e, s, head = m
    name = os.path.basename(os.path.dirname(os.path.abspath(a.file))) + "/" + os.path.basename(a.file)
    ok = w + STEP <= b and b + STEP <= e and e + STEP <= s
    print(f"{name:34s} wrap {w:5.1f} < bullet {b:5.1f} < entry {e:5.1f} < section {s:5.1f}  "
          f"{'OK' if ok else 'ORDER VIOLATED'}  (next after last bullet: '{head}')")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

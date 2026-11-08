"""Typst compile, page count and PNG render, native CLI or typst-py (a leaf under verify_env: no `import verify`).

Compile, page count, text and word-box extraction, and raster/crop rendering.
"""
from __future__ import annotations

import glob
import html
import importlib
import math
import os
import re
import shutil
import subprocess
import tempfile
from collections.abc import Sequence
from typing import Any, Literal, cast, overload

from PIL import Image

from vitae.core.base import HIDDEN_PPI, Box, WordBox
from vitae.core.env import PdfBackend, _importable, pdf_backend, typst_font_kw, typst_py
from vitae.verify.page import CROP_CAP, CROP_PAD_IN, CROP_PPI, CROP_SCAN_PPI, crop_candidates
from vitae.verify.typst import _strip_typst_comments

# ---------- compile / page-count / extraction, native or fallback ----------

def auto_root(typ: str) -> str | None:
    """Typst project root a file needs, or None for the default (its own folder).

    The reference family files import the shared mechanics by relative path
    (`#import "../../lib.typ"`), which Typst refuses unless `--root` is an ancestor
    holding both. Climb as many levels as the deepest leading `../` of a
    non-comment import; a CV folder (`#import "lib.typ"`) needs nothing."""
    try:
        with open(typ, encoding="utf-8-sig", errors="replace") as fh:
            src = _strip_typst_comments(fh.read())
    except OSError:
        return None
    ups = max((len(m.group(1)) // 3 for m in re.finditer(r'\bimport\s*\(?\s*"((?:\.\./)+)[^"]*\.typ"', src)), default=0)
    root = os.path.dirname(os.path.abspath(typ))
    for _ in range(ups):
        root = os.path.dirname(root)
    return root if ups else None


# auto_root as a typst-py keyword and as CLI flags; empty when the default root (the file's own folder) is right.
def _root_kw(typ: str) -> dict[str, str]:
    r = auto_root(typ)
    return {"root": r} if r else {}


def _root_cli(typ: str) -> list[str]:
    r = auto_root(typ)
    return ["--root", r] if r else []


def compile_pdf(typ: str, pdf: str, use_cli: bool) -> tuple[bool, str]:
    """Returns (ok, stderr_text)."""
    if use_cli:
        r = subprocess.run(["typst", "compile", os.path.abspath(typ), os.path.abspath(pdf)] + _root_cli(typ), capture_output=True, text=True)
        return r.returncode == 0, (r.stdout + r.stderr)
    try:
        typst: Any = importlib.import_module("typst")
        typst.compile(typ, output=pdf, **_root_kw(typ), **typst_font_kw())
        return True, ""
    except Exception as e:
        return False, str(e)


def render_pngs(typ: str, tmp_dir: str, use_cli: bool) -> list[str]:
    """One 90 ppi PNG per page, the raster the fill scan reads (the hidden-text gate renders its own, at HIDDEN_PPI).
    The second typst-py call is for a version whose compile() does not take `ppi`."""
    pattern = os.path.join(tmp_dir, "p{p}.png")
    if use_cli:
        subprocess.run(["typst", "compile", os.path.abspath(typ), os.path.abspath(pattern), "--format", "png", "--ppi", "90"] + _root_cli(typ),
                        capture_output=True, text=True)
    else:
        typst: Any = importlib.import_module("typst")
        try:
            typst.compile(typ, output=pattern, format="png", ppi=90, **_root_kw(typ), **typst_font_kw())
        except TypeError:
            typst.compile(typ, output=pattern, format="png", **_root_kw(typ), **typst_font_kw())
    return sorted(glob.glob(os.path.join(tmp_dir, "p*.png")))


def _pdfium_doc(pdf: str) -> Any:
    return importlib.import_module("pypdfium2").PdfDocument(pdf)


def count_pages(pdf: str, backend: PdfBackend) -> str | None:
    """The page count as text, compared with EXPECTED_PAGES as text; None when pdfinfo prints no Pages line."""
    if backend == "pdfium":
        return str(len(_pdfium_doc(pdf)))
    if backend == "poppler":
        out = subprocess.run(["pdfinfo", pdf], capture_output=True, text=True).stdout
        for line in out.splitlines():
            if line.startswith("Pages:"):
                return line.split()[1]
        return None
    pypdf: Any = importlib.import_module("pypdf")
    return str(len(pypdf.PdfReader(pdf).pages))


def ensure_icons(typ: str) -> None:
    """Guarantee an `icons.typ` beside the file being compiled.

    `lib.typ` does `#import "icons.typ": *`, and Typst resolves that against
    the importing file, so the deliverable folder needs one. Step 4 of
    SKILL.md copies the repo's EMPTY fallback there along with `lib.typ`, and
    `harvest_icons.py <folder>` overwrites it with the fetched path data. This
    covers the one case those two miss: a folder where the copy was forgotten
    — copy the empty fallback instead of failing the compile with a Typst
    import error. No network here; fetching stays harvest_icons.py's job.
    """
    if auto_root(typ):                 # reference family file: lib.typ/icons.typ live in templates/
        return
    d = os.path.dirname(os.path.abspath(typ))
    dst = os.path.join(d, "icons.typ")
    if os.path.islink(dst):            # never write through a symlink
        if not os.path.exists(dst):
            print(f"WARN  {dst} is a dangling symlink — not writing through it; "
                  f"replace it with a regular file")
        return
    if not os.path.exists(dst):
        src = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__))))), "templates", "icons.typ")
        if not os.path.exists(src):    # no repo fallback (nothing to copy)
            return
        fd = os.open(dst, os.O_WRONLY | os.O_CREAT | os.O_EXCL
                     | getattr(os, "O_NOFOLLOW", 0), 0o644)
        with os.fdopen(fd, "wb") as fh, open(src, "rb") as sf:
            fh.write(sf.read())
        print(f"NOTE  copied the empty fallback icons.typ into {d} — run "
              f"scripts/harvest_icons.py there for the real marks")


def typst_compile(src: str, pdf: str | None = None) -> tuple[bool, str]:
    """(ok, stderr) for `typst compile src [pdf]` via the CLI, else typst-py
    (the selftests' compile step; warnings are included in the text)."""
    if shutil.which("typst"):
        r = subprocess.run(["typst", "compile", src] + ([pdf] if pdf else []) + _root_cli(src), capture_output=True, text=True)
        return r.returncode == 0, r.stderr
    mod = typst_py() or importlib.import_module("typst")
    try:
        res = mod.Compiler(src, **_root_kw(src), **typst_font_kw()).compile_with_warnings(output=pdf or os.path.splitext(src)[0] + ".pdf")
        warns = res[1] if isinstance(res, tuple) and len(res) > 1 else []
        return True, "\n".join(str(w) for w in warns or [])
    except Exception as e:
        return False, str(e)


LINE_GAP = 1.0


def _pdfium_page_text(pg: Any) -> str:
    """pypdfium2's page text with its lines cut like pdftotext's. pdfium joins cells that
    share a baseline (a contact row, a left-flushed role and its right-flushed date) into one
    line; a new line starts where the gap to the previous character exceeds LINE_GAP (1.0) x the box height. That
    value was picked by search against pdftotext's line counts: poppler's own cut is not purely geometric, and
    `_reading_order` cuts its pieces at 1.5 x for a different purpose (reading order). A gap with whitespace in it
    becomes the newline; a gap without any gets one inserted. Trailing blanks are dropped."""
    tp = pg.get_textpage()
    if not tp.count_chars():
        return ""
    text = tp.get_text_range()
    out: list[str] = []
    prev: tuple[float, float, float, float] | None = None
    idx = 0
    pending = ""                                   # whitespace seen since the last glyph
    for ch in text:
        i, idx = idx, idx + (2 if ord(ch) > 0xFFFF else 1)
        if ch.isspace() or ord(ch) < 0x20:
            if ch in "\r\n":
                prev = None
            pending += ch
            continue
        box = tp.get_charbox(i, loose=True)
        if box[2] <= box[0] or box[3] <= box[1]:
            out.append(pending + ch)
            pending = ""
            continue
        if prev is not None and "\n" not in pending:
            height = min(prev[3] - prev[1], box[3] - box[1])
            same_row = abs((prev[1] + prev[3]) / 2 - (box[1] + box[3]) / 2) <= 0.4 * height
            if same_row and box[0] - prev[2] > LINE_GAP * height:
                pending = "\n"
        out.append(pending.rstrip(" \t") if "\n" in pending else pending)
        out.append(ch)
        pending = ""
        prev = (box[0], box[1], box[2], box[3])
    out.append(pending)
    return "".join(out)


def extract_text(pdf: str, backend: PdfBackend) -> str:
    """The PDF text the ATS checks read, in pdftotext's shape whatever the backend. pypdf's is indicative only."""
    if backend == "poppler":
        return subprocess.run(["pdftotext", pdf, "-"], capture_output=True, text=True).stdout
    if backend == "pdfium":
        # pdftotext's shape: pages end with \f (a blank line before it), lines with \n
        return "".join(t.replace("\r\n", "\n").rstrip("\n") + "\n\n\f"
                       for t in (_pdfium_page_text(pg) for pg in _pdfium_doc(pdf)))
    pypdf: Any = importlib.import_module("pypdf")
    reader = pypdf.PdfReader(pdf)
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def family_from_path(path: str) -> str | None:
    """The family this CV is built from, for the DEVICELESS exemption and the drawn fill target (_drawn_fill).

    Read from the `// FAMILY: <name>` banner every template carries on line 1,
    NOT from the directory. A delivered CV is a copy of the template living in
    the user's own folder (SKILL.md: "delivered copies are retailoring"), so a
    path-only rule exempts the template and fails the very file the skill
    ships — measured: a copy of `humanist-quiet` outside the tree FAILed the
    quorum while the family is legitimately device-less. The banner travels
    with the copy; the path does not. Directory name is the fallback, for a
    file whose banner was edited away."""
    try:
        with open(path, encoding="utf-8") as fh:
            head = "".join(fh.readline() for _ in range(3))   # line 1 may be the `// vitae:` header
        m = re.search(r"^\s*//\s*FAMILY:\s*([\w-]+)", head, re.M)
        if m:
            return m.group(1)
    except OSError:
        pass
    parts = os.path.normpath(path).split(os.sep)
    if "families" in parts:
        i = parts.index("families")
        if i + 1 < len(parts):
            return parts[i + 1]
    return None


@overload
def word_boxes(pdf: str, with_text: Literal[False] = ...) -> list[list[Box]] | None: ...


@overload
def word_boxes(pdf: str, with_text: Literal[True]) -> list[list[WordBox]] | None: ...


@overload
def word_boxes(pdf: str, with_text: bool) -> list[list[Box]] | list[list[WordBox]] | None: ...


def word_boxes(pdf: str, with_text: bool = False) -> list[list[Box]] | list[list[WordBox]] | None:
    """Per-page list of pdftotext word boxes (x0, y0, x1, y1) in PDF points.

    With `with_text` each item is ((x0, y0, x1, y1), word) instead.

    Returns None (not a list of empties) when pdftotext is missing or fails,
    so callers can tell "no text found" from "couldn't check" and degrade to
    the ink-only detector rather than treating every row as furniture.
    """
    pages = _bbox_pages(pdf)
    if pages is None:
        return None
    if with_text:
        return [items for _, _, items in pages]
    return [[b for b, _ in items] for _, _, items in pages]


def _bbox_pages(pdf: str) -> list[tuple[float, float, list[WordBox]]] | None:
    """[(page_w, page_h, [((x0, y0, x1, y1), word), ...]), ...] from
    `pdftotext -bbox` (PDF points), or None when pdftotext is missing/fails.
    With the pdfium backend the words are built from pypdfium2's character boxes."""
    if pdf_backend() == "pdfium":
        return _pdfium_bbox_pages(pdf)[0]
    try:
        r = subprocess.run(["pdftotext", "-bbox", pdf, "-"],
                            capture_output=True, text=True)
    except (FileNotFoundError, OSError):
        return None
    if r.returncode != 0:
        return None
    pages = []
    for pg in r.stdout.split("<page ")[1:]:
        dim = re.match(r'width="([\d.]+)" height="([\d.]+)"', pg)
        items = [((float(m[1]), float(m[2]), float(m[3]), float(m[4])), html.unescape(m[5]))
                 for m in re.finditer(r'<word xMin="([-\d.]+)" yMin="([-\d.]+)" '
                                      r'xMax="([-\d.]+)" yMax="([-\d.]+)">([^<]*)</word>', pg)]
        pages.append((float(dim[1]) if dim else 0.0, float(dim[2]) if dim else 0.0, items))
    return pages


def _reading_order(words: list[WordBox]) -> list[WordBox]:
    """pdftotext's reading order, approximated: pdfium lists words in content-stream
    order, poppler in layout order. Words on one baseline form a line, cut where the gap
    exceeds 1.5 x the box height (a right-flushed date is another piece); a piece joins
    every piece directly above it that it overlaps in x (one text block); blocks read by
    row then x, lines within a block top to bottom, left to right. A right-flushed date
    joins the first line under it that overlaps its x-range, up to the next dated head, so
    it is read in place only then, which is the behaviour `check_date_adjacency` measures."""
    if not words:
        return words
    rows: list[list[int]] = []
    for i in sorted(range(len(words)), key=lambda k: (words[k][0][1] + words[k][0][3]) / 2):
        wb = words[i][0]
        yc, hh = (wb[1] + wb[3]) / 2, wb[3] - wb[1]
        if rows:
            rb = [words[k][0] for k in rows[-1]]
            ryc = sum((q[1] + q[3]) / 2 for q in rb) / len(rb)
            # 0.4x box height (~4pt on 10pt text): keeps bold/regular or small-caps words on one baseline together
            if abs(yc - ryc) <= 0.4 * min(hh, min(q[3] - q[1] for q in rb)):
                rows[-1].append(i)
                continue
        rows.append([i])
    pieces: list[list[int]] = []                       # word indexes, left to right, one row each
    piece_row: list[int] = []
    for r, row in enumerate(rows):
        cur: list[int] = []
        for i in sorted(row, key=lambda k: words[k][0][0]):
            if cur:
                prev = words[cur[-1]][0]
                # >1.5x box height (~15pt): wider than word/separator spacing, splits a right-flushed date or column cell
                if words[i][0][0] - prev[2] > 1.5 * min(prev[3] - prev[1], words[i][0][3] - words[i][0][1]):
                    pieces.append(cur)
                    piece_row.append(r)
                    cur = []
            cur.append(i)
        pieces.append(cur)
        piece_row.append(r)
    geo = [(min(words[k][0][0] for k in pc), max(words[k][0][2] for k in pc),
            min(words[k][0][1] for k in pc), max(words[k][0][3] for k in pc)) for pc in pieces]
    parent = list(range(len(pieces)))

    def find(a: int) -> int:
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a
    for lo in range(len(pieces)):
        for up in range(len(pieces)):
            if piece_row[up] == piece_row[lo] - 1 and geo[up][0] < geo[lo][1] and geo[lo][0] < geo[up][1]:
                parent[find(up)] = find(lo)
    # A piece with another piece to its left on its row (a right-flushed date beside its role) is
    # read after the lines of its entry, at any distance, unless one of them under it overlaps its
    # x-range: then it is read in place. Measured on poppler: role, org, date at every head-to-org
    # gap from 4 to 200 pt and heads of 9 to 18 pt, so there is no distance cutoff. The lines of
    # its entry stop at the next row that holds a right-flushed piece (the next dated head).
    side = [n for n in range(len(pieces)) if any(piece_row[m] == piece_row[n] and geo[m][0] < geo[n][0]
                                                 for m in range(len(pieces)))]
    for n in side:
        stop = min((piece_row[m] for m in side if piece_row[m] > piece_row[n]), default=len(rows))
        under = [m for m in range(len(pieces)) if piece_row[n] < piece_row[m] < stop and m not in side
                 and geo[m][0] < geo[n][1] and geo[n][0] < geo[m][1]]
        if under:
            parent[find(n)] = find(min(under, key=lambda m: (piece_row[m], geo[m][0])))
    blocks: dict[int, list[int]] = {}
    for n in range(len(pieces)):
        blocks.setdefault(find(n), []).append(n)
    # by row (the rows are clustered on the baseline with a tolerance), not by the box top: a bold role
    # and a regular date of one size differ by a point or two of box top
    order = sorted(blocks.values(), key=lambda bl: (min(piece_row[n] for n in bl), min(geo[n][0] for n in bl)))
    return [words[k] for bl in order for n in sorted(bl, key=lambda n: (piece_row[n], geo[n][0])) for k in pieces[n]]


def _boxes_unavailable(pdf: str) -> str:
    """Why `word_boxes` returned None on `pdf`, for the WARN that says a gate was skipped.
    Only reached on that failure path, so the pdfium read is repeated to get its error."""
    if pdf_backend() == "pdfium":
        return f"pypdfium2 could not read the PDF ({_pdfium_bbox_pages(pdf)[1] or 'unknown error'})"
    return "pdftotext not found (install poppler-utils)"


def _pdfium_bbox_pages(pdf: str) -> tuple[list[tuple[float, float, list[WordBox]]] | None, str | None]:
    """`_bbox_pages` on pypdfium2: words are runs of non-space characters, each box the union of its loose character
    boxes (top-down, like pdftotext). LOOSE boxes, because pdfium's tight ones are ink extents and vary with the
    letters (a word without descenders is shorter), while the loose ones follow the font's ascent and descent like
    poppler's word boxes. Measured on the shipped templates against `pdftotext -bbox`: x within 0.8 pt, y within ~1
    pt for most fonts; tight boxes padded by 2.5 pt per side were off by up to 10 pt and cut one hard-edge line out
    of its band, a FAIL poppler does not give. Returns (pages, None), or (None, why) when pypdfium2 fails."""
    try:
        doc = _pdfium_doc(pdf)
        pdfium_raw: Any = importlib.import_module("pypdfium2.raw")
        pages: list[tuple[float, float, list[WordBox]]] = []
        for pg in doc:
            pw, ph = pg.get_size()
            tp = pg.get_textpage()
            text = tp.get_text_range() if tp.count_chars() else ""
            items: list[WordBox] = []
            chars: list[str] = []
            box: list[float] = []
            size: list[float] = [0.0]

            def flush(chars: list[str] = chars, box: list[float] = box, items: list[WordBox] = items,
                      size: list[float] = size, ph: float = ph) -> None:
                if chars and box:
                    # a mark pdfium splits off a word (Arabic dots, accents) has a sliver of a box:
                    # never under the font size, like the line it belongs to in poppler's boxes
                    grow = max(0.0, size[0] - (box[3] - box[1])) / 2
                    items.append(((box[0], ph - box[3] - grow, box[2], ph - box[1] + grow), "".join(chars)))
                chars.clear()
                box.clear()
                size[0] = 0.0
            idx = 0
            for ch in text:
                i, idx = idx, idx + (2 if ord(ch) > 0xFFFF else 1)   # pdfium counts UTF-16 units
                if ch.isspace() or ord(ch) < 0x20:
                    flush()
                    continue
                l, b, r, t = tp.get_charbox(i, loose=True)
                if r <= l or t <= b:
                    continue
                chars.append(ch)
                size[0] = max(size[0], float(pdfium_raw.FPDFText_GetFontSize(tp, i)))
                if box:
                    box[:] = [min(box[0], l), min(box[1], b), max(box[2], r), max(box[3], t)]
                else:
                    box[:] = [l, b, r, t]
            flush()
            pages.append((float(pw), float(ph), _reading_order(items)))
        return pages, None
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"[:120]


def _pdfium_render(pdf: str, ppi: int, gray: bool = False, pages: Sequence[int] | None = None) -> list[Image.Image]:
    """One PIL image per page (1-based `pages`, default all) rendered by pypdfium2, cropped to
    the size pdftoppm gives (pdfium rounds a page's pixel size up one row more often)."""
    doc = _pdfium_doc(pdf)
    scale = ppi / 72.0
    out: list[Image.Image] = []
    for n in (pages if pages is not None else range(1, len(doc) + 1)):
        pg = doc[n - 1]
        pw, ph = pg.get_size()
        im = pg.render(scale=scale, grayscale=gray).to_pil()
        want = (math.ceil(pw * scale - 1e-3), math.ceil(ph * scale - 1e-3))
        if im.size[0] > want[0] or im.size[1] > want[1]:
            im = im.crop((0, 0, min(im.size[0], want[0]), min(im.size[1], want[1])))
        out.append(im.convert("L" if gray else "RGB"))
    return out


def _render_pages_png(pdf: str, tmp: str, ppi: int = HIDDEN_PPI) -> list[str]:
    """PNG per page via pdftoppm (poppler) or pypdfium2, or [] when neither is there."""
    if pdf_backend() == "pdfium":
        paths = []
        for n, im in enumerate(_pdfium_render(pdf, ppi), 1):
            paths.append(os.path.join(tmp, f"h-{n}.png"))
            im.save(paths[-1])
        return paths
    if not shutil.which("pdftoppm"):
        return []
    subprocess.run(["pdftoppm", "-r", str(ppi), "-png", pdf, os.path.join(tmp, "h")],
                   capture_output=True, text=True)
    return sorted(glob.glob(os.path.join(tmp, "h*.png")),
                  key=lambda f: int(cast(re.Match[str], re.search(r"(\d+)\.png$", f)).group(1)))


def pdf_unreadable(pdf: str) -> bool:
    """True when the PDF backend cannot open `pdf` (not a PDF, corrupt): header, then a page count."""
    try:
        with open(pdf, "rb") as fh:
            if b"%PDF" not in fh.read(1024):
                return True
        backend = pdf_backend()
        return backend is not None and not count_pages(pdf, backend)
    except Exception:
        return True


def render_pages(pdf: str, out_dir: str, ppi: int) -> list[str]:
    """`<stem>-p<N>.png` per page in out_dir: pypdfium2 when it imports, else pdftoppm.
    Returns the paths, or [] when neither is there."""
    os.makedirs(out_dir, exist_ok=True)
    stem = os.path.splitext(os.path.basename(pdf))[0]
    stale = re.compile(r"%s-p\d+(?:-(?:fill|icon)\d+)?\.png" % re.escape(stem))

    def drop_stale() -> None:        # a longer previous render, or one with --crops, must not leave its pages or crops behind
        for f in os.listdir(out_dir):
            if stale.fullmatch(f):
                os.remove(os.path.join(out_dir, f))
    if _importable("pypdfium2"):
        paths = []
        ims = _pdfium_render(pdf, ppi)
        drop_stale()
        for n, im in enumerate(ims, 1):
            paths.append(os.path.join(out_dir, f"{stem}-p{n}.png"))
            im.save(paths[-1])
        return paths
    if not shutil.which("pdftoppm"):
        return []
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(["pdftoppm", "-r", str(ppi), "-png", pdf, os.path.join(tmp, "p")],
                       capture_output=True, text=True)
        paths = []
        drop_stale()
        for f in sorted(glob.glob(os.path.join(tmp, "p*.png")),
                        key=lambda f: int(cast(re.Match[str], re.search(r"(\d+)\.png$", f)).group(1))):
            n = int(cast(re.Match[str], re.search(r"(\d+)\.png$", f)).group(1))
            paths.append(os.path.join(out_dir, f"{stem}-p{n}.png"))
            shutil.move(f, paths[-1])
    return paths


def _page_rasters(pdf: str, ppi: int) -> list[Image.Image]:
    """One RGB PIL image per page, the way render_pages picks its backend; [] when neither is there."""
    if _importable("pypdfium2"):
        return _pdfium_render(pdf, ppi)
    if not shutil.which("pdftoppm"):
        return []
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(["pdftoppm", "-r", str(ppi), "-png", pdf, os.path.join(tmp, "c")],
                       capture_output=True, text=True)
        files = sorted(glob.glob(os.path.join(tmp, "c*.png")),
                       key=lambda f: int(cast(re.Match[str], re.search(r"(\d+)\.png$", f)).group(1)))
        out = []
        for f in files:
            with Image.open(f) as fh:
                out.append(fh.convert("RGB"))
        return out


def render_crops(pdf: str, out_dir: str) -> tuple[list[str], list[str]]:
    """`<stem>-p<N>-<band>.png` at CROP_PPI for the bands at visual risk (solid fills, icons),
    band = fill1, icon2, ... counted per kind in reading order. At most CROP_CAP per page, fills
    first, then the icons with the most ink. Crops of this stem from an earlier run are removed
    first. Returns (paths, notes naming the bands dropped by the cap)."""
    stem = os.path.splitext(os.path.basename(pdf))[0]
    scan = _page_rasters(pdf, CROP_SCAN_PPI)
    if not scan:
        return [], []
    boxes = word_boxes(pdf)
    big = _page_rasters(pdf, CROP_PPI)
    old_crops = re.compile(r"%s-p\d+-(?:fill|icon)\d+\.png" % re.escape(stem))
    if os.path.isdir(out_dir):
        for f in os.listdir(out_dir):        # a run with fewer bands must not leave the old ones beside it
            if old_crops.fullmatch(f):
                os.remove(os.path.join(out_dir, f))
    paths: list[str] = []
    notes: list[str] = []
    r = CROP_PPI / CROP_SCAN_PPI
    pad = CROP_PAD_IN * CROP_PPI
    for n, (sm, lg) in enumerate(zip(scan, big), 1):
        bands = crop_candidates(sm, boxes[n - 1] if boxes and n <= len(boxes) else None)
        count = {"fill": 0, "icon": 0}
        named = []
        score = {}
        for kind, box, sc in bands:
            count[kind] += 1
            named.append((f"{kind}{count[kind]}", kind, box))
            score[count[kind], kind] = sc
        ranked = [b for b in named if b[1] == "icon"]
        ranked.sort(key=lambda b: -score[int(b[0][4:]), "icon"])
        keep = ([b for b in named if b[1] == "fill"] + ranked)[:CROP_CAP]
        if len(named) > len(keep):
            notes.append(f"NOTE  crops: p.{n} capped at {CROP_CAP}, dropped "
                         + ", ".join(b[0] for b in named if b not in keep))
        for name, _, (x0, y0, x1, y1) in sorted(keep, key=lambda b: (b[2][1], b[2][0])):
            crop = lg.crop((max(0, int(x0 * r - pad)), max(0, int(y0 * r - pad)),
                            min(lg.size[0], int(x1 * r + pad)), min(lg.size[1], int(y1 * r + pad))))
            paths.append(os.path.join(out_dir, f"{stem}-p{n}-{name}.png"))
            crop.save(paths[-1])
    return paths, notes

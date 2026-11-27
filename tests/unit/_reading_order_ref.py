"""Reference oracle for tests: `vitae.verify.pdf._reading_order` as it was before the row index (O(P^2) in the pieces
of a page). Kept verbatim so the equivalence tests compare the fast version with the behaviour it replaced."""
from vitae.core.base import WordBox


def reading_order_quadratic(words: list[WordBox]) -> list[WordBox]:  # noqa: C901 (verbatim copy of the replaced code)
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

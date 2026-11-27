"""Synthetic word pages and lib marks for the grouping / bullet tests: a CV page as `pdftotext -bbox` would give it
(words with boxes, 12 pt line pitch) and the <vitae-head> / <vitae-bullet> marks lib.typ would emit for it."""
from vitae.core.base import HeadMark, Mark, WordBox

PITCH = 12.0


def cv_page(entries: int, bullets: int = 3, words_per_line: int = 12, page: int = 1, y0: float = 40.0,
            x0: float = 10.0) -> tuple[list[Mark], list[Mark], list[WordBox]]:
    """(head marks, bullet marks, words) of one page of `entries` entries: a head line, an org line, then `bullets`
    bullets of a full line and a short wrapped line each. Entry e's head words are `Role{e}`, `Org{e}`."""
    heads: list[Mark] = []
    bullet_marks: list[Mark] = []
    words: list[WordBox] = []
    y = y0

    def line(x: float, y: float, tokens: list[str]) -> None:
        for k, t in enumerate(tokens):
            words.append(((x + k * 34.0, y, x + k * 34.0 + 30.0, y + 9.0), t))

    for e in range(entries):
        heads.append(HeadMark(text=f"Role{e}", page=page, x=x0, y=y, kind="entry", org=f"Org{e}"))
        line(x0, y, [f"Role{e}", "at", f"Org{e}"])
        y += PITCH
        line(x0, y, [f"Org{e}", "Montreal", "2020"])
        y += PITCH
        for b in range(bullets):
            bullet_marks.append(Mark(text="•", page=page, x=x0 + 8, y=y, kind="bullet"))
            line(x0 + 20, y, [f"w{e}x{b}x{k}" for k in range(words_per_line)])
            y += PITCH
            line(x0 + 20, y, [f"end{e}x{b}"])
            y += PITCH
        y += 6.0
    return heads, bullet_marks, words

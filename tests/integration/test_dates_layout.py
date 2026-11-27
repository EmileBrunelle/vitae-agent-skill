"""Date adjacency on real Typst layouts: the lib `entry` markers plus the PDF reader's word order, on both toolchains
(typst CLI + poppler, then typst-py + pypdfium2). One page per case, one compile and one query per document.
"""
from __future__ import annotations

import shutil
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import pytest
from harness import ROOT
from vitae.core.base import Mark
from vitae.verify.groups import ENTRY_MARKS, _typst_query, check_date_adjacency
from vitae.verify.pdf import typst_compile, word_boxes

HEAD = ('#import "lib.typ": *\n#set page(width: 14cm, height: 12cm, margin: 2cm)\n#set text(size: 10pt)\n'
        '#let ok(r, o, d, ..b) = { entry(r, o, d, [Montreal · what the employer is, in one clause · full-time, hybrid])\n'
        '  b.pos().map(x => list(x)).join() }\n'
        # bad: the markers of lib `entry`, but the org line sits 2pt under the role row: pdftotext reads role, org, date
        '#let bad(r, o, d, ..b) = block[#grid(columns: (1fr, auto), align: (left + bottom, right + bottom),\n'
        '  [#head-mark("entry", r, org: o, dated: true)#text(size: 11pt, weight: "bold", r)],\n'
        '  [#part-mark("date", text(size: 9pt, d))#text(size: 9pt, d)])\n'
        '  #v(-8pt)\n  #text(size: 9pt)[#part-mark("org", o)#o]\n  #b.pos().map(x => list(x)).join()]\n'
        '#let wide(g, r, o, d, hs: 11pt, ds: 9pt) = block[#grid(columns: (1fr, auto), align: (left + bottom, right + bottom),\n'
        '  [#head-mark("entry", r, org: o, dated: true)#text(size: hs, weight: "bold", r)],\n'
        '  [#part-mark("date", text(size: ds, d))#text(size: ds, d)])\n'
        '  #v(g)\n  #text(size: 9pt)[#part-mark("org", o)#o]]\n'
        '#let inl(r, o, d) = block[#head-mark("entry", r, org: o, dated: true)#r #part-mark("org", o)#o \\\n'
        '  #part-mark("date", d)#d]\n'
        '#let bare(r, d) = entry(r, [], d, none)\n'
        '#let hbare(r, d) = block(above: 10pt, grid(columns: (1fr, auto), align: (left + bottom, right + bottom),\n'
        '  [#head-mark("entry", r, dated: true)#text(size: 11pt, weight: "bold", r)],\n'
        '  [#part-mark("date", text(size: 9pt, weight: "bold", d))#text(size: 9pt, weight: "bold", d)]))\n'
        '#let old(r, o) = block[#context [#metadata((kind: "entry", text: r, org: o, page: here().page(),\n'
        '  x: 0, y: 0)) <vitae-head>]#r \\ #o \\ 2020 – 2023]\n')
# Letter-width page for the date anchor: the date goes inline after the role when nothing reaches under it.
HEAD2 = ('#import "lib.typ": *\n#set page(width: 21.59cm, height: 14cm, margin: 1.5cm)\n#set text(size: 10pt)\n'
         '#let sec(t, body) = wd-section((t, b) => block(above: 9pt)[#strong(upper(t)) #b])(t, body)\n'
         '#let job(r, o, d, n) = entry(r, o, d, n)\n')
LONG = "Montréal · what the employer is, in one clause · full-time, hybrid, on-site three days a week, remote otherwise"
BULLET = "list([a long bullet that runs across])"


@dataclass(frozen=True)
class Case:
    name: str
    body: str
    verdict: str                   # "pass" | "fail" | "warn"
    inline: bool | None = None     # expected `inline` flag of the first date marker, when the case pins it


CASES = [
    # the org line stops short of the date (the trap) vs the lib order role -> date -> org
    Case("lib order", 'ok("Backend Developer", "Acme Corp", "Mar 2024 – present")', "pass"),
    Case("trap order", 'bad("Backend Developer", "Acme Corp", "Mar 2024 – present")', "fail"),
    Case("trap 12pt under the head", 'wide(12pt, "Senior Engineer", "Acme Corp", "2019")', "fail"),
    Case("trap 150pt under the head", 'wide(150pt, "Senior Engineer", "Acme Corp", "2019")', "fail"),
    Case("trap, bold 9pt head and date", 'wide(8pt, "Senior Engineer", "Acme Corp", "2019", hs: 9pt, ds: 9pt)', "fail"),
    Case("trap, 4-word org on the head line", 'inl("Engineer", "Acme Global Systems Ltd", "2020 – 2023")', "fail"),
    Case("trap, bullet number then date", 'bad("Engineer", "Acme Corp", "2020 – 2023", [Led 3 years of work])', "fail"),
    Case("trap, open-ended date", 'bad("Eng", "Acme", "03/24 – en cours")', "fail"),
    Case("trap, month range without year", 'bad("Eng", "Acme", "Jan – Mar")', "fail"),
    Case("trap, role with a comma", 'bad("Engineer, Montreal", "Acme Corp", "2020 – 2023")', "fail"),
    Case("trap, same role twice, one trap", 'ok("Engineer", "Acme", "2020 – 2023"); hbare("Engineer", "2019");'
         ' ok("Engineer", "Beta", "2015 – 2019")', "fail"),
    # org text that looks like a date must not hide the trap, nor fake one in the lib order
    Case("trap, org with a year", 'bad("Engineer", "Vision 2020 Inc", "2021 – 2023")', "fail"),
    Case("lib, org with a year", 'ok("Engineer", "Vision 2020 Inc", "2021 – 2023")', "pass"),
    Case("trap, org Now", 'bad("Engineer", "Now", "2021 – 2023")', "fail"),
    Case("lib, org Now", 'ok("Engineer", "Now", "2021 – 2023")', "pass"),
    Case("lib, org 3M", 'ok("Engineer", "3M Corp", "2020 – 2023")', "pass"),
    Case("lib, role Tier 2", 'ok("Tier 2 Support", "Acme Corp", "2020 – 2023")', "pass"),
    # date notations
    Case("Present alone", 'ok("Eng", "Acme", "Present")', "pass"),
    Case("open-ended, French", 'ok("Eng", "Acme", "Janvier – présent")', "pass"),
    Case("Arabic digits", 'ok("Eng", "Acme", "٢٠٢٤")', "pass"),
    Case("Reiwa", 'ok("Eng", "Acme", "令和6年")', "pass"),
    Case("Thai digits", 'ok("Eng", "Acme", "๒๕๖๗")', "pass"),
    Case("date on two lines", 'ok("Eng", "Acme", [Jan 2020 – \\ Dec 2021])', "pass"),
    # undated entries: a year in a bullet is not a date
    Case("empty date", 'ok("Backend Developer", "Acme Corp", "")', "pass"),
    Case("undated, year in a bullet", 'ok("Engineer", "Acme", "", [Shipped in 2019 the thing])', "pass"),
    Case("undated then dated, bullet years", 'ok("Volunteer", "Club", ""); ok("Engineer", "Acme", "2020 – 2023",'
         ' [Shipped in 2019 the thing], [Won award 2022])', "pass"),
    # org-less entry: lib `entry` sets the date inline; a hand-built head with the same markers is the orphan
    Case("org-less, bullet short of the date", f'bare("Engineer", "2012"); {BULLET}', "pass", inline=True),
    Case("hand-built, bullet short of the date", f'hbare("Engineer", "2012"); {BULLET}', "fail"),
    Case("org-less before the next section", 'bare("Engineer", "2012"); list([b]); v(1em); text(weight: "bold")[EDUCATION];'
         ' bare("BSc", "2010"); list([x])', "pass"),
    Case("B.Sc. year, then a dated entry", 'bare("B.Sc. Physics", "2012"); ok("Backend Developer", "Acme Corp", "Mar 2024 – present")',
         "pass", inline=True),
    Case("hand-built B.Sc. year, then a dated entry", 'hbare("B.Sc. Physics", "2012");'
         ' ok("Backend Developer", "Acme Corp", "Mar 2024 – present")', "fail"),
    # not measurable: WARN, never a silent pass
    Case("empty role", 'ok("", "Acme", "2020 – 2023")', "warn"),
    Case("old lib heads without markers", 'old("Engineer", "Acme")', "warn"),
]

_LONG_ROLE = ("Senior Staff Principal Distinguished Software Engineering Architect and Technical Lead for the Platform Group")
CASES2 = [   # HEAD2 pages; every one passes, `inline` pins where the date went
    Case("short org, no note", 'sec("Certifications")[#job("AWS Solutions Architect", "Amazon", "Mar 2023 – Mar 2026", none)]',
         "pass", inline=True),
    Case("long org line reaches under the date", f'sec("Education")[#job("B.Sc.", "Université de Montréal", "Sep 2019 – May 2023", "{LONG}")]',
         "pass", inline=False),
    Case("own bullets reaching under the date do not anchor it", 'sec("Experience")[#job("Engineer", "Acme", "Jan 2020 – Mar 2021", "")\n'
         '- Led the migration of the billing platform to an event-driven design used by every team, cutting incident load by half]',
         "pass", inline=True),
    Case("long role wraps", f'sec("Education")[#job("{_LONG_ROLE}", "Acme", "Sep 2022 – May 2026 (expected)", "")]', "pass", inline=True),
    Case("wrapping org line", 'sec("S")[#job("Role R09", "Org O09", "2016", "' + " ".join(["gamma be alpha d gamma ep ep ep gamma alpha"] * 4)
         + '")\n#job("Role R10", "Org O10", "2017", "City")]', "pass", inline=True),
    Case("long unbreakable word in the note", 'sec("S")[#job("Role R11", "Org", "2016", "' + "x" * 120 + '")\n#job("Role R12", "Org", "2017", "City")]',
         "pass", inline=True),
    Case("two-column family", 'grid(columns: (4.2cm, 1fr), column-gutter: 14pt, sec("Contact")[a\\@b.c \\ 555-0100],'
         ' sec("Education")[#job("B.Sc. Computer Science", "Université de Montréal", "Sep 2022 – May 2026", "Montréal")\n'
         '#job("DEC in Science", "Collège Riverside", "Aug 2020 – May 2022", "Laval")])', "pass"),
]


Verdict = Callable[[str], tuple[str, list[str], list[str], list[Mark]]]


def _measure(tmp: Path, head: str, cases: list[Case]) -> Verdict:
    for f in ("lib.typ", "icons.typ"):
        shutil.copy(ROOT / "templates" / f, tmp)
    src = tmp / "t.typ"
    src.write_text(head + "\n#pagebreak()\n".join(f"#{{ {c.body} }}" for c in cases), encoding="utf-8")
    ok, err = typst_compile(str(src), str(tmp / "t.pdf"))
    assert ok and "converge" not in err, err
    marks, words = _typst_query(str(src), ENTRY_MARKS), word_boxes(str(tmp / "t.pdf"), with_text=True)
    assert marks is not None and words is not None and len(words) == len(cases)
    page = {c.name: i for i, c in enumerate(cases, 1)}

    def verdict(name: str) -> tuple[str, list[str], list[str], list[Mark]]:
        pm = [m for m in marks if m.get("page") == page[name]]
        warns: list[str] = []
        fails = check_date_adjacency("", "", marks=pm, warns=warns, words=words)
        return ("fail" if fails else "warn" if warns else "pass"), fails, warns, pm
    return verdict


@pytest.fixture(scope="module")
def layouts(toolchain: str, tmp_path_factory: pytest.TempPathFactory) -> Verdict:
    return _measure(tmp_path_factory.mktemp("dates"), HEAD, CASES)


@pytest.fixture(scope="module")
def layouts2(toolchain: str, tmp_path_factory: pytest.TempPathFactory) -> Verdict:
    return _measure(tmp_path_factory.mktemp("dates2"), HEAD2, CASES2)


def _inline(marks: list[Mark]) -> bool:
    return bool(next(m for m in marks if m.get("kind") == "date").get("inline"))


@pytest.mark.parametrize("case", CASES, ids=[c.name for c in CASES])
def test_verdict_on_a_real_layout(layouts: Verdict, case: Case) -> None:
    got, fails, warns, marks = layouts(case.name)
    assert got == case.verdict, fails or warns
    if case.inline is not None:
        assert _inline(marks) is case.inline, marks


@pytest.mark.parametrize("case", CASES2, ids=[c.name for c in CASES2])
def test_date_anchor(layouts2: Verdict, case: Case) -> None:
    """The lib sets the date inline after the role when no one-line org line reaches under it; either way the date reads in place."""
    got, fails, warns, marks = layouts2(case.name)
    assert got == "pass", fails or warns
    if case.inline is not None:
        assert _inline(marks) is case.inline, marks


def test_messages_name_the_entry_and_the_remedy(layouts: Verdict) -> None:
    assert layouts("trap order")[1][0].startswith('lengthen the org/descriptor line of entry "Backend Developer"')
    fails = layouts("hand-built B.Sc. year, then a dated entry")[1]
    assert len(fails) == 1 and "B.Sc. Physics" in fails[0] and "next entry starts" in fails[0]
    assert any("below the entry head" in m for m in layouts("hand-built, bullet short of the date")[1])
    assert len(layouts("trap, same role twice, one trap")[1]) == 1       # only the hand-built one is reported
    assert "head words not found" in layouts("empty role")[2][0]
    assert any("no lib markers" in m for m in layouts("old lib heads without markers")[2])


@pytest.mark.parametrize("above", ["9.0", "9.5"])
def test_inline_decision_does_not_depend_on_the_page(toolchain: str, tmp_path: Path, above: str) -> None:
    """An entry whose inline date wraps its role at the page foot, a long bullet below: the lib must converge."""
    for f in ("lib.typ", "icons.typ"):
        shutil.copy(ROOT / "templates" / f, tmp_path)
    src = tmp_path / "c.typ"
    src.write_text(HEAD2.replace("height: 14cm", "height: 6cm") + f'#v({above}pt)\n'
                   '#sec("Education")[#job("Senior Staff Principal Distinguished Software Engineering Architect and Technical Lead'
                   ' Platform Group Scale Core", "Org", "Sep 2022 – May 2026", "City")]\n'
                   '#sec("Exp")[- A long bullet that runs across the whole width of the column to reach under the date at the'
                   ' right edge yes yes yes yes yes.]\n', encoding="utf-8")
    ok, err = typst_compile(str(src))
    assert ok and "converge" not in err, err

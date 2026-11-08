"""verify.py --selftest: Date adjacency: measured from lib markers and pdftotext word order"""

from __future__ import annotations

import os
import shutil
import tempfile
from collections.abc import Iterator

from vitae.core.base import Mark, WordBox
from vitae.core.env import pdf_tool, typst_can_query
from vitae.selftest.gates.fixtures import VERIFY_FILE
from vitae.verify.groups import (
    ENTRY_MARKS,
    _typst_query,
    check_date_adjacency,
)
from vitae.verify.pdf import typst_compile, word_boxes


def date_adjacency() -> None:
    """Date adjacency: measured from lib markers and pdftotext word order."""

    # date adjacency: measured from lib markers + pdftotext word ORDER, so every
    # case is a real layout. `ok(...)` is lib `entry` (role -> date -> org)
    # with a descriptor line reaching under the date, as every template has
    # (an org line that stops short of a far-right date IS read before it:
    # that is the trap);
    # `bad(...)` keeps the markers but sets the org line 2pt under the role row,
    # so the boxes overlap and pdftotext reads role, org, date (the trap);
    # `inl(...)` puts the org on the head line and the date under it.
    # Each case is one page of one document: one compile, one query.
    if typst_can_query() and pdf_tool("pdftotext"):
        _lib = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(VERIFY_FILE))), "templates")
        _pre = ('#import "lib.typ": *\n#set page(width: 14cm, height: 12cm, margin: 2cm)\n'
                '#set text(size: 10pt)\n'
                '#let ok(r, o, d, ..b) = { entry(r, o, d, [Montreal · what the employer is, in one clause · full-time, hybrid])\n'
                '  b.pos().map(x => list(x)).join() }\n'
                '#let bad(r, o, d, ..b) = block[#grid(columns: (1fr, auto), align: (left + bottom, right + bottom),\n'
                '  [#head-mark("entry", r, org: o, dated: true)#text(size: 11pt, weight: "bold", r)],\n'
                '  [#part-mark("date", text(size: 9pt, d))#text(size: 9pt, d)])\n'
                '  #v(-8pt)\n  #text(size: 9pt)[#part-mark("org", o)#o]\n'
                '  #b.pos().map(x => list(x)).join()]\n'
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
        # (name, typst body, expected: "fail" | "pass" | "warn")
        _dcases: list[tuple[str, str, str]] = [
            ("lib order", 'ok("Backend Developer", "Acme Corp", "Mar 2024 – present")', "pass"),
            ("trap order", 'bad("Backend Developer", "Acme Corp", "Mar 2024 – present")', "fail"),
            ("trap order, 12pt under the head", 'wide(12pt, "Senior Engineer", "Acme Corp", "2019")', "fail"),
            ("trap order, 16pt under the head", 'wide(16pt, "Senior Engineer", "Acme Corp", "2019")', "fail"),
            ("trap order, 20pt under the head", 'wide(20pt, "Senior Engineer", "Acme Corp", "2019")', "fail"),
            ("trap order, 32pt under the head", 'wide(32pt, "Senior Engineer", "Acme Corp", "2019")', "fail"),
            ("trap order, 60pt under the head", 'wide(60pt, "Senior Engineer", "Acme Corp", "2019")', "fail"),
            ("trap order, 150pt under the head", 'wide(150pt, "Senior Engineer", "Acme Corp", "2019")', "fail"),
            ("trap order, bold 10pt head and 10pt date", 'wide(14pt, "Senior Engineer", "Acme Corp", "2019", hs: 10pt, ds: 10pt)', "fail"),
            ("trap order, bold 9pt head and 9pt date", 'wide(8pt, "Senior Engineer", "Acme Corp", "2019", hs: 9pt, ds: 9pt)', "fail"),
            ("org with year", 'bad("Engineer", "Vision 2020 Inc", "2021 – 2023")', "fail"),
            ("org with year, lib", 'ok("Engineer", "Vision 2020 Inc", "2021 – 2023")', "pass"),
            ("org address", 'bad("Engineer", "Acme, 1234 Main St", "2021 – 2023")', "fail"),
            ("org Current", 'bad("Engineer", "Current", "2021 – 2023")', "fail"),
            ("org Now", 'bad("Engineer", "Now", "2021 – 2023")', "fail"),
            ("org Now, lib", 'ok("Engineer", "Now", "2021 – 2023")', "pass"),
            ("org Currentware", 'bad("Eng", "Currentware", "2020 – 2021")', "fail"),
            ("org 3M", 'bad("Engineer", "3M Corp", "2020 – 2023")', "fail"),
            ("org 3M, lib", 'ok("Engineer", "3M Corp", "2020 – 2023")', "pass"),
            ("org 10-15 staff", 'bad("Eng", "Acme, 10-15 staff", "03/20 – 04/22")', "fail"),
            ("role Tier 2", 'bad("Tier 2 Support", "Acme Corp", "2020 – 2023")', "fail"),
            ("role Tier 2, lib", 'ok("Tier 2 Support", "Acme Corp", "2020 – 2023")', "pass"),
            ("role dash+year", 'bad("Eng – Tier 2024", "Acme", "2021 – 2022")', "fail"),
            ("role with comma", 'bad("Engineer, Montreal", "Acme Corp", "2020 – 2023")', "fail"),
            ("role with comma, lib", 'ok("Engineer, Montreal", "Acme Corp", "2020 – 2023")', "pass"),
            ("4-word org on head line", 'inl("Engineer", "Acme Global Systems Ltd", "2020 – 2023")', "fail"),
            ("same-line org with year", 'inl("Engineer", "Vision 2020 Inc", "2021 – 2023")', "fail"),
            ("Jan to Present, trap", 'bad("Eng", "Acme", "Jan to Present")', "fail"),
            ("Janvier présent, trap", 'bad("Eng", "Acme", "Janvier – présent")', "fail"),
            ("Present alone", 'ok("Eng", "Acme", "Present")', "pass"),
            ("empty role", 'ok("", "Acme", "2020 – 2023")', "warn"),
            ("undated cert then dated w/ bullet year",
             'ok("AWS Cert", "", ""); ok("Dev", "Acme", "2020 – 2023", [Won award 2022])', "pass"),
            ("org-less 2012, bullet short of the date, last on page",
             'bare("Engineer", "2012"); list([a long bullet that runs across])', "pass"),
            ("hand-built 2012, bullet short of the date, last on page",
             'hbare("Engineer", "2012"); list([a long bullet that runs across])', "fail"),
            ("org-less 2012, bullet wrapping under the date",
             'bare("Engineer", "2012"); list([a long bullet that runs across the whole line width of the page for sure, yes yes yes])', "pass"),
            ("org-less 2012 before next section title",
             'bare("Engineer", "2012"); list([b]); v(1em); text(weight: "bold")[EDUCATION]; bare("BSc", "2010"); list([x])', "pass"),
            ("next entry with empty role", 'ok("Engineer", "Acme", "2020 – 2023"); ok("", "Beta", "2019 – 2020")', "warn"),
            ("bullet number then date", 'bad("Engineer", "Acme Corp", "2020 – 2023", [Led 3 years of work])', "fail"),
            ("en cours, trap", 'bad("Eng", "Acme", "03/24 – en cours")', "fail"),
            ("Jan - Mar no year, trap", 'bad("Eng", "Acme", "Jan – Mar")', "fail"),
            ("Present alone, trap", 'bad("Eng", "Acme", "Present")', "fail"),
            ("Sep 2011, trap", 'bad("Eng", "Acme", "Sep 2011 – Jun 2012")', "fail"),
            ("en cours", 'ok("Eng", "Acme", "03/24 – en cours")', "pass"),
            ("Janvier présent", 'ok("Eng", "Acme", "Janvier – présent")', "pass"),
            ("arabic digits", 'ok("Eng", "Acme", "٢٠٢٤")', "pass"),
            ("reiwa", 'ok("Eng", "Acme", "令和6年")', "pass"),
            ("thai digits", 'ok("Eng", "Acme", "๒๕๖๗")', "pass"),
            ("date on two lines", 'ok("Eng", "Acme", [Jan 2020 – \\ Dec 2021])', "pass"),
            ("empty date", 'ok("Backend Developer", "Acme Corp", "")', "pass"),
            ("undated, bullet year", 'ok("Engineer", "Acme", "", [Shipped in 2019 the thing])', "pass"),
            ("undated, bullet 5000", 'ok("Engineer", "Acme", "", [Served 5000 users])', "pass"),
            ("undated, wrapped now", 'ok("Engineer", "Acme", "", [Did the thing right ' + "x " * 60 + 'now])', "pass"),
            ("undated, no org", 'ok("Engineer", "", "", [Cut cost 30%])', "pass"),
            ("undated then dated w/ bullet years",
             'ok("Volunteer", "Club", ""); ok("Engineer", "Acme", "2020 – 2023", [Shipped in 2019 the thing], [Won award 2022])', "pass"),
            ("undated then dated, trailing section",
             'ok("Volunteer", "Club", ""); ok("Engineer", "Acme", "2020 – 2023", [bullet]); [EDUCATION \\ BSc \\ 2012 \\ Cert 2020]', "pass"),
            ("B.Sc. 2012 orphan", 'bare("B.Sc. Physics", "2012"); ok("Backend Developer", "Acme Corp", "Mar 2024 – present")', "pass"),
            ("hand-built B.Sc. 2012 orphan", 'hbare("B.Sc. Physics", "2012"); ok("Backend Developer", "Acme Corp", "Mar 2024 – present")', "fail"),
            ("B.Sc. month range", 'ok("B.Sc. Physics", "Université Laval", "Sep 2008 – Jun 2012"); ok("Backend Developer", "Acme Corp", "Mar 2024 – present")', "pass"),
            ("same role twice, one trap", 'ok("Engineer", "Acme", "2020 – 2023"); hbare("Engineer", "2019"); ok("Engineer", "Beta", "2015 – 2019")', "fail"),
            ("old lib heads", 'old("Engineer", "Acme")', "warn"),
        ]
        def _layouts(pre: str, cases: list[tuple[str, str, str]]) -> Iterator[
                tuple[str, str, str, list[str], list[str], list[Mark], list[WordBox]]]:
            """Compile one page per case; yield (name, expected, got, fails, warns, marks, words)."""
            with tempfile.TemporaryDirectory(prefix="vitae-date-") as _td:
                for _nm in ("lib.typ", "icons.typ"):
                    shutil.copy(os.path.join(_lib, _nm), _td)
                _src = os.path.join(_td, "t.typ")
                with open(_src, "w", encoding="utf-8") as _fh:
                    _fh.write(pre + "\n#pagebreak()\n".join(f"#{{ {b} }}" for _, b, _ in cases))
                _pdf = os.path.join(_td, "t.pdf")
                _ok, _err = typst_compile(_src, _pdf)
                assert _ok and "converge" not in _err, _err
                _marks = _typst_query(_src, ENTRY_MARKS)
                _words = word_boxes(_pdf, with_text=True)
                assert _marks is not None and _words is not None and len(_words) == len(cases)
            for _p, (_n, _b, _exp) in enumerate(cases, 1):
                _w: list[str] = []
                _pm: list[Mark] = [m for m in _marks if m.get("page") == _p]
                _f = check_date_adjacency("", "", marks=_pm, warns=_w, words=_words)
                yield _n, _exp, "fail" if _f else "warn" if _w else "pass", _f, _w, _pm, _words[_p - 1]
        for _n, _lexp, _gt, _fl, _wl, _pm, _pw in _layouts(_pre, _dcases):
            assert _gt == _lexp, (_n, _gt, _fl or _wl)
            if _n in ("B.Sc. 2012 orphan", "org-less 2012, bullet short of the date, last on page"):
                # lib entry() with nothing under its date: the date goes inline
                assert [m for m in _pm if m.get("kind") == "date"][0].get("inline"), _pm
            if _n == "hand-built B.Sc. 2012 orphan":
                assert len(_fl) == 1 and "B.Sc. Physics" in _fl[0] and "next entry starts" in _fl[0], _fl
            if _n == "trap order":
                assert _fl[0].startswith('lengthen the org/descriptor line of entry "Backend Developer"'), _fl
            if _n == "same role twice, one trap":
                assert len(_fl) == 1, _fl
            if _n.startswith("hand-built 2012"):
                assert any("below the entry head" in m for m in _fl), _fl
            if _n == "next entry with empty role":
                assert len(_wl) == 1 and "head words not found" in _wl[0], _wl
            if _n == "old lib heads":
                assert any("no lib markers" in m for m in _wl), _wl
        # DATE ANCHOR (lib entry): a bullet-less entry whose org line stops short of
        # its right-flushed date, with nothing further down reaching under it, sets
        # the date inline after the role. Letter width, so short lines stay short.
        # run6f (local-model run, color-band): with the 0.6.11 lib its B.Sc. date was
        # emitted last on the page; here it must read B.Sc. -> date -> org.
        _pre2 = ('#import "lib.typ": *\n#set page(width: 21.59cm, height: 14cm, margin: 1.5cm)\n'
                 '#set text(size: 10pt)\n'
                 '#let sec(t, body) = wd-section((t, b) => block(above: 9pt)[#strong(upper(t)) #b])(t, body)\n'
                 '#let job(r, o, d, n) = entry(r, o, d, n)\n'
                 '#let sk(l, i) = srow(strong(l), i, brk: true, brk-gap: 2pt, above: auto, below: 0pt)\n')
        _long = ("Montréal · what the employer is, in one clause · full-time, hybrid, on-site three days "
                 "a week, remote otherwise")
        _cases2 = [
            ("run6f education",
             'sec("Education")[#job("B.Sc. Computer Science", "Université de Montréal", '
             '"Sep 2022 – May 2026 (expected)", "Montréal · GPA 3.6/4.3")\n'
             '#job("DEC in Science", "Collège Riverside", "", "Laval · 2020 – 2022")]; '
             'sec("Technical Stack")[#sk("PROGRAMMING", [Python, Go, SQL, Rust, Bash]) '
             '#sk("BACKEND", [FastAPI, PostgreSQL])]; '
             'sec("Languages")[Bilingual — English (fluent), French (native)]', "pass"),
            ("short org, no note, last on page",
             'sec("Certifications")[#job("AWS Solutions Architect", "Amazon", "Mar 2023 – Mar 2026", none)]', "pass"),
            ("empty note", 'sec("Education")[#job("B.Sc.", "Uni", "Sep 2019 – May 2023", "")]', "pass"),
            ("long org reaches", f'sec("Education")[#job("B.Sc.", "Université de Montréal", "Sep 2019 – May 2023", "{_long}")]', "pass"),
            ("long role wraps",
             'sec("Education")[#job("Senior Staff Principal Distinguished Software Engineering Architect and '
             'Technical Lead for the Platform Group", "Acme", "Sep 2022 – May 2026 (expected)", "")]', "pass"),
            ("long role + long date, bullets",
             'sec("Experience")[#job("Senior Staff Principal Distinguished Software Engineering Architect and '
             'Technical Lead", "Acme Corporation International", "September 2022 – May 2026 (expected, part-time)", '
             f'"{_long}")\n- Led the migration of the billing platform to an event-driven design used by every team]', "pass"),
            ("two-column family",
             'grid(columns: (4.2cm, 1fr), column-gutter: 14pt, sec("Contact")[a\\@b.c \\ 555-0100 \\ Montréal], '
             'sec("Education")[#job("B.Sc. Computer Science", "Université de Montréal", "Sep 2022 – May 2026", "Montréal")\n'
             '#job("DEC in Science", "Collège Riverside", "Aug 2020 – May 2022", "Laval")])', "pass"),
            ("bullets that do not reach", 'sec("Experience")[#job("Engineer", "Acme", "Jan 2020 – Mar 2021", "")\n- b]', "pass"),
            # bullets reaching under the date do NOT anchor it (a short org line is
            # still read first, measured): the date goes inline all the same
            ("own bullets reach", 'sec("Experience")[#job("Engineer", "Acme", "Jan 2020 – Mar 2021", "")\n'
             '- Led the migration of the billing platform to an event-driven design used by every team, '
             'cutting incident load by half]', "pass"),
            # reviewer repro: bullet-less / one short bullet / bullet-less in one section
            ("neighbours do not anchor", 'sec("Experience")[#job("Role01", "Org1", "Sep 2001 – May 2002", "City")\n'
             '#job("Role02", "Org2", "Sep 2002 – May 2003", "City")\n- b\n'
             '#job("Role03", "Org3", "Sep 2003 – May 2004", "City")]', "pass"),
            # reviewer repro: role about a line wide + long date: the separator never
            # opens the second line (it stays on the role line, the date box wraps)
            # reviewer repros (ff5da87): an org line WIDER than the column wraps and its
            # first line may stop short of the date — only a one-line org line that
            # runs under the date keeps the date right-flushed; a wrapping role too
            ("wrapping org line", 'sec("S")[#job("Role R09", "Org O09", "2016", "' + " ".join(
                ["gamma be alpha d gamma ep ep ep gamma alpha gamma ep alpha gamma gamma ep gamma d gamma gamma gamma be ep alpha d"] * 2)
             + '")\n#job("Role R10", "Org O10", "2017", "City")]', "pass"),
            ("long unbreakable word in the note", 'sec("S")[#job("Role R11", "Org", "2016", "' + "x" * 120
             + '")\n#job("Role R12", "Org", "2017", "City")]', "pass"),
            ("wrapping role, reaching org line", 'sec("S")[#job("Senior Staff Principal Distinguished Software '
             'Engineering Architect and Technical Lead of the Platform Group and Core R13", "Org", "2016", '
             f'"{_long}")\n#job("Role R14", "Org", "2017", "City")]', "pass"),
            ("long role, sep stays on the role line",
             'sec("Education")[#job("Bachelor of Science in Computer Science and Software Engineering, Honours '
             'Co-op Program", "Uni", "September 2022 – May 2026 (expected)", "City")]', "pass"),
            ("same, descriptor lengthened",
             f'sec("Experience")[#job("Engineer", "Acme", "Jan 2020 – Mar 2021", "{_long}, twice a month")\n- b]', "pass"),
        ]
        _inline = {"run6f education": True, "short org, no note, last on page": True, "empty note": True,
                   "long org reaches": False, "long role wraps": True,
                   "long role + long date, bullets": True, "bullets that do not reach": True,
                   "own bullets reach": True, "long role, sep stays on the role line": True,
                   "wrapping org line": True, "long unbreakable word in the note": True,
                   "wrapping role, reaching org line": True}
        for _n, _lexp, _gt, _fl, _wl, _pm, _pw in _layouts(_pre2, _cases2):
            assert _gt == _lexp, (_n, _gt, _fl or _wl)
            _dm = [m for m in _pm if m.get("kind") == "date"]
            if _n in _inline:
                assert bool(_dm[0].get("inline")) == _inline[_n], (_n, _dm)
            if _n == "neighbours do not anchor":
                assert all(m.get("inline") for m in _pm if m.get("kind") == "date"), _pm
            if _n == "long role, sep stays on the role line":
                _ls: dict[int, list[tuple[float, str]]] = {}
                for _b, _t in _pw:
                    _ls.setdefault(round((_b[1] + _b[3]) / 2), []).append((_b[0], _t))
                assert not any(min(_v)[1] in ("\u2014", "\u2013", "\u00b7") for _v in _ls.values()), _ls
                assert len([1 for _v in _ls.values() if any(_t == "September" for _x, _t in _v)]) == 1
            # never two words colliding on one line (role vs date, wrapped or not)
            _bx = [b for b, _t in _pw]
            assert not any(abs((a[1] + a[3]) - (b[1] + b[3])) < 6 and a[0] < b[2] - 0.5 and b[0] < a[2] - 0.5
                           for i, a in enumerate(_bx) for b in _bx[i + 1:]), _n
        # reviewer repro: an entry whose inline date wraps its role sits at the page
        # foot, a long bullet below; the decision must not depend on the page
        # (the 9869cc0 lib flipped between pages and never converged)
        # the separator is the family's content, kept as given (outer spaces only
        # trimmed): a box or a styled glyph survives the inline date
        with tempfile.TemporaryDirectory(prefix="vitae-date-") as _td:
            for _f in ("lib.typ", "icons.typ"):
                shutil.copy(os.path.join(_lib, _f), _td)
            with open(os.path.join(_td, "s.typ"), "w", encoding="utf-8") as _fh:
                _fh.write('#import "lib.typ": *\n'
                          '#metadata(repr(trim-sep([ #box(width: 4pt, height: 4pt, fill: red) ]))) <a>\n'
                          '#metadata(repr(trim-sep([ #text(fill: red)[◆] ]))) <b>\n'
                          '#metadata(repr(trim-sep([ — ]))) <c>\n')
            _sa = _typst_query(os.path.join(_td, "s.typ"), "<a>") or [""]
            _sb = _typst_query(os.path.join(_td, "s.typ"), "<b>") or [""]
            _sc = _typst_query(os.path.join(_td, "s.typ"), "<c>") or [""]
            assert "box" in _sa[0] and "ff4136" in _sa[0], _sa
            assert "◆" in _sb[0] and "styled" in _sb[0], _sb
            assert _sc[0].strip("[]") == "—", _sc
        for _y in ("9.0", "9.5"):
            _src = ('#import "lib.typ": *\n#set page(width: 21.59cm, height: 6cm, margin: 1.5cm)\n'
                    '#set text(size: 10pt)\n' + _pre2.split("\n", 3)[3] + f'#v({_y}pt)\n'
                    '#sec("Education")[#job("Senior Staff Principal Distinguished Software Engineering '
                    'Architect and Technical Lead Platform Group Scale Core", "Org", "Sep 2022 – May 2026", "City")]\n'
                    '#sec("Exp")[- A long bullet that runs across the whole width of the column to reach '
                    'under the date at the right edge yes yes yes yes yes.]\n')
            with tempfile.TemporaryDirectory(prefix="vitae-date-") as _td:
                for _f in ("lib.typ", "icons.typ"):
                    shutil.copy(os.path.join(_lib, _f), _td)
                with open(os.path.join(_td, "c.typ"), "w", encoding="utf-8") as _fh:
                    _fh.write(_src)
                _ok, _err = typst_compile(os.path.join(_td, "c.typ"))
                assert _ok and "converge" not in _err, (_y, _err)
        print(f"selftest date adjacency: {len(_dcases) + len(_cases2)} typst layouts measured, "
              "2 page-foot layouts converge (date anchor: run6f education reads in place)")
    else:
        print("selftest date adjacency SKIPPED (typst / pdftotext not on PATH)")

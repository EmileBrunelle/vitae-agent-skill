"""The `summary:` and `expected:` arguments of lib.typ reach the <vitae-sec> / <vitae-head> marks (both toolchains),
with and without the workday flag path, and only when declared."""
from __future__ import annotations

import shutil
from datetime import date
from pathlib import Path

from harness import ROOT
from vitae.verify.declared import check_expected_past
from vitae.verify.groups import typst_query
from vitae.verify.pdf import typst_compile

SRC = ('#import "lib.typ": *\n#set page(width: 14cm, height: 12cm, margin: 2cm)\n'
       '#let section = wd-section((t, body, airy: false) => block[#strong(t) #body])\n'
       '#section("About", summary: true)[Cut costs by 40%.]\n'
       '#section("Work")[#entry("Analyst", "Acme", "2020 – 2022", none)]\n'
       '#section("School")[#entry("B.Sc. Physics", "McGill", "2021 – 2024", none, expected: true)]\n')


def test_declared_arguments_reach_the_marks(toolchain: str, tmp_path: Path) -> None:
    for f in ("lib.typ", "icons.typ"):
        shutil.copy(ROOT / "templates" / f, tmp_path)
    src = tmp_path / "d.typ"
    src.write_text(SRC, encoding="utf-8")
    ok, err = typst_compile(str(src), str(tmp_path / "d.pdf"))
    assert ok, err
    marks = typst_query(str(src), "selector(<vitae-sec>).or(<vitae-head>)")
    assert marks is not None
    secs = {m["text"]: m for m in marks if "kind" not in m}
    assert secs["About"].get("summary") is True
    assert "summary" not in secs["Work"] and "summary" not in secs["School"]
    heads = {m["text"]: m for m in marks if m.get("kind") == "entry"}
    assert heads["B.Sc. Physics"].get("expected") is True and "2024" in heads["B.Sc. Physics"].get("dates", "")
    assert "expected" not in heads["Analyst"]
    got = check_expected_past(list(heads.values()), date(2026, 1, 1))
    assert len(got) == 1 and "B.Sc. Physics" in got[0]

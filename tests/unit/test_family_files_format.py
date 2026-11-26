"""references/design/families/*.md follow the format in CONTRIBUTING.md ("Family file format")."""
import re

import pytest
from _paths import ROOT
from vitae.design.tables import FAMILIES

DIR = ROOT / "references" / "design" / "families"
HEADER = re.compile(r"^## (\d+)\. (\S+) — .+ · register: \S.*$")
BULLET = re.compile(r"^- \*\*([^*]+)\*\*")
CORE = ("Heading device", "Skills block", "Accent role", "Icons", "Header", "Type", "Accents", "Verified")
# Every label in its only legal position; optional ones sit in the slot shown.
ORDER = ("Heading device", "Skills block", "Accent role", "Icons", "List marker", "Header",
         "Family variant", "Section order", "Type", "Accents", "Gabarit", "Verified")


def problems(stem: str, text: str) -> list[str]:
    lines = text.splitlines()
    head = HEADER.match(lines[0]) if lines else None
    out = []
    if not head:
        out.append("header")
    elif head.group(2) != stem:
        out.append("stem")
    labels = [m.group(1) for ln in lines if (m := BULLET.match(ln))]
    unknown = [x for x in labels if x not in ORDER]
    if unknown:
        out.append(f"unknown {unknown}")
    if labels != [x for x in ORDER if x in labels]:
        out.append("order or duplicate")
    if missing := [x for x in CORE if x not in labels]:
        out.append(f"missing {missing}")
    if not lines[-1].startswith("- Markets:"):
        out.append("Markets bullet last")
    return out


def numbers(files: dict[str, str]) -> list[str]:
    return [m.group(1) for t in files.values() if (m := HEADER.match(t.splitlines()[0]))]


def texts() -> dict[str, str]:
    return {p.stem: p.read_text(encoding="utf-8") for p in sorted(DIR.glob("*.md"))}


@pytest.mark.parametrize("stem", sorted(texts()))
def test_family_file_format(stem):
    assert problems(stem, texts()[stem]) == []


def test_numbers_are_unique_and_stems_match_the_roster():
    nums = numbers(texts())
    assert len(set(nums)) == len(nums)
    assert set(texts()) == set(FAMILIES)


@pytest.mark.parametrize(("label", "mutate"), [
    ("swapped core labels", lambda t: t.replace("- **Type**", "- @@").replace("- **Header**", "- **Type**").replace("- @@", "- **Header**")),
    ("optional out of slot", lambda t: t.replace("- **Verified**", "- **List marker**: x\n- **Verified**", 1)),
    ("unknown label", lambda t: t.replace("- **Icons**", "- **Bogus**: x\n- **Icons**", 1)),
    ("missing core label", lambda t: t.replace("- **Icons**", "- Icons", 1)),
    ("renamed stem", lambda t: t.replace(" swiss-grid ", " swiss-gridx ", 1)),
    ("bad header", lambda t: t.replace("## 1.", "# 1.", 1)),
])
def test_the_checker_rejects_a_broken_file(label, mutate):
    text = texts()["swiss-grid"]
    assert problems("swiss-grid", mutate(text)) != [], label


def test_the_checker_rejects_a_duplicate_number_and_an_extra_file():
    files = texts()
    files["extra"] = files["swiss-grid"].replace("swiss-grid", "extra")
    assert len(set(numbers(files))) != len(numbers(files))
    assert set(files) != set(FAMILIES)

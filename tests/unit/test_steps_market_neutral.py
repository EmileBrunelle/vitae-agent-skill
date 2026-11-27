"""SKILL.md and references/steps/ carry general rules only: market names live in references/regional/.

The market names come from the regional/ tree (folder and file names), never from a hard-coded list.
"""
import re
import unicodedata

import pytest
from _paths import ROOT

REGIONAL = ROOT / "references" / "regional"
SCANNED = [ROOT / "SKILL.md", *sorted((ROOT / "references" / "steps").rglob("*.md"))]
ROUTING = ROOT / "references" / "steps" / "2-region.md"

# Words in a regional/ file or folder name that name a topic or a role, not a place.
TOPIC_WORDS = {
    "academic", "aviation", "common", "credentials", "driving", "education", "financial", "foreign",
    "francophone", "government", "health", "law", "licensing", "market", "nationalisation", "outbound",
    "overview", "regulated", "safety", "teaching", "trades", "transnational", "workers", "workplace",
}
# Case-sensitive: the lowercase word is common English ("us"); the uppercase token is the country.
CASE_SENSITIVE = {"us"}
# A paper format, not a market rule (SKILL.md rule 5 states it as a margin example).
FORMAT_PHRASES = re.compile(r"\bUS Letter\b")


def _fold(text):
    return unicodedata.normalize("NFD", text).encode("ascii", "ignore").decode().lower()


def market_names(root=REGIONAL):
    """Place names derived from the file and folder names under `root`."""
    names = set()
    for path in root.rglob("*"):
        stem = path.stem if path.is_file() else path.name
        words = [w for w in stem.split("-") if w not in TOPIC_WORDS]
        if words:
            names.add(" ".join(words))
    return names


def strip_paths(text):
    """Drop link targets and code spans that are file paths: the path of a market file is not a market claim."""
    text = re.sub(r"\]\([^)\s]*\)", "]", text)
    return re.sub(r"`[^`\n]*(?:/|\.md)[^`\n]*`", "", text)


def find_market_names(text, names):
    text = FORMAT_PHRASES.sub("", strip_paths(text))
    folded = _fold(text)
    hits = []
    for name in sorted(names):
        if name in CASE_SENSITIVE:
            found = re.search(rf"\b{name.upper()}\b", text)
        else:
            pattern = re.escape(_fold(name)).replace("\\ ", "[ -]")
            found = re.search(rf"\b{pattern}\b", folded)
        if found:
            hits.append(name)
    return hits


def test_names_come_from_the_tree():
    names = market_names()
    # Control: the tree yields real markets and drops topic words
    assert {"quebec", "japan", "new zealand", "us"} <= names
    assert not names & TOPIC_WORDS


def test_detector_finds_a_name_and_ignores_paths():
    names = {"japan", "us"}
    assert find_market_names("Dates run oldest first in Japan.", names) == ["japan"]  # positive control
    assert find_market_names("Margins on US Letter.", names) == []
    assert find_market_names("The US market.", names) == ["us"]
    assert find_market_names("See [x](regional/asia/east-asia/japan.md) and `asia/japan.md`.", names) == []


@pytest.mark.parametrize("path", SCANNED, ids=lambda p: str(p.relative_to(ROOT)))
def test_no_market_name_outside_routing(path):
    if path == ROUTING:
        pytest.skip("step 2 routes to the market files by name")
    hits = find_market_names(path.read_text(encoding="utf-8"), market_names())
    assert not hits, f"market names in a general-rules file (move them to references/regional/): {hits}"

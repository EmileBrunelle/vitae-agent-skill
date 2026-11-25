"""Unit tests of the reference-format rule functions (positive and negative samples per rule)."""
import os

import pytest
from test_reference_format import outbound_naming_errors, violations

PATH = "references/regional/x/market.md"
FILLER = " ".join(["word"] * 90)


def doc(h1="# Education: Foo", first="Loaded on demand when X.", body="", h2=None):
    parts = [h1, "", first, ""]
    if h2:
        parts += [h2, ""]
    parts += [body, FILLER]
    return "\n".join(parts)


def has(found, needle):
    return any(needle in f for f in found)


def test_valid_doc_passes():
    assert violations(PATH, doc()) == []


@pytest.mark.parametrize("genre", ["Market", "Education", "Regulated professions", "Field pack", "Gulf credentials"])
def test_h1_genre_ok(genre):
    text = doc(h1=f"# {genre}: Foo", h2="## At a glance" if genre == "Market" else None)
    assert violations(PATH, text) == []


@pytest.mark.parametrize("h1", ["# Foo", "# Foo: Bar", "# Education:Foo", "## Education: Foo", "# Education: "])
def test_h1_genre_bad(h1):
    assert has(violations(PATH, doc(h1=h1)), "H1 lacks")


def test_first_paragraph_missing():
    assert has(violations(PATH, doc(first="Some other intro.")), "Loaded on demand")


def test_first_paragraph_skips_headings():
    text = "# Education: Foo\n\n## Sub\n\nLoaded on demand when X.\n" + FILLER
    assert violations(PATH, text) == []


def test_market_with_at_a_glance_ok():
    assert violations(PATH, doc(h1="# Market: Foo", h2="## At a glance")) == []


@pytest.mark.parametrize("h2", [None, "## Other"])
def test_market_without_at_a_glance(h2):
    assert has(violations(PATH, doc(h1="# Market: Foo", h2=h2)), "At a glance")


def test_non_market_needs_no_at_a_glance():
    assert violations(PATH, doc(h1="# Education: Foo", h2="## Other")) == []


@pytest.mark.parametrize("line", ["See https://example.com/x", "see http://a.b", "go to www.example.org"])
def test_url_present(line):
    assert has(violations(PATH, doc(body=line)), "URL")


@pytest.mark.parametrize("line", ["Publisher site only, no link.", "a www-style name"])
def test_url_absent(line):
    assert violations(PATH, doc(body=line)) == []


@pytest.mark.parametrize("label", ["HIGH", "MEDIUM", "unverified", "not sourced", "LOW", "LOW confidence", "Unverified"])
def test_confidence_banned(label):
    assert has(violations(PATH, doc(body=f"Fact ({label}).")), "banned confidence label")


@pytest.mark.parametrize(
    "line",
    ["Fact (LOW, unsourced).", "Fact (not checked).", "A low rate and a medium size, high salary.", "Fact (S12)."],
)
def test_confidence_ok(line):
    assert violations(PATH, doc(body=line)) == []


@pytest.mark.parametrize(
    "line",
    [
        "(Pub, « T », accessed 2026-11-07, S1)",
        "(Pub, « T », retrieved 2026-11-07, S1)",
        "(Pub, « T », read 2026-11-07, S1)",
        "(Pub, « T », consulté 2026-11-07, S1)",
        "(Pub, « T », consulté le 7 novembre 2026, S1)",
        "Accessed Nov 7, 2026 by hand",
    ],
)
def test_date_verb_banned_in_citation(line):
    # « T » is stripped before matching, so verbs outside the quotes are what counts.
    assert has(violations(PATH, doc(body=line)), "banned date verb")


@pytest.mark.parametrize(
    "line",
    [
        "The form was not retrieved by the office.",
        "Records are retrieved on request.",
        "Candidates read the notice carefully.",
        "The page was accessed through a portal.",
        "Les employeurs ont consulté les dossiers.",
        "(Pub, « T », consulted 2026-11-07, S1)",
        "(Pub, « T », 2023-05-26, consulted 2026-11-07, S295)",
        "(Pub, « T », snapshot 2026-11-07, S1)",
        "(Pub, « T », 2023-05-26, snapshot 2026-11-07, S1)",
        "(Pub, « retrieved 2026-01-01 », consulted 2026-11-07, S1)",
    ],
)
def test_date_verb_ok(line):
    assert violations(PATH, doc(body=line)) == []


def test_fenced_code_is_ignored():
    assert violations(PATH, doc(body="```\nhttps://x.example HIGH accessed 2026-01-01\n```")) == []


@pytest.mark.parametrize(
    "path,text",
    [
        ("references/regional/x/europe-common.md", "# Bad\n" + FILLER),
        ("references/regional/x/overview.md", "# Bad\n" + FILLER),
        ("references/regional/x/stub.md", "# Bad\nshort stub"),
        ("references/other/x.md", "# Bad\n" + FILLER),
    ],
)
def test_scope_exemptions(path, text):
    assert violations(path, text) == []


def test_in_scope_bad_file_is_checked():
    assert violations("references/fields/x.md", "# Bad\n" + FILLER) != []


@pytest.mark.parametrize(
    "rel,first",
    [
        ("references/regional/quebec/outbound/france.md", "# Outbound: France"),
        ("references/regional/near-east/outbound.md", "# Outbound: Gulf"),
        ("references/regional/quebec/market.md", "# Market: Quebec"),
        ("references/regional/india/outbound/europe-common.md", "# Outbound: Europe"),
    ],
)
def test_outbound_naming_ok(rel, first):
    assert outbound_naming_errors(rel.replace("/", os.sep), first) == []


@pytest.mark.parametrize(
    "rel,first,needle",
    [
        ("references/regional/quebec/outbound/to-france.md", "# Outbound: France", "prefix"),
        ("references/regional/quebec/outbound-france.md", "# Market: X", "prefix"),
        ("references/regional/quebec/france.md", "# Outbound: France", "must live"),
    ],
)
def test_outbound_naming_bad(rel, first, needle):
    errors = outbound_naming_errors(rel.replace("/", os.sep), first)
    assert errors and any(needle in e for e in errors)

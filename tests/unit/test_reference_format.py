"""Reference files follow the format in CONTRIBUTING.md ("Reference file format").

Strict rule over every in-scope file; the rule logic itself is covered by test_reference_format_rules.py.
"""
import glob
import os
import re

import pytest

pytestmark = pytest.mark.lint

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SCOPE = ("references/regional/", "references/certifications/", "references/fields/")
MIN_WORDS = 80
GENRES = (
    "Market", "Education", "Regulated professions", "Health professions", "Academic", "Outbound",
    "Law", "Field pack", "Certifications", "Foreign workers", "Gulf nationalisation", "Gulf credentials",
)
H1 = re.compile(r"^# (?:{}): \S".format("|".join(GENRES)))
URL = re.compile(r"https?://|\bwww\.")
QUOTED = re.compile(r"«[^»]*»")
# A banned date verb only counts in citation context: the verb followed by a date.
_DATE = r"(?:\d{4}\b|\d{1,2}\s+\w+\s+\d{4}|[A-Za-z]{3,9}\.?\s+\d{1,2},?\s+\d{4})"
DATE_VERB = re.compile(
    rf"\b(?:accessed|retrieved|consulté)\s+(?:(?:le|on)\s+)?{_DATE}|\bread\s+\d{{4}}-\d{{2}}", re.IGNORECASE
)
CONFIDENCE = re.compile(
    r"\b(?:HIGH|MEDIUM)\b|\bunverified\b|\bnot sourced\b|\bLOW confidence\b|\bLOW\b(?!, unsourced)", re.IGNORECASE
)
CASE_SENSITIVE = {"HIGH", "MEDIUM", "LOW"}


def is_exempt(path: str, text: str) -> bool:
    """Scope exemptions: out of scope dir, *-common.md, overview.md, stubs under MIN_WORDS words."""
    name = os.path.basename(path)
    return (
        not path.startswith(SCOPE)
        or name.endswith("-common.md")
        or name == "overview.md"
        or len(text.split()) < MIN_WORDS
    )


def in_scope_files():
    paths = sorted(
        os.path.relpath(p, ROOT)
        for scope in SCOPE
        for p in glob.glob(os.path.join(ROOT, scope, "**", "*.md"), recursive=True)
    )
    return [p for p in paths if not is_exempt(p, read(p))]


def read(path):
    with open(os.path.join(ROOT, path), encoding="utf-8") as fh:
        return fh.read()


def prose(text):
    """Lines outside fenced code blocks."""
    fence = False
    kept = []
    for line in text.split("\n"):
        if line.lstrip().startswith("```"):
            fence = not fence
        elif not fence:
            kept.append(line)
    return kept


def violations(path: str, text: str) -> list[str]:
    """Format violations of one reference file; empty for an exempt file."""
    if is_exempt(path, text):
        return []
    lines = prose(text)
    found = []
    heading = next((ln for ln in lines if ln.strip()), "")
    if not H1.match(heading):
        found.append("H1 lacks an allowed '<Genre>: ' prefix")
    first = next((ln for ln in lines[1:] if ln.strip() and not ln.startswith("#")), "")
    if not first.startswith("Loaded on demand when"):
        found.append("first paragraph does not start with 'Loaded on demand when'")
    if heading.startswith("# Market:"):
        h2 = next((ln for ln in lines if ln.startswith("## ")), "")
        if h2.strip() != "## At a glance":
            found.append("first H2 of a Market file is not 'At a glance'")
    for line in lines:
        if URL.search(line):
            found.append(f"URL in line text: {line.strip()[:60]}")
        unquoted = QUOTED.sub("", line)
        if m := DATE_VERB.search(unquoted):
            found.append(f"banned date verb: {m.group(0)}")
        for m in CONFIDENCE.finditer(unquoted):
            word = m.group(0)
            if word.split()[0].upper() in CASE_SENSITIVE and not word.split()[0].isupper():
                continue
            found.append(f"banned confidence label: {word}")
    return found


def test_reference_format():
    files = in_scope_files()
    assert files, "no in-scope reference files found"
    errors = [f"{path}: {p}" for path in files for p in violations(path, read(path))]
    assert not errors, "\n".join(errors)


def outbound_naming_errors(rel: str, first_line: str) -> list[str]:
    """Naming errors for one regional file (`rel` relative to the repo root, using os.sep)."""
    name = os.path.basename(rel)
    errors = []
    if name.startswith(("to-", "outbound-")):
        errors.append(f"{rel}: rename by destination without the `to-`/`outbound-` prefix, inside an `outbound/` folder")
    if first_line.startswith("# Outbound:") and name != "outbound.md" and "outbound" not in rel.split(os.sep)[:-1]:
        errors.append(f"{rel}: H1 genre is Outbound, so the file must live in an `outbound/` folder or be named `outbound.md`")
    return errors


def test_outbound_naming():
    """Outbound guides: no `to-*.md` / `outbound-*.md` names; genre Outbound lives in `outbound/` or `outbound.md`."""
    regional = os.path.join(ROOT, "references", "regional")
    errors = []
    for path in sorted(glob.glob(os.path.join(regional, "**", "*.md"), recursive=True)):
        with open(path, encoding="utf-8") as fh:
            first = fh.readline()
        errors.extend(outbound_naming_errors(os.path.relpath(path, ROOT), first))
    assert not errors, "Outbound naming convention (CONTRIBUTING.md, Reference file format):\n" + "\n".join(errors)

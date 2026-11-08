"""Reference files follow the format in CONTRIBUTING.md ("Reference file format").

Files that do not comply yet are listed in LEGACY. The list only shrinks: a listed file that
now complies fails the test (remove it), and a file outside it that violates fails too.
"""
import os
import re
import subprocess

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SCOPE = ("references/regional/", "references/certifications/", "references/fields/")
GENRES = (
    "Market", "Education", "Regulated professions", "Health professions", "Academic", "Outbound",
    "Law", "Field pack", "Certifications", "Foreign workers", "Gulf nationalisation", "Gulf credentials",
)
H1 = re.compile(r"^# (?:%s): \S" % "|".join(GENRES))
URL = re.compile(r"https?://")
QUOTED = re.compile(r"«[^»]*»")
DATE_VERB = re.compile(r"\b(?:accessed|retrieved|consulté|read)\s+(?:on\s+|le\s+)?(?:\d{4}\b|\d{1,2}\s)", re.I)
CONFIDENCE = re.compile(
    r"\b(?:HIGH|MEDIUM)\b|\bunverified\b|\bnot sourced\b|\bLOW confidence\b|\bLOW\b(?!, unsourced)", re.I
)
CASE_SENSITIVE = {"HIGH", "MEDIUM", "LOW"}

# Not aligned yet; remove each path when aligned.
LEGACY = {
    "references/certifications/finance-accounting.md",
    "references/certifications/health.md",
    "references/certifications/languages.md",
    "references/certifications/project-hr.md",
    "references/certifications/quality.md",
    "references/certifications/rules.md",
    "references/certifications/safety-professional.md",
    "references/certifications/teaching-english.md",
    "references/certifications/tech.md",
    "references/fields/academic.md",
    "references/fields/software-dev.md",
    "references/fields/trades.md",
    "references/regional/africa/maghreb-outbound/common.md",
    "references/regional/africa/maghreb-outbound/to-europe.md",
    "references/regional/africa/maghreb-outbound/to-quebec-canada.md",
    "references/regional/africa/maghreb-outbound/transnational.md",
    "references/regional/asia/east-asia/japan.md",
    "references/regional/asia/east-asia/korea.md",
    "references/regional/asia/east-asia/taiwan.md",
    "references/regional/asia/outbound/china.md",
    "references/regional/asia/outbound/common.md",
    "references/regional/asia/outbound/philippines.md",
    "references/regional/asia/outbound/south-asia.md",
    "references/regional/asia/southeast-asia/indonesia.md",
    "references/regional/asia/southeast-asia/malaysia.md",
    "references/regional/asia/southeast-asia/philippines.md",
    "references/regional/asia/southeast-asia/singapore.md",
    "references/regional/asia/southeast-asia/thailand.md",
    "references/regional/asia/southeast-asia/vietnam.md",
    "references/regional/europe/austria.md",
    "references/regional/europe/france.md",
    "references/regional/europe/germany.md",
    "references/regional/europe/ireland.md",
    "references/regional/europe/spain.md",
    "references/regional/europe/switzerland.md",
    "references/regional/europe/to-north-america.md",
    "references/regional/europe/uk.md",
    "references/regional/asia/india/market.md",
    "references/regional/asia/india/to-anglosphere.md",
    "references/regional/asia/india/to-europe/common.md",
    "references/regional/asia/india/to-europe/france.md",
    "references/regional/asia/india/to-europe/germany.md",
    "references/regional/asia/india/to-europe/ireland.md",
    "references/regional/asia/india/to-europe/netherlands.md",
    "references/regional/latin-america/argentina.md",
    "references/regional/latin-america/brazil.md",
    "references/regional/latin-america/chile.md",
    "references/regional/latin-america/colombia.md",
    "references/regional/latin-america/mexico.md",
    "references/regional/middle-east/gulf/credentials.md",
    "references/regional/middle-east/gulf/credentials/saudi-arabia.md",
    "references/regional/middle-east/gulf/credentials/uae.md",
    "references/regional/middle-east/gulf/market.md",
    "references/regional/middle-east/gulf/nationalisation.md",
    "references/regional/middle-east/gulf/nationalisation/saudi-arabia.md",
    "references/regional/middle-east/near-east/jordan-foreign-workers.md",
    "references/regional/middle-east/near-east/outbound.md",
    "references/regional/middle-east/near-east/turkiye-foreign-workers.md",
    "references/regional/north-america/aviation.md",
    "references/regional/north-america/canada/financial-licensing.md",
    "references/regional/north-america/canada/francophone.md",
    "references/regional/north-america/canada/government.md",
    "references/regional/north-america/canada/health.md",
    "references/regional/north-america/canada/law.md",
    "references/regional/north-america/canada/market.md",
    "references/regional/north-america/canada/teaching.md",
    "references/regional/north-america/canada/trades.md",
    "references/regional/north-america/common.md",
    "references/regional/north-america/driving.md",
    "references/regional/north-america/quebec/education.md",
    "references/regional/north-america/quebec/financial-licensing.md",
    "references/regional/north-america/quebec/health.md",
    "references/regional/north-america/quebec/law.md",
    "references/regional/north-america/quebec/market.md",
    "references/regional/north-america/quebec/outbound-canada.md",
    "references/regional/north-america/quebec/outbound-france.md",
    "references/regional/north-america/quebec/outbound-us.md",
    "references/regional/north-america/quebec/teaching.md",
    "references/regional/north-america/quebec/trades-safety.md",
    "references/regional/north-america/quebec/trades.md",
    "references/regional/north-america/us/financial-licensing.md",
    "references/regional/north-america/us/government.md",
    "references/regional/north-america/us/health.md",
    "references/regional/north-america/us/law.md",
    "references/regional/north-america/us/market.md",
    "references/regional/north-america/us/teaching.md",
    "references/regional/north-america/workplace-safety.md",
    "references/regional/oceania/australia.md",
    "references/regional/oceania/new-zealand.md",
}


def in_scope_files():
    out = subprocess.run(["git", "ls-files", "*.md"], cwd=ROOT, capture_output=True, text=True, check=True)
    result = []
    for path in out.stdout.split("\n"):
        name = os.path.basename(path)
        if not path.startswith(SCOPE) or name.endswith("-common.md") or name == "overview.md":
            continue
        text = read(path)
        if len(text.split()) >= 80:
            result.append(path)
    return result


def read(path):
    with open(os.path.join(ROOT, path), encoding="utf-8") as fh:
        return fh.read()


def prose(text):
    """Text outside fenced code blocks."""
    fence = False
    kept = []
    for line in text.split("\n"):
        if line.lstrip().startswith("```"):
            fence = not fence
        elif not fence:
            kept.append(line)
    return kept


def violations(path):
    lines = prose(read(path))
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
    for n, line in enumerate(lines, 1):
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
    errors = []
    files = in_scope_files()
    assert files, "no in-scope reference files found"
    for path in files:
        problems = violations(path)
        if path in LEGACY and not problems:
            errors.append(f"{path}: now complies, remove it from LEGACY")
        elif path not in LEGACY and problems:
            errors.extend(f"{path}: {p}" for p in problems)
    stale = LEGACY - set(files)
    errors.extend(f"{p}: in LEGACY but not an in-scope file" for p in sorted(stale))
    assert not errors, "\n".join(errors)

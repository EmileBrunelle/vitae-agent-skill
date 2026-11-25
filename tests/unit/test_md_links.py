"""Relative links between the repo's Markdown files must resolve (file and #anchor)."""
import os
import re
import subprocess

import pytest
from _paths import ROOT

LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
HEADING = re.compile(r"^#{1,6}\s+(.*?)\s*#*\s*$")


def md_files():
    out = subprocess.run(["git", "ls-files", "*.md"], cwd=ROOT, capture_output=True, text=True, check=True)
    return [f for f in out.stdout.split("\n") if f]


def prose_lines(path):
    """Lines of a file outside fenced code blocks. `path` is repo-relative (or absolute)."""
    fence = False
    with open(ROOT / path, encoding="utf-8") as fh:
        for n, line in enumerate(fh, 1):
            if line.lstrip().startswith("```"):
                fence = not fence
            elif not fence:
                yield n, line


def slug(heading):
    """GitHub anchor: lowercase, drop punctuation, spaces to hyphens."""
    text = re.sub(r"[`*_]", "", heading.lower())
    return re.sub(r"[^\w\- ]", "", text).replace(" ", "-")


def anchors(path):
    """Every anchor GitHub generates for the file's headings: a repeated heading gets -1, -2, ..."""
    seen, out = {}, set()
    for _, line in prose_lines(path):
        if m := HEADING.match(line):
            base = slug(m.group(1))
            n = seen.get(base, 0)
            seen[base] = n + 1
            out.add(base if n == 0 else f"{base}-{n}")
    return out


@pytest.mark.lint
def test_relative_md_links_resolve():
    errors = []
    for src in md_files():
        for n, line in prose_lines(src):
            for target in LINK.findall(line):
                if re.match(r"(https?:|mailto:)", target):
                    continue
                path, _, frag = target.partition("#")
                dest = os.path.normpath(os.path.join(os.path.dirname(src), path)) if path else src
                if not os.path.exists(ROOT / dest):
                    errors.append(f"{src}:{n}: missing file {target}")
                elif frag and dest.endswith(".md") and frag not in anchors(dest):
                    errors.append(f"{src}:{n}: no heading #{frag} in {dest}")
    assert not errors, "\n".join(errors)


# --- the helpers the lint relies on ---------------------------------------------------------------------------

@pytest.mark.parametrize("heading, expected", [
    ("Hello World", "hello-world"),
    ("Why `pick_design` & co?", "why-pickdesign--co"),   # backticks/underscores stripped, & dropped, both spaces kept
    ("Décisions déjà prises", "décisions-déjà-prises"),                    # accents and unicode letters survive
    ("1. Setup (v2.0)", "1-setup-v20"),
    ("Keep-this-hyphen", "keep-this-hyphen"),
    ("**Bold** and *italic*", "bold-and-italic"),
])
def test_slug(heading, expected):
    assert slug(heading) == expected


def test_anchors_number_duplicate_headings(tmp_path):
    md = tmp_path / "d.md"
    md.write_text("# Intro\n## Usage\n## Usage\n## Usage\n", encoding="utf-8")
    assert anchors(md) == {"intro", "usage", "usage-1", "usage-2"}


def test_anchors_ignore_fenced_code_and_closing_hashes(tmp_path):
    md = tmp_path / "f.md"
    md.write_text("## Real ##\n```\n# not a heading\n```\n####### seven hashes\n", encoding="utf-8")
    assert anchors(md) == {"real"}

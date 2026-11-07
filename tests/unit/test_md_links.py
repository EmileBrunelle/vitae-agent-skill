"""Relative links between the repo's Markdown files must resolve (file and #anchor)."""
import os
import re
import subprocess

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
HEADING = re.compile(r"^#{1,6}\s+(.*?)\s*#*\s*$")


def md_files():
    out = subprocess.run(["git", "ls-files", "*.md"], cwd=ROOT, capture_output=True, text=True, check=True)
    return [f for f in out.stdout.split("\n") if f]


def prose_lines(path):
    """Lines of a file outside fenced code blocks."""
    fence = False
    with open(os.path.join(ROOT, path), encoding="utf-8") as fh:
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
    return {slug(m.group(1)) for _, line in prose_lines(path) if (m := HEADING.match(line))}


def test_relative_md_links_resolve():
    errors = []
    for src in md_files():
        for n, line in prose_lines(src):
            for target in LINK.findall(line):
                if re.match(r"(https?:|mailto:)", target):
                    continue
                path, _, frag = target.partition("#")
                dest = os.path.normpath(os.path.join(os.path.dirname(src), path)) if path else src
                if not os.path.exists(os.path.join(ROOT, dest)):
                    errors.append(f"{src}:{n}: missing file {target}")
                elif frag and dest.endswith(".md") and frag not in anchors(dest):
                    errors.append(f"{src}:{n}: no heading #{frag} in {dest}")
    assert not errors, "\n".join(errors)

"""SKILL.md frontmatter must be valid YAML: skill loaders and GitHub parse it strictly.

A plain (unquoted) scalar may not contain ": " or " #" — `(pip-only: typst …)` in
`compatibility:` broke GitHub's rendering from 0.7.x to 0.9.1. The plain-scalar rule is
checked without PyYAML (not a dependency); a full parse also runs when PyYAML is present.
"""
import os
import re

import pytest

SKILL = os.path.join(os.path.dirname(__file__), "..", "..", "SKILL.md")


def _frontmatter() -> str:
    with open(SKILL, encoding="utf-8") as fh:
        text = fh.read()
    assert text.startswith("---\n"), "SKILL.md must open with a --- frontmatter block"
    return text[4:text.index("\n---", 4)]


def test_plain_scalars_have_no_mapping_or_comment_markers() -> None:
    for n, line in enumerate(_frontmatter().splitlines(), start=2):
        m = re.match(r"\s*[\w-]+:\s+(.*)$", line)
        if not m or m.group(1)[:1] in ('"', "'", "|", ">"):
            continue
        value = m.group(1)
        assert ": " not in value, f"SKILL.md line {n}: ': ' in an unquoted value is invalid YAML"
        assert " #" not in value, f"SKILL.md line {n}: ' #' in an unquoted value starts a YAML comment"


def test_parses_as_yaml() -> None:
    yaml = pytest.importorskip("yaml")
    data = yaml.safe_load(_frontmatter())
    assert {"name", "description", "metadata"} <= set(data)

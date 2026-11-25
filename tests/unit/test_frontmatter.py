"""SKILL.md frontmatter must be valid YAML: skill loaders and GitHub parse it strictly.

A plain (unquoted) scalar may not contain ": " or " #" — `(pip-only: typst …)` in
`compatibility:` broke GitHub's rendering from 0.7.x to 0.9.1. The plain-scalar rule is
checked textually, then the whole block is parsed with PyYAML (a hard test dependency: it is in the CI pip line).
"""
import re

import pytest
import yaml
from _paths import SKILL_MD

pytestmark = pytest.mark.lint


def _frontmatter() -> str:
    text = SKILL_MD.read_text(encoding="utf-8")
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
    data = yaml.safe_load(_frontmatter())
    assert {"name", "description", "metadata"} <= set(data)

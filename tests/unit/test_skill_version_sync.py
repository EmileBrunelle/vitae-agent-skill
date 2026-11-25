"""The version the JSON output reports is the one the changelog's latest released heading names. (Not in the mutmut
selection: under mutmut the module lives in mutants/, where the real SKILL.md is not at the expected relative path.)"""
import re

from _paths import ROOT
from vitae.verify import jsonout


def test_skill_version_matches_the_latest_released_changelog_heading():
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    latest = re.search(r"^## (\d+\.\d+\.\d+) - ", changelog, re.M)
    assert latest and jsonout.skill_version() == latest.group(1)

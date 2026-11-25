"""Repo path constants shared by the unit tests (pathlib only)."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
PICK_DESIGN = SCRIPTS / "pick_design.py"
SKILL_MD = ROOT / "SKILL.md"

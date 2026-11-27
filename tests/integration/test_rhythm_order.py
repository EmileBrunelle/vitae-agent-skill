"""Vertical rhythm order, every template: wrapped-line pitch < bullet pitch < entry pitch < section pitch.

tests/rhythm_measure.py compiles a copy of the template with two lengthened bullets and measures the pitches
(each step >= 1.5 pt). It runs here on the scratch copy, so no template file is touched.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from harness import ROOT, Template

if not all(shutil.which(t) for t in ("typst", "pdftotext")):
    pytest.skip("needs the typst CLI and pdftotext", allow_module_level=True)


def test_rhythm_order(template: Template, scratch: Path) -> None:
    typ = scratch / "templates" / "families" / template.family / f"{template.name}.typ"
    r = subprocess.run([sys.executable, str(ROOT / "tests" / "rhythm_measure.py"), str(typ)],
                       capture_output=True, text=True, timeout=60, check=False)
    assert r.returncode == 0, r.stdout + r.stderr

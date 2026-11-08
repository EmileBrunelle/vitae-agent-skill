"""verify.py --selftest: Drawn fill target, fill arguments, page count from the name, --all gating"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile

from vitae.core.base import LOWERED_FILL_FLOOR
from vitae.selftest.gates.fixtures import VERIFY_FILE
from vitae.verify.cv import (
    is_gated,
    pages_from_name,
)
from vitae.verify.source import _drawn_fill


def cv_header() -> None:
    """Drawn fill target, fill arguments, page count from the name, --all gating."""
    # --all's headerless fallback: the page count read off the name. Wrong
    # here and every 2-page deliverable is silently gated as a 1-pager.
    assert pages_from_name("a/resume-2page.typ") == "2"
    # drawn fill target: family table wins over header; no/disagreeing header WARNs
    # The family banner is the authority, not the editable header (CHANGELOG, drawn fill target). A header
    # beyond the first 3 lines counts as absent; with no family known the header is read on line 1 only.
    with tempfile.TemporaryDirectory(prefix="vitae-drawn-") as _td:
        from vitae.design.tables import FAMILIES as _FAMILIES
        _fam = next(iter(_FAMILIES))
        _exp = tuple(int(_x) for _x in _FAMILIES[_fam]["page"]["fill"].split("-"))
        _ft = os.path.join(_td, "cv.typ")
        for _body, _want_t, _want_w in (
                (f"// vitae: pages=1 fill={_exp[0]}-{_exp[1]}\n// FAMILY: {_fam}\n", _exp, 0),
                (f"// FAMILY: {_fam}\n", _exp, 1),
                (f"// vitae: pages=1 fill=50-60\n// FAMILY: {_fam}\n", _exp, 1),
                (f"// FAMILY: {_fam}\n\n\n\n// vitae: pages=1 fill=50-60\n", _exp, 1),
                ("// vitae: pages=1 fill=91-93\n", (91, 93), 0),
                ("// vitae: pages=1\n", None, 0),
                ("\n// vitae: pages=1 fill=91-93\n", None, 0)):
            with open(_ft, "w", encoding="utf-8") as _fh:
                _fh.write(_body)
            _dt, _dw = _drawn_fill(_ft)
            assert _dt == _want_t and len(_dw) == _want_w, (_body, _dt, _dw)
            assert all(str(_exp[0]) in _w and str(_exp[1]) in _w for _w in _dw), _dw
    # a non-integer fill argument exits non-zero with a FAIL line, never a ValueError traceback (CHANGELOG, drawn fill target)
    assert LOWERED_FILL_FLOOR == 60
    _r = subprocess.run([sys.executable, "-I", os.path.abspath(VERIFY_FILE), "x.typ", "1", "9x", "96"],
                        capture_output=True, text=True)
    assert _r.returncode != 0 and "FAIL  fill args must be integers" in _r.stdout, (_r.stdout, _r.stderr)
    assert "Traceback" not in _r.stderr, _r.stderr
    assert pages_from_name("a/resume.typ") == "1"
    # the name pattern is `[-_]2\s*p(ages)?` not followed by a letter: `2pager` and `12p` stay 1-page
    for n in ("CV_X_2p.typ", "cv_2page.typ", "cv_2pages.typ", "cv-2p.typ",
              "cv-2pages.typ", "CV-2 page.typ"):
        assert pages_from_name(n) == "2", n
    for n in ("CV_X_1p.typ", "cv_2pager.typ", "cv_12p.typ"):
        assert pages_from_name(n) == "1", n
    assert is_gated("CV_A_1p.typ") and not is_gated("Guide_X.typ")
    assert is_gated("Jane_Doe.typ") and is_gated("lebenslauf.typ")
    # --all gates every .typ except guide / letter / cover / lisez-moi / readme by name (NON_CV_RE); a
    # `// vitae:` header opts a file back in (Odd_Letter, Guide_Hdr), a headerless CV name is gated by default.
    with tempfile.TemporaryDirectory() as td:
        for n, body in (("Odd_Letter.typ", "// vitae: pages=1\n"),
                        ("Guide_Candidature_X.typ", "x\n"),
                        ("Guide_Hdr.typ", "// vitae: pages=1\n"),
                        ("Jane_Doe.typ", "x\n")):
            with open(os.path.join(td, n), "w", encoding="utf-8") as fh:
                fh.write(body)
        g = {n for n in os.listdir(td) if is_gated(os.path.join(td, n))}
        assert g == {"Odd_Letter.typ", "Guide_Hdr.typ", "Jane_Doe.typ"}, g
    assert pages_from_name("a/resume-pair-b.typ") == "1"
    assert pages_from_name("a/CV-2 page.typ") == "2"  # a space still counts
    assert pages_from_name("2page/resume.typ") == "1", "directory, not file"

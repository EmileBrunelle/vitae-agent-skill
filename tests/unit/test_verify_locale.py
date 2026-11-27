"""The verify gates read files as UTF-8 whatever the locale (a Windows code page, `LC_ALL=C`)."""
import json
import os
import re
import subprocess
import sys

import _locale_probe
from _paths import SKILL_MD


def _expected_version():
    head = SKILL_MD.read_text(encoding="utf-8").split("\n---", 2)[0]
    m = re.search(r'^\s+version:\s*"?([^"\s]+)"?\s*$', head, re.MULTILINE)
    assert m is not None
    return m.group(1)


def test_reads_of_non_ascii_files_do_not_depend_on_the_locale(tmp_path):
    expected = {
        "gated": True, "lib": ["WARN"], "academic": True, "letter": True, "leading_warn": True, "size_warn": True,
        "check_cv_accent_warn": True, "sweep": [0, True], "record": ["INFO", "True"],
        "layout": "Layout review: subagent haiku — café", "version": _expected_version(),
    }
    in_process = _locale_probe.run(tmp_path / "in-process")
    family_default = in_process.pop("family_default")
    assert len(family_default) == 2 and all(x > 0 for x in family_default)
    assert in_process == expected

    env = dict(os.environ, LC_ALL="C", LANG="C", PYTHONUTF8="0", PYTHONIOENCODING="ascii:backslashreplace")
    env.pop("PYTHONCOERCECLOCALE", None)
    r = subprocess.run([sys.executable, "-X", "utf8=0", _locale_probe.__file__, json.dumps(sys.path), str(tmp_path / "ascii")],
                       env=env, capture_output=True, text=True, cwd=os.getcwd(), check=False)     # mutmut finds its config from the working directory
    assert r.returncode == 0, r.stderr[-1500:]
    out = json.loads(r.stdout)
    assert out.pop("family_default") == family_default
    assert out == expected

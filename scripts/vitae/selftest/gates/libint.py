"""verify.py --selftest: lib.typ integrity: current / different / no import"""

from __future__ import annotations

import os
import tempfile
from collections.abc import Callable
from typing import Any

from vitae.verify.cv import (
    check_lib_integrity,
)


def lib_integrity() -> None:
    """lib.typ integrity: current / different / no import."""
    # lib.typ integrity: current / different (older or edited) / no import
    # check_lib_integrity: a lib.typ next to the CV that matches the skill's current one (CRLF and BOM
    # tolerated) is silent, any other content (older release or rewrite) FAILs with the `cp` that restores it,
    # and a CV that does not really import it (commented, in a raw span) WARNs.
    with tempfile.TemporaryDirectory() as _li_d:
        _li_sk = os.path.join(_li_d, "skill"); _li_cv = os.path.join(_li_d, "cv")
        os.makedirs(os.path.join(_li_sk, "templates")); os.makedirs(_li_cv)
        _li_w: Callable[[str, str], int] = lambda p, t: open(p, "w", encoding="utf-8").write(t)
        _li_w(os.path.join(_li_sk, "templates", "lib.typ"), "#let derive() = 1\n")
        _li_w(os.path.join(_li_cv, "cv.typ"), '#import "lib.typ": *\n')
        _li_chk: Callable[[], list[Any]] = lambda: check_lib_integrity(os.path.join(_li_cv, "cv.typ"), _li_sk)
        _li_w(os.path.join(_li_cv, "lib.typ"), "#let derive() = 1\n")
        assert _li_chk() == [], _li_chk()
        _li_w(os.path.join(_li_cv, "lib.typ"), "#let old = 1\n")
        _li_r = _li_chk()
        assert [l for l, _ in _li_r] == ["FAIL"] and "differs from the skill's" in _li_r[0][1] and "cp " in _li_r[0][1], _li_r
        _li_w(os.path.join(_li_cv, "lib.typ"), "#let mine = 1\n")
        _li_r = _li_chk()
        assert [l for l, _ in _li_r] == ["FAIL"] and "cp " in _li_r[0][1], _li_r
        _li_w(os.path.join(_li_cv, "cv.typ"), "hello\n")
        assert [l for l, _ in _li_chk()] == ["WARN"], _li_chk()      # lib next to CV, no import: never silent
        os.remove(os.path.join(_li_cv, "lib.typ"))
        assert _li_chk() == []
        _li_w(os.path.join(_li_cv, "lib.typ"), "#let mine = 1\n")
        # CRLF copy of the current lib is still current; commented / root-absolute imports
        open(os.path.join(_li_cv, "lib.typ"), "wb").write(b"#let derive() = 1\r\n")
        _li_w(os.path.join(_li_cv, "cv.typ"), '#import "lib.typ": *\n')
        assert _li_chk() == [], _li_chk()
        _li_w(os.path.join(_li_cv, "cv.typ"), '// #import "lib.typ": *\n/* #import "lib.typ" */\n')
        assert [l for l, _ in _li_chk()] == ["WARN"], _li_chk()     # commented imports do not count
        for _src, _lexp in (('#{ import "lib.typ": * }\n', "FAIL"), ('#import("lib.typ")\n', "FAIL"),
                           ('/* a /* b */ #import "lib.typ" */\n#set page()\n', "WARN"),
                           ('a 6" pipe\n#import "lib.typ": *\n', "FAIL"),
                           ('`#import "lib.typ"`\n', "WARN")):
            _li_w(os.path.join(_li_cv, "lib.typ"), "#let mine = 1\n")
            _li_w(os.path.join(_li_cv, "cv.typ"), _src)
            assert [l for l, _ in _li_chk()] == [_lexp], (_src, _li_chk())
        open(os.path.join(_li_cv, "lib.typ"), "wb").write(b"\xef\xbb\xbf#let derive() = 1\n")
        _li_w(os.path.join(_li_cv, "cv.typ"), '#import "lib.typ": *\n')
        assert _li_chk() == [], "BOM lib must not false-FAIL"
        open(os.path.join(_li_cv, "cv.typ"), "wb").write(b'// caf\xe9\n#import "lib.typ": *\n')
        assert _li_chk() == [], "non-UTF-8 cv must not crash"
        os.makedirs(os.path.join(_li_cv, "sub"))
        _li_w(os.path.join(_li_cv, "sub", "cv.typ"), '#import "/lib.typ": *\n')
        _li_w(os.path.join(_li_cv, "lib.typ"), "#let mine = 1\n")
        _li_r = check_lib_integrity(os.path.join(_li_cv, "sub", "cv.typ"), _li_sk)
        assert [l for l, _ in _li_r] == ["FAIL"], _li_r
        assert "cp " in _li_r[0][1]
        # family template copied without changing the import: lib.typ goes NEXT TO cv.typ
        _li_gp = os.path.join(_li_d, "g", "p", "mycv"); os.makedirs(_li_gp)
        _li_w(os.path.join(_li_gp, "cv.typ"), '#import "../../lib.typ": *\n')
        _li_r = check_lib_integrity(os.path.join(_li_gp, "cv.typ"), _li_sk)
        assert [l for l, _ in _li_r] == ["FAIL"] and '#import "lib.typ": *' in _li_r[0][1], _li_r
        assert f"{_li_gp}/" in _li_r[0][1] and f"{_li_d}/g/ " not in _li_r[0][1], _li_r

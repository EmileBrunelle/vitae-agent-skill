"""verify.py --selftest: The tuner regex: read, write and round-trip a par declaration"""

from __future__ import annotations

import os
import tempfile

from vitae.core.base import LEADING_WARN
from vitae.core.env import preflight
from vitae.verify.tune import tune
from vitae.verify.typst import _doc_leading, _read_par, _write_par


def par_regex() -> None:
    """The tuner regex: read, write and round-trip a par declaration."""
    # The one piece of non-trivial logic here that can break silently: the
    # regex the tuner edits with. A miss makes --tune a no-op that still
    # reports success, so it gets a check.
    src = ('#set page(paper: "us-letter")\n'
           '#set par(justify: false, leading: 0.555em, spacing: 0.615em)\n'
           'body 0.999em\n')
    assert _read_par(src) == (0.555, 0.615), _read_par(src)
    out = _write_par(src, 0.61, 0.7)
    assert "leading: 0.610em, spacing: 0.700em" in out, out
    assert "body 0.999em" in out, "edited past the par declaration"
    assert _read_par(out) == (0.610, 0.700)


def par_reader() -> None:
    """The par reader and the leading reader (_read_par, _doc_leading)."""
    # a file with no par declaration must be reported, never guessed at
    assert _read_par("#set text(size: 10.5pt)\n") is None
    # spacing-before-leading is not the template's order and must not match
    # silently in a way that swaps the two values
    alt = "#set par(spacing: 0.7em, leading: 0.6em)\n"
    assert _read_par(alt) is None, "would write the two values swapped"
    # the WARN reader: any argument order, em or pt, top-level only, last one wins
    assert _doc_leading("#set par(leading: 1.2em)\n") == 1.2
    assert _doc_leading("#set par(spacing: 0.7em, leading: 1.3em)\n") == 1.3
    assert _doc_leading("#set par(leading: 0.6em, spacing: 8pt)\n") == 0.6
    assert abs((_doc_leading("#set par(leading: 14pt)\n") or 0) - 14 / 11) < 1e-9
    assert abs((_doc_leading("#set text(size: 10pt)\n#set par(leading: 14pt, justify: true)\n") or 0) - 1.4) < 1e-9
    assert _doc_leading("#set par(leading: 0.6em)\n#set par(leading: 1.2em)\n") == 1.2
    assert _doc_leading("#let h(b) = {\n  #set par(leading: 1.5em)\n  b\n}\n#set par(leading: 0.6em)\n") == 0.6
    assert _doc_leading("#let h(b) = [\n#set par(leading: 1.5em)\n b]\n") is None
    assert _doc_leading("#show heading: it => [\n#set par(leading: 1.5em)\n#it]\n#set par(leading: 0.6em)\n") == 0.6
    assert _doc_leading("#set par(leading: 0.6em)\nBody\n#set par(leading: 1.5em)\n") == 0.6
    assert _doc_leading("// #set par(leading: 1.5em)\n#set text(size: 10pt)\n") is None


def tuner_cap() -> None:
    """Tuner cap: under-filled doc FAILs with content advice, leading clamped at the cap."""
    # Tuner cap: an under-filled doc must FAIL with content advice, the
    # leading clamped at the cap even when the caller passes 0.40 1.60; an
    # over-full doc keeps the old advice; a normal doc converges in the cap.
    if preflight()[0]:
        import contextlib
        import io
        def _tune_doc(nlines: int, *rng: float, fmin: int = 94
                      ) -> tuple[int, str, str | None, tuple[float, float] | None]:
            with tempfile.TemporaryDirectory() as _d:
                _f = os.path.join(_d, "t.typ")
                _body = "".join("Line %d of body text.\\\n" % i for i in range(nlines))
                open(_f, "w", encoding="utf-8").write(
                    '#set page(paper: "us-letter", margin: 0.75in)\n'
                    '#set text(size: 10pt)\n'
                    '#set par(leading: 0.6em, spacing: 0.7em)\n' + _body)
                _b = io.StringIO()
                with contextlib.redirect_stdout(_b):
                    _rc, _footer = tune(_f, 1, fmin, 96, *rng)
                return _rc, _b.getvalue(), _footer, _read_par(open(_f).read())
        _trc, _to, _tft, _tpar = _tune_doc(15, 0.40, 1.60)
        assert _trc == 1 and "UNDER-FILLED" in _to and "never invent" in _to, _to
        assert "clamped to 1.000em" in _to and "searching [0.400, 1.000]" in _to, _to
        assert "Widen the range" not in _to and _tft is not None and "under-filled" in _tft and _tpar == (0.6, 0.7), (_to, _tft)
        _trc, _to, _tft, _tpar = _tune_doc(70)
        assert _trc == 1 and "UNDER-FILLED" not in _to, _to
        _trc, _to, _tft, _tpar = _tune_doc(40, fmin=88)
        assert _trc == 0 and _tpar is not None and _tpar[0] <= LEADING_WARN + 1e-9, (_to, _tpar)

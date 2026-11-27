"""LOG320 worst-case sweep of placeholders.py: the linear e-mail sample scan and the once-per-span squash give exactly
what the replaced code gave (the old code is kept verbatim in _placeholders_ref.py; Hypothesis builds texts from the
fragments the scans react to: address characters, `@example.`, backslashes, brackets and the templates' own
placeholders), and stay fast on the worst case (`slow`)."""
import time
from collections.abc import Callable

import pytest
from _growth import GROWTH_BOUND, best_time, growth_ratio
from _placeholders_ref import check_placeholders_squashing, placeholders_in_scanning
from hypothesis import given, settings
from hypothesis import strategies as st
from vitae.core.context import VerifyContext
from vitae.verify import placeholders

_FRAGMENTS = ["a", "b1", "_", ".", "+", "-", "@", "\\", "\\@", "@example.", "@example.com", "@example.org", "example",
              ".com", " ", "\n", "[", "]", "[Mon YYYY]", "[City, Region]", "(555) 555-0100", "Firstname Lastname",
              "me@example.com", "x.y@example.net", "linkedin.com/in/handle", "#", "/*", "*/", "//", "ab c"]
_texts = st.lists(st.sampled_from(_FRAGMENTS), max_size=20).map("".join)


def _ctx(txt: str) -> VerifyContext:
    return VerifyContext(typ="", pdf="", txt=txt, src="", backend=None)


@settings(max_examples=1000, deadline=None)
@given(_texts)
def test_email_samples_are_the_matches_of_the_old_pattern(src: str) -> None:
    got = [(m.start(), m.end()) for m in placeholders._email_samples(src)]

    assert got == [(m.start(), m.end()) for m in placeholders._SAMPLES[0].finditer(src)]


@settings(max_examples=600, deadline=None)
@given(_texts)
def test_placeholders_in_matches_the_old_scan(src: str) -> None:
    assert placeholders.placeholders_in(src) == placeholders_in_scanning(src)


def test_email_sample_equivalence_is_not_vacuous() -> None:
    # control: a match after a match inside one run (the case the continuation handles), and runs that never match
    got = [m.group(0) for m in placeholders._email_samples("a@example.com.b@example.org +x@example.net..y")]

    assert got == ["a@example.com", ".b@example.org", "+x@example.net"]
    assert placeholders._email_samples("a.b+c-d@other.com") == []


@settings(max_examples=400, deadline=None)
@given(st.lists(st.sampled_from(["[Mon YYYY]", "[item]", "[ITEM]", "[linkedin.com/in/handle]", "[abc def]", "[x]",
                                 "me@example.com", "(555) 555-0100", "Firstname Lastname", "github.com/handle",
                                 "[a1]", "plain words", "[", "]", "\n", "  "]), max_size=16).map(" ".join))
def test_check_placeholders_matches_the_old_gate(txt: str) -> None:
    assert placeholders.check_placeholders(_ctx(txt)) == check_placeholders_squashing(_ctx(txt))


def test_check_placeholders_equivalence_is_not_vacuous() -> None:
    got = placeholders.check_placeholders(_ctx("Contact me@example.com or see [abc def] and [Mon YYYY]"))

    assert [lvl.name for lvl, _ in got] == ["FAIL", "WARN"]
    assert "[abc def]" in got[1][1]


@pytest.mark.slow
def test_email_samples_bound_time_on_long_runs_without_an_at_sign() -> None:
    src = "a" * 40000 + " " + ".+-" * 14000 + " " + "ab " * 50000
    start = time.perf_counter()

    out = placeholders.placeholders_in(src)

    assert time.perf_counter() - start < 1.0     # measured ~0.01 s; the old scan took ~15 s on these runs
    assert out == set()


@pytest.mark.slow
def test_check_placeholders_time_grows_linearly_with_the_bracketed_spans() -> None:
    known = " ".join(placeholders.placeholders_from(placeholders.TEMPLATES))   # ~65 hits whatever the size

    def prepare(spans: int) -> Callable[[], object]:
        ctx = _ctx(known + " " + "[abc def] " * spans)
        return lambda: placeholders.check_placeholders(ctx)

    assert growth_ratio(prepare, 15000) < GROWTH_BOUND
    assert best_time(prepare(30000)) < 2.0       # measured ~0.19 s idle; the squash per placeholder takes ~2.3 s: linear too, 12x slower
    assert [lvl.name for lvl, _ in placeholders.check_placeholders(_ctx(known + " [abc def]"))] == ["FAIL", "WARN"]

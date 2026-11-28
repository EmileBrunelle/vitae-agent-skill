"""The three comment strippers of vitae.core.typst_source: what each strips and where they deliberately differ."""
from collections.abc import Callable

import pytest
from _complexity import assert_linear, line_events
from _scan_str import ScanStr
from vitae.core.typst_source import strip_block_comments, strip_comments_keep_urls, strip_typst_comments

# (source, block-only, keep-urls, typst-aware)
CASES = [
    ("a /* x */ b", "a  b", "a  b", "a  b"),
    ("a // x\nb", "a // x\nb", "a \nb", "a \nb"),
    ("a /* x /* y */ z */ b", "a  z */ b", "a  z */ b", "a  b"),         # nesting
    ("a /* open", "a /* open", "a /* open", "a "),                         # unclosed block
    ("see https://x.y // c", "see https://x.y // c", "see https://x.y ", "see https://x.y "),
    ("a//b", "a//b", "a//b", "a"),                                         # word char before //
    ('"a // b" c', '"a // b" c', '"a ', '"a // b" c'),                     # string
    ("`a // b` c", "`a // b` c", "`a ", "  c"),                             # raw span
    ('6" // c\nd', '6" // c\nd', '6" \nd', '6" // c\nd'),                 # an open string runs to the newline
]


@pytest.mark.parametrize(("src", "block", "keep_urls", "typst"), CASES)
def test_each_stripper_on_its_cases(src: str, block: str, keep_urls: str, typst: str) -> None:
    assert strip_block_comments(src) == block
    assert strip_comments_keep_urls(src) == keep_urls
    assert strip_typst_comments(src) == typst


_SOURCE_FILES = frozenset({strip_block_comments.__code__.co_filename})


def _work(strip: Callable[[str], str], src: str) -> int:
    """Python line events in typst_source plus the characters `find` scans and slices copy (C-level work)."""
    ScanStr.reset()
    events, _ = line_events(_SOURCE_FILES, lambda: strip(ScanStr(src)))
    return events + ScanStr.scanned


@pytest.mark.parametrize("unit", ["/*", "`", "/", '"/*', "\\"])
@pytest.mark.parametrize("strip", [strip_block_comments, strip_comments_keep_urls, strip_typst_comments],
                         ids=lambda f: f.__name__)
def test_strippers_work_grows_linearly_on_adversarial_runs(strip: Callable[[str], str], unit: str) -> None:
    assert_linear(lambda n: _work(strip, unit * (n // len(unit))), 4000)


@pytest.mark.parametrize("strip", [strip_block_comments, strip_comments_keep_urls, strip_typst_comments],
                         ids=lambda f: f.__name__)
def test_find_based_strippers_scan_through_the_counted_find(strip: Callable[[str], str]) -> None:
    # the scan of an unclosed `/*` is a C-level `find`: if it stopped going through `find`, the count above is blind
    _work(strip, "/*" * 100 if strip is not strip_typst_comments else "// x\n" * 100)
    assert ScanStr.calls > 0
    assert ScanStr.scanned > 0

"""The three comment strippers of vitae.core.typst_source: what each strips and where they deliberately differ."""
import time

import pytest
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


@pytest.mark.parametrize("unit", ["/*", "`", "/", '"/*', "\\"])
def test_strippers_are_linear_on_adversarial_runs(unit: str) -> None:
    src = unit * 100_000
    for strip in (strip_block_comments, strip_comments_keep_urls, strip_typst_comments):
        t = time.perf_counter()
        strip(src)
        assert time.perf_counter() - t < 2.0, strip.__name__

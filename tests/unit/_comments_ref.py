"""Reference oracle for tests: the comment-stripping regex of `vitae.verify.placeholders` as it was before the linear
scan (quadratic on unclosed `/*`). Kept verbatim so the equivalence tests compare the new code with the behaviour it
replaced."""
import re

COMMENTS = re.compile(r"/\*.*?\*/|(?<![:\w])//[^\n]*", re.DOTALL)


def strip_comments_regex(src: str) -> str:
    return COMMENTS.sub("", src)


BLOCK_COMMENTS = re.compile(r"/\*.*?\*/", re.DOTALL)


def strip_block_comments_regex(src: str) -> str:
    """`vitae.verify.fonts.requested_families` first step before the linear scan (same quadratic shape)."""
    return BLOCK_COMMENTS.sub("", src)

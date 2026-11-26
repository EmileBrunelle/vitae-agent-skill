"""The scripts' own --selftest modes, run on the scratch copy."""
from __future__ import annotations

from collections.abc import Callable

import pytest
from harness import CheckResult, assert_passed


@pytest.mark.parametrize("script", ["verify", "pick_design"])
def test_selftest(script: str, check: Callable[..., CheckResult], py: str) -> None:
    assert_passed(check(f"selftest-{script}", [py, "-I", f"scripts/{script}.py", "--selftest"]))

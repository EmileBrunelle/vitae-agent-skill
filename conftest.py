"""Command-line options of the integration suite (tests/integration); they live here because pytest only reads
`pytest_addoption` from conftests it loads at start-up, and a run of `pytest tests` must accept them too."""
import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    group = parser.getgroup("vitae", "vitae integration suite")
    group.addoption("--vitae-out", default=None, metavar="DIR",
                    help="keep the template PDFs/PNGs in DIR/pdf and every check's log in DIR/log (default: a temp dir)")
    group.addoption("--quick", action="store_true", default=False,
                    help="integration suite: first 3 templates only, no spacing fixtures (`--quick`)")

"""Put scripts/ on sys.path so tests import the façades (`verify`, ...) and the `vitae` package.

Importing these modules has no side effect: main() is behind __main__. Shared path constants live in `_paths`.
"""
import sys

import pytest
from _paths import SCRIPTS

# Appended, not prepended: mutmut puts its mutated copy of the package (mutants/src) first, and it must win.
sys.path.append(str(SCRIPTS))


TEMPLATE_FAMILIES = {"Carlito", "Montserrat"}      # resume.typ fits its one page only with these (body, headings)


@pytest.fixture
def template_fonts():
    """Skip when the shipped resume.typ's fonts are not visible to Typst the way the gate resolves them (`typst fonts` /
    typst-py, honouring TYPST_FONT_PATHS and TYPST_IGNORE_SYSTEM_FONTS): with a fallback face it runs to 2 pages."""
    from vitae.core import env
    have = env.typst_fonts()
    if have is None:
        pytest.skip("no Typst font listing available (neither the typst CLI nor typst-py)")
    missing = sorted(TEMPLATE_FAMILIES - {f.strip() for f in have})
    if missing:
        pytest.skip(f"templates/resume.typ needs {', '.join(missing)} to fit one page; Typst does not see them")


@pytest.fixture
def tuner_original_compiles(monkeypatch):
    """The tuner compiles the CV once before fitting it. The tune tests inject their probes and use placeholder sources
    that Typst would refuse (no title), so that one compile is a success unless a test sets its own. Opt in with
    `pytestmark = pytest.mark.usefixtures("tuner_original_compiles")`."""
    from vitae.verify import tune
    monkeypatch.setattr(tune, "compile_pdf", lambda typ, pdf, use_cli: (True, ""))


@pytest.fixture(autouse=True)
def _fresh_typst_cli_decision():
    """`env.typst_cli_usable` is probed once per process; tests that fake `typst` on PATH need their own probe."""
    from vitae.core import env
    env.typst_cli_usable.cache_clear()
    yield
    env.typst_cli_usable.cache_clear()

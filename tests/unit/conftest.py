"""Put scripts/ on sys.path so tests import the façades (`verify`, ...) and the `vitae` package.

Importing these modules has no side effect: main() is behind __main__. Shared path constants live in `_paths`.
"""
import sys
from types import ModuleType

import pytest
from _paths import SCRIPTS
from hypothesis import settings

# Appended, not prepended: mutmut puts its mutated copy of the package (mutants/src) first, and it must win.
sys.path.append(str(SCRIPTS))

# Same examples on every run and every machine (a CI failure reproduces locally); `print_blob` prints the
# `@reproduce_failure` line of a failure; no deadline: the oracle comparisons and compiles have no stable timing.
settings.register_profile("vitae", derandomize=True, deadline=None, print_blob=True, database=None)
settings.load_profile("vitae")


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
def fresh_typst_probes():
    """Opt-in for the tests that fake `typst` on PATH (`shutil.which`, `subprocess.run`, an executable shim): the typst
    route and the CLI version are probed once per process, so these tests start and leave with no cached probe."""
    from vitae.core import env
    env._cli_probe.cache_clear()
    env.typst_route.cache_clear()
    yield
    env._cli_probe.cache_clear()
    env.typst_route.cache_clear()


@pytest.fixture
def fake_typst(fresh_typst_probes, monkeypatch):
    """Opt-in: fake the two probes the typst route is decided from. `install(cli=None, api=None, full=True)`: `cli` is the
    CLI's version ("0.15.0", "?" when it prints none; None = no CLI on PATH), `api` the typst-py module (None = no
    working package; its version is 0.15.2) and `full` whether it also queries and lists fonts."""
    from vitae.core import env

    def install(cli: str | None = None, api: ModuleType | None = None, full: bool = True) -> None:
        monkeypatch.setattr(env, "_cli_probe", lambda: cli)
        monkeypatch.setattr(env, "_typst_py_probe", lambda: env.TypstPyProbe(api, "0.15.2" if api else "", "", full and api is not None))
        env.typst_route.cache_clear()
    return install


@pytest.fixture
def typst_api_only(fake_typst):
    """Opt-in: every typst call goes through the real typst-py package, as with no CLI on PATH (skips without it)."""
    fake_typst(api=pytest.importorskip("typst"))


@pytest.fixture
def tuner_original_compiles(monkeypatch):
    """The tuner compiles the CV once before fitting it. The tune tests inject their probes and use placeholder sources
    that Typst would refuse (no title), so that one compile is a success unless a test sets its own. Opt in with
    `pytestmark = pytest.mark.usefixtures("tuner_original_compiles")`."""
    from vitae.verify import tune
    monkeypatch.setattr(tune, "compile_or_messages", lambda typ, pdf: ("", []))

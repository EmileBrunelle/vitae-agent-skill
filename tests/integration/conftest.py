"""Session fixtures of the integration suite: the scratch copy and the output dir.

verify.py writes PDFs next to the .typ and some checks write files into templates/, so every check runs on a scratch
copy and the repo stays clean. Parallelism is pytest-xdist's (`-n auto`): each worker has its own
session, hence its own scratch copy `<out>/work-<worker>` (`work-main` without xdist); `<out>/pdf` and `<out>/log` are
shared, every file in them named after its check.
"""
from __future__ import annotations

import importlib.util
import os
import shutil
import sys
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest
from harness import ROOT, SCRIPTS, CheckResult, Template, discover_templates, run_check

if str(SCRIPTS) not in sys.path:
    sys.path.append(str(SCRIPTS))

def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    if "template" in metafunc.fixturenames:
        ts = discover_templates()
        metafunc.parametrize("template", ts, ids=[t.check_name for t in ts])


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    for item in items:
        if "tests/integration" in item.nodeid.replace("\\", "/"):
            item.add_marker(pytest.mark.integration)


@pytest.fixture(scope="session")
def quick(request: pytest.FixtureRequest) -> bool:
    return bool(request.config.getoption("--quick"))


@pytest.fixture(scope="session")
def out_dir(request: pytest.FixtureRequest, tmp_path_factory: pytest.TempPathFactory) -> Path:
    opt = request.config.getoption("--vitae-out")
    d = Path(opt).resolve() if opt else tmp_path_factory.mktemp("vitae-out")
    (d / "pdf").mkdir(parents=True, exist_ok=True)
    (d / "log").mkdir(parents=True, exist_ok=True)
    return d


@pytest.fixture(scope="session")
def log_dir(out_dir: Path) -> Path:
    return out_dir / "log"


@pytest.fixture(scope="session")
def scratch(out_dir: Path) -> Path:
    """Scratch copy of what the checks need (what `pytest tests/integration` needs), in <out>/work-<xdist worker>."""
    s = out_dir / f"work-{os.environ.get('PYTEST_XDIST_WORKER', 'main')}"
    shutil.rmtree(s, ignore_errors=True)
    s.mkdir(parents=True)
    ignore = shutil.ignore_patterns("__pycache__", "*.pyc", "*.pdf", "*.png")
    for d in ("templates", "scripts", "references"):
        shutil.copytree(ROOT / d, s / d, ignore=ignore)
    (s / "tests").mkdir()
    for d in ("fixtures", "font_fallback", "language"):
        shutil.copytree(ROOT / "tests" / d, s / "tests" / d, ignore=ignore)
    for f in ("compare_backends.py",):
        shutil.copy2(ROOT / "tests" / f, s / "tests" / f)
    if (ROOT / "SKILL.md").is_file():
        shutil.copy2(ROOT / "SKILL.md", s)
    return s


@pytest.fixture(scope="session")
def py() -> str:
    return sys.executable


@pytest.fixture(scope="session")
def check(scratch: Path, log_dir: Path) -> Callable[..., CheckResult]:
    """check(name, argv, env=None, cwd=None): run one check on the scratch copy, logged under <out>/log."""
    def _check(name: str, argv: list[str], env: dict[str, str] | None = None, cwd: Path | None = None) -> CheckResult:
        return run_check(name, argv, cwd or scratch, env, log_dir)
    return _check


@pytest.fixture(scope="session")
def run_template(scratch: Path, out_dir: Path) -> Callable[[Template], CheckResult]:
    """run_template(t): verify.py on the template, then keep the PDF and a 60-dpi PNG in <out>/pdf (CI uploads them)."""
    def _run(t: Template) -> CheckResult:
        typ = scratch / "templates" / "families" / t.family / f"{t.name}.typ"
        r = run_check(t.check_name, [sys.executable, "-I", "scripts/verify.py", typ.relative_to(scratch), t.pages,
                                     t.fill_min, t.fill_max, "--allow-placeholders"], scratch, None, out_dir / "log")
        pdf = typ.with_suffix(".pdf")
        if pdf.is_file():
            shutil.copy2(pdf, out_dir / "pdf" / f"{t.family}-{t.name}.pdf")
            pdftoppm = shutil.which("pdftoppm")
            if pdftoppm:
                run_check(f"png/{t.family}-{t.name}", [pdftoppm, "-r", "60", "-png", "-singlefile", pdf,
                                                      out_dir / "pdf" / f"{t.family}-{t.name}"], scratch)
        return r
    return _run


@pytest.fixture
def _not_quick(quick: bool) -> None:
    if quick:
        pytest.skip("--quick: no fixtures")


@pytest.fixture(scope="session")
def fixtures_rendered(scratch: Path, out_dir: Path, log_dir: Path) -> tuple[CheckResult, Path]:
    """All spacing fixtures rendered once per worker (render.sh) into <out>/fixtures-<worker>: (the render's result, the dir)."""
    if not shutil.which("typst") and importlib.util.find_spec("typst") is None:
        pytest.skip("neither the typst CLI nor typst-py available")
    fx = out_dir / f"fixtures-{os.environ.get('PYTEST_XDIST_WORKER', 'main')}"
    shutil.rmtree(fx, ignore_errors=True)
    fx.mkdir(parents=True)
    # render.sh falls back on `python3 -c "import typst"` when there is no typst CLI: put the interpreter running
    # the suite (the venv holding typst-py) first on PATH so that python3 is the one with the module.
    env = {**os.environ, "PATH": f"{Path(sys.executable).parent}{os.pathsep}{os.environ.get('PATH', '')}"}
    return run_check("fixtures-render", ["bash", "tests/fixtures/render.sh", fx], scratch, env, log_dir), fx


@pytest.fixture(scope="module", params=["cli+poppler", "typst-py+pdfium"])
def toolchain(request: pytest.FixtureRequest) -> Iterator[str]:
    """The compile and read route of the gate: the reference tools, then the pure-Python ones (PATH hidden from the gate)."""
    if request.param == "cli+poppler":
        if not all(shutil.which(t) for t in ("typst", "pdftotext", "pdfinfo", "pdftoppm")):
            pytest.skip("typst CLI / poppler missing")
        yield request.param
        return
    if importlib.util.find_spec("typst") is None or importlib.util.find_spec("pypdfium2") is None:
        pytest.skip("typst-py / pypdfium2 missing")
    mp = pytest.MonkeyPatch()
    mp.setattr(shutil, "which", lambda *a, **k: None)
    yield request.param
    mp.undo()

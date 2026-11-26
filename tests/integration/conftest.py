"""Session fixtures of the integration suite: the scratch copy, the output dir, and the parallel batches.

verify.py writes PDFs next to the .typ and some checks write files into templates/, so every check runs on a scratch
copy (as run_all.sh does) and the repo stays clean. The slow subprocess checks of a group run concurrently once, on first
use; each parametrized test then asserts on its own cached result, so a failure is still reported per template/fixture.
"""
from __future__ import annotations

import shutil
import sys
from collections.abc import Callable
from pathlib import Path

import pytest
from harness import QUICK_TEMPLATES, ROOT, SCRIPTS, CheckResult, Template, discover_templates, run_check, run_parallel

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
    """Scratch copy of what the checks need (same set as run_all.sh), in <out>/work."""
    s = out_dir / "work"
    shutil.rmtree(s, ignore_errors=True)
    s.mkdir(parents=True)
    ignore = shutil.ignore_patterns("__pycache__", "*.pyc", "*.pdf", "*.png")
    for d in ("templates", "scripts", "references"):
        shutil.copytree(ROOT / d, s / d, ignore=ignore)
    (s / "tests").mkdir()
    for d in ("fixtures", "font_fallback", "language"):
        shutil.copytree(ROOT / "tests" / d, s / "tests" / d, ignore=ignore)
    for f in ("compare_backends.py", "test_look.py"):
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


def _tpl_run(t: Template, scratch: Path, out_dir: Path) -> CheckResult:
    """verify.py on the template, then keep the PDF and a 60-dpi PNG in <out>/pdf (CI uploads them)."""
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


@pytest.fixture(scope="session")
def template_results(scratch: Path, out_dir: Path, quick: bool) -> dict[str, CheckResult]:
    """Every template check, run concurrently once; keyed by check name."""
    ts = discover_templates()
    ts = ts[:QUICK_TEMPLATES] if quick else ts
    return run_parallel({t.check_name: (lambda t=t: _tpl_run(t, scratch, out_dir)) for t in ts})


@pytest.fixture(scope="session")
def fixture_results(scratch: Path, out_dir: Path, log_dir: Path) -> dict[str, CheckResult]:
    """Spacing fixtures: render them all (render.sh), then the backends comparison and one --gates run per fixture, concurrently."""
    fx = out_dir / "fixtures"
    shutil.rmtree(fx, ignore_errors=True)
    fx.mkdir(parents=True)
    results: dict[str, CheckResult] = {"fixtures-render": run_check("fixtures-render", ["bash", "tests/fixtures/render.sh", fx],
                                                                    scratch, None, log_dir)}
    jobs: dict[str, Callable[[], CheckResult]] = {}
    pdfs = sorted(fx.glob("*.pdf"))
    if pdfs:
        jobs["backends/lines"] = lambda: run_check("backends/lines", [sys.executable, "-I", "tests/compare_backends.py", *pdfs],
                                                  scratch, None, log_dir)
    for typ in sorted((scratch / "tests" / "fixtures").glob("*.typ")):
        nm = typ.stem
        pdf = fx / f"{nm}.pdf"
        if pdf.is_file():
            jobs[f"gates/{nm}"] = lambda nm=nm, typ=typ, pdf=pdf: run_check(
                f"gates/{nm}", [sys.executable, "-I", "scripts/verify.py", "--gates", typ.relative_to(scratch), pdf,
                                "--root", "."], scratch, None, log_dir)
        else:
            results[f"gates/{nm}"] = CheckResult(f"gates/{nm}", 1, f"FAIL gates/{nm} (no PDF rendered)", None)
    results.update(run_parallel(jobs))
    return results

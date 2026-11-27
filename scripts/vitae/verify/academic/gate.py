"""Academic gate: compile, extract, run the checks against the declared TOML."""
from __future__ import annotations

import os
import shutil
import tempfile
import tomllib

import vitae.fill as measure_fill
from vitae.core.env import preflight
from vitae.core.level import Level
from vitae.verify.academic.checks import analyze
from vitae.verify.academic.parse import extract_layout_text
from vitae.verify.academic.spec import build_sections_spec, check_headings_table, declared_statuses, printed_headings
from vitae.verify.pdf import compile_or_messages, count_pages, render_pngs, run_memo
from vitae.verify.text import check_hidden_text


def hidden_text_msgs(pdf: str) -> list[tuple[bool | None, str]]:
    """The shared hidden-text gate as (is_fail, msg) pairs; is_fail None = WARN."""
    return [(True if lvl == Level.FAIL else None, msg) for lvl, msg in check_hidden_text(pdf)]


def run_gate(typ: str, toml_path: str) -> tuple[bool, list[tuple[bool | None, str]], list[str]]:
    """`_run_gate` in its own memo scope (as `check_cv` does): each tool runs once per file state in this run only."""
    with run_memo():
        return _run_gate(typ, toml_path)


def _run_gate(typ: str, toml_path: str) -> tuple[bool, list[tuple[bool | None, str]], list[str]]:
    """Compile `typ`, run the checks against the declared `toml_path`.
    Returns (passed, (is_fail, msg) pairs, reported-only INFO lines); is_fail None = WARN."""
    pf = preflight()
    backend = pf.backend
    ok = pf.ok and bool(shutil.which("pdftotext"))
    if not ok:
        return False, [(True, "missing dependency -- see --doctor output above")], []

    with open(toml_path, "rb") as f:
        data = tomllib.load(f)
    sections = build_sections_spec(data)
    statuses = declared_statuses(data)
    surname = data["meta"]["name"].split(" ")[-1]    # the running head prints the last space-separated word of the name

    # NOTE: deliberately no ensure_icons(typ) here -- lib-academic.typ
    # never imports icons.typ (icons/photo are an explicit anti-goal for this
    # genre, fields/academic.md "Never on an academic CV"), so that plumbing would just write an
    # unused file under templates/academic/.
    with tempfile.TemporaryDirectory() as tmp:
        pdf = os.path.join(tmp, "cv.pdf")
        _, failed = compile_or_messages(typ, pdf)
        if failed:
            return False, [(True, m) for m in failed], []

        text = extract_layout_text(pdf)
        extra, declared = printed_headings(data)
        results, total_pages = analyze(text, sections, surname, extra, statuses, declared)
        results = check_headings_table(data) + results

        # ---- reported-only metrics (never failed): page count, last-page
        # fill, and a rough prose/list share. academic-mode.md "Correctness properties" and "What does not apply here".
        reported = [f'{total_pages} page(s)']
        pages_from_cli = count_pages(pdf, backend)
        if pages_from_cli and str(pages_from_cli) != str(total_pages):
            reported.append(f'note: pdfinfo reports {pages_from_cli} page(s)')
        pngs = render_pngs(typ, tmp)
        unrendered: list[tuple[bool | None, str]] = []
        if pngs:
            reported.append(f'last-page fill: {measure_fill.measure(pngs[-1])}')
        else:
            unrendered.append((True, "vitae: no PNG rendered, so the last-page fill is unmeasured"))
        hidden = hidden_text_msgs(pdf) + unrendered

    msgs = [(not ok, msg) for _, ok, msg in results] + hidden
    fail = any(not ok for _, ok, _ in results) or any(f for f, _ in hidden if f)
    return not fail, msgs, reported

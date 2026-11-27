"""A failed PNG render is never read as "no page to check": render_pngs returns [] (stale files included) and the
academic gate FAILs with a vitae message instead of passing without its raster measurement."""
from pathlib import Path

import pytest
from vitae.verify import pdf
from vitae.verify.academic import gate


def test_failed_render_returns_no_page_even_with_stale_pngs(tmp_path, monkeypatch):
    (tmp_path / "p1.png").write_bytes(b"stale")
    monkeypatch.setattr(pdf, "_typst_compile", lambda *a, **k: (False, "boom"))
    assert pdf.render_pngs(str(tmp_path / "a.typ"), str(tmp_path)) == []


def test_successful_render_lists_the_pages_in_order(tmp_path, monkeypatch):
    def fake(src, out, **_kw):
        for n in (1, 2):
            Path(out.replace("{p}", str(n))).write_bytes(b"png")
        return True, ""
    monkeypatch.setattr(pdf, "_typst_compile", fake)
    assert [Path(p).name for p in pdf.render_pngs("a.typ", str(tmp_path))] == ["p1.png", "p2.png"]


@pytest.fixture
def academic_gate(tmp_path, monkeypatch):
    toml = tmp_path / "d.toml"
    toml.write_text('[meta]\nname = "Ada Doe"\n', encoding="utf-8")
    monkeypatch.setattr(gate, "preflight", lambda: (True, "pdftoppm"))
    monkeypatch.setattr(gate.shutil, "which", lambda name: "/usr/bin/" + name)
    monkeypatch.setattr(gate, "build_sections_spec", lambda data: [])
    monkeypatch.setattr(gate, "declared_statuses", lambda data: {})
    monkeypatch.setattr(gate, "compile_or_messages", lambda typ, out: ("", []))
    monkeypatch.setattr(gate, "extract_layout_text", lambda out: "")
    monkeypatch.setattr(gate, "printed_headings", lambda data: ([], []))
    monkeypatch.setattr(gate, "analyze", lambda *a: ([], 1))
    monkeypatch.setattr(gate, "check_headings_table", lambda data: [])
    monkeypatch.setattr(gate, "count_pages", lambda out, backend: "1")
    monkeypatch.setattr(gate, "hidden_text_msgs", lambda out: [])
    return str(toml)


def test_academic_gate_fails_when_no_png_was_rendered(academic_gate, monkeypatch):
    monkeypatch.setattr(gate, "render_pngs", lambda typ, tmp: [])
    ok, msgs, _ = gate.run_gate("cv.typ", academic_gate)
    assert not ok and (True, "vitae: no PNG rendered, so the last-page fill is unmeasured") in msgs


def test_academic_gate_passes_with_a_png(academic_gate, monkeypatch):
    monkeypatch.setattr(gate, "render_pngs", lambda typ, tmp: ["p1.png"])
    monkeypatch.setattr(gate.measure_fill, "measure", lambda path: "fill to 80%")
    ok, _, reported = gate.run_gate("cv.typ", academic_gate)
    assert ok and reported[-1] == "last-page fill: fill to 80%"

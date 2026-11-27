"""The tuner's par reader/writer and the gate's leading reader (_read_par, _write_par, _doc_leading)."""
import pytest
from vitae.core.base import LEADING_WARN
from vitae.verify import tune as T
from vitae.verify.typst import _doc_leading, _read_par, _write_par

pytestmark = pytest.mark.usefixtures("tuner_original_compiles")

PAR = '#set page(paper: "us-letter")\n#set par(justify: false, leading: 0.555em, spacing: 0.615em)\nbody 0.999em\n'


def test_write_then_read_round_trips_and_stops_at_the_declaration():
    out = _write_par(PAR, 0.61, 0.7)
    assert "leading: 0.610em, spacing: 0.700em" in out and "body 0.999em" in out
    assert _read_par(PAR) == (0.555, 0.615) and _read_par(out) == (0.61, 0.7)


@pytest.mark.parametrize("src", [
    "#set text(size: 10.5pt)\n",                       # no declaration: reported, never guessed
    "#set par(spacing: 0.7em, leading: 0.6em)\n",      # not the template's order: would write the two swapped
])
def test_a_declaration_the_tuner_cannot_rewrite_is_not_read(src):
    assert _read_par(src) is None and _write_par(src, 0.9, 1.0) == src


@pytest.mark.parametrize("src, want", [
    ("#set par(leading: 1.2em)\n", 1.2),
    ("#set par(spacing: 0.7em, leading: 1.3em)\n", 1.3),                              # any argument order
    ("#set par(leading: 0.6em, spacing: 8pt)\n", 0.6),
    ("#set par(leading: 14pt)\n", 14 / 11),                                          # pt over the 11pt default
    ("#set text(size: 10pt)\n#set par(leading: 14pt, justify: true)\n", 1.4),         # pt over the declared size
    ("#set par(leading: 0.6em)\n#set par(leading: 1.2em)\n", 1.2),                    # last one wins
    ("#let h(b) = {\n  #set par(leading: 1.5em)\n  b\n}\n#set par(leading: 0.6em)\n", 0.6),   # scoped: ignored
    ("#let h(b) = [\n#set par(leading: 1.5em)\n b]\n", None),
    ("#show heading: it => [\n#set par(leading: 1.5em)\n#it]\n#set par(leading: 0.6em)\n", 0.6),
    ("#set par(leading: 0.6em)\nBody\n#set par(leading: 1.5em)\n", 0.6),               # after the body: ignored

    ("// #set par(leading: 1.5em)\n#set text(size: 10pt)\n", None),                   # commented out
])
def test_doc_leading_is_the_last_top_level_rule_before_the_body(src, want):
    assert _doc_leading(src) == pytest.approx(want) if want is not None else _doc_leading(src) is None


@pytest.mark.parametrize("under, rng", [(True, (0.40, 1.60)), (False, ())])
def test_under_filled_document_fails_with_content_advice(tmp_path, monkeypatch, capsys, under, rng):
    """Under-filled even at the leading cap: FAIL with content advice, search clamped (never padded). A page that
    overflows at every leading keeps the old advice."""
    monkeypatch.setattr(T, "preflight", lambda: (True, True, "pypdf"))
    monkeypatch.setattr(T, "_probe_text", lambda typ, cand, exp, cli, be:
                        (True, 40 + int(20 * (_doc_leading(cand) or 0))) if under else (False, None))
    p = tmp_path / "cv.typ"
    p.write_text("#set par(leading: 0.6em, spacing: 0.7em)\nbody\n", encoding="utf-8")
    rc, footer = T.tune(str(p), 1, 94, 96, *rng)
    out = capsys.readouterr().out
    assert rc == 1 and ("UNDER-FILLED" in out) == under
    if under:
        assert "never invent" in out and f"clamped to {LEADING_WARN:.3f}em" in out
        assert footer is not None and "under-filled" in footer and _read_par(p.read_text()) == (0.6, 0.7)


def test_probe_landing_in_the_window_is_kept_under_the_leading_cap(tmp_path, monkeypatch, capsys):
    """Fill grows with leading: the tuner keeps the largest leading whose fill stays within the window, never above the cap."""
    monkeypatch.setattr(T, "preflight", lambda: (True, True, "pypdf"))
    monkeypatch.setattr(T, "_probe_text", lambda typ, cand, exp, cli, be: (True, int(80 + 20 * (_doc_leading(cand) or 0))))
    p = tmp_path / "cv.typ"
    p.write_text("#set par(leading: 0.6em, spacing: 0.7em)\nbody\n", encoding="utf-8")
    rc, _ = T.tune(str(p), 1, 88, 96, 0.40, 1.60)
    leading, _ = _read_par(p.read_text()) or (None, None)
    assert rc == 0 and leading is not None and 0.6 < leading <= LEADING_WARN + 1e-9, (capsys.readouterr().out, leading)

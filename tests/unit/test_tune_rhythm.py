"""--tune with a `#let rhythm` line (phase 1: scale every gap together, leading fixed; phase 2: leading at the
rhythm bound), without one (old path), and with two `#set par` rules (the tuned line is the gate's, the last).
The compile/measure probe and preflight are injected; the fake page is `50 * rhythm + 50 * leading` tall."""
from pathlib import Path

import pytest
from vitae.core.env import PdfCheck
from vitae.verify import tune as T
from vitae.verify.typst import (
    doc_par_list,
    read_par,
    read_rhythm,
    write_par,
)


def _doc_leading(text):
    """The gate's leading reader: the first of `doc_par_list`."""
    return doc_par_list(text)[0]


pytestmark = pytest.mark.usefixtures("tuner_original_compiles")

RHYTHM_FILE = ("#let rhythm = 1.000\n"
               "#set par(leading: 0.800em, spacing: 0.900em)\n"
               "#set list(spacing: 0.500em)\nbody\n")
OLD_FILE = ("#set par(leading: 0.800em, spacing: 0.900em)\n"
            "#set list(spacing: 0.500em)\nbody\n")
TWO_PAR = ("#set par(justify: false, leading: 0.527em, spacing: 0.607em)\n"
           "#set list(spacing: 0.400em)\n"
           "// page 2\n"
           "#set par(justify: false, leading: 0.700em, spacing: 0.800em)\n"
           "#set list(spacing: 0.600em)\nbody\n")


def write(tmp_path, text):
    p = tmp_path / "cv.typ"
    p.write_text(text, encoding="utf-8")
    return p


def install(monkeypatch, *, breakat=1000.0, weights=(50, 50), log=None, preflight=None):
    """Pages hold iff the fake height <= breakat; fill = round(height). Height reads the gate's own
    leading (_doc_leading) and the rhythm line, from the candidate text the tuner writes."""
    check = preflight or PdfCheck(True, "pypdf")
    monkeypatch.setattr(T, "preflight", lambda: check)

    def probe(typ, candidate, expected, backend):
        Path(typ).write_text(candidate, encoding="utf-8")
        r = read_rhythm(candidate) or 1.0
        lead = _doc_leading(candidate)
        assert lead is not None
        if log is not None:
            log.append(candidate)
        h = weights[0] * r + weights[1] * lead
        return (True, round(h)) if h <= breakat else (False, None)
    monkeypatch.setattr(T, "_probe_text", probe)


def state(path):
    text = path.read_text(encoding="utf-8")
    par = read_par(text)
    assert par is not None
    return read_rhythm(text), par, doc_par_list(text)[1]


class TestRhythmPhase:
    def test_lands_in_window_without_touching_leading(self, tmp_path, monkeypatch):
        p = write(tmp_path, RHYTHM_FILE)
        install(monkeypatch)                                   # fill(r=1) = 90
        code, _ = T.tune(str(p), T.FillTarget(1, 94, 96))
        r, (lead, spacing), lsp = state(p)
        assert code == 0 and r is not None and 1.0 < r < 1.30
        assert lead == 0.8 and round(50 * r + 40) in (94, 95, 96)
        assert spacing == pytest.approx(0.9 * r, abs=1e-3) and lsp == pytest.approx(0.5 * r, abs=1e-3)

    def test_rhythm_hits_the_top_then_leading_takes_over(self, tmp_path, monkeypatch):
        p = write(tmp_path, RHYTHM_FILE)
        install(monkeypatch)                                   # r tops out at 1.30 -> fill 105
        code, _ = T.tune(str(p), T.FillTarget(1, 106, 108))
        r, (lead, spacing), lsp = state(p)
        assert code == 0 and r is not None and r == pytest.approx(1.30, abs=T.RHYTHM_STEP)
        assert lead > 0.8 and 106 <= round(50 * r + 50 * lead) <= 108
        # phase 2 keeps the family's delta at the tuned rhythm, and the list follows leading and rhythm
        assert spacing - lead == pytest.approx(0.9 * r - 0.8, abs=2e-3)
        # this list sits tighter than the leading (gap < floor): the gap it had is kept, never made worse
        assert lsp is not None and lsp - lead == pytest.approx(0.5 * r - 0.8, abs=2e-3)

    def test_rhythm_hits_the_bottom_then_leading_comes_down(self, tmp_path, monkeypatch):
        p = write(tmp_path, RHYTHM_FILE)
        install(monkeypatch)                                   # r = RHYTHM_LO -> fill 50*RHYTHM_LO+40 = 86, still over fmax 80
        code, _ = T.tune(str(p), T.FillTarget(1, 76, 80))
        r, (lead, _), _ = state(p)
        assert code == 0 and r is not None and r == pytest.approx(T.RHYTHM_LO, abs=T.RHYTHM_STEP) and lead < 0.8
        assert 76 <= round(50 * r + 50 * lead) <= 80

    def test_spacing_cap_stops_the_rhythm(self, tmp_path, monkeypatch):
        text = RHYTHM_FILE.replace("spacing: 0.900em", "spacing: 1.100em").replace("leading: 0.800em", "leading: 0.900em")
        p = write(tmp_path, text)
        log = []
        install(monkeypatch, log=log)
        code, _ = T.tune(str(p), T.FillTarget(1, 100, 102))
        _r, (_, spacing), _ = state(p)
        assert code == 0 and spacing <= T.SPACING_CAP + 1e-3
        assert max(read_rhythm(c) or 0 for c in log) <= T.SPACING_CAP / 1.1 + 1e-9

    def test_unreachable_target_restores_every_byte_including_the_rhythm_line(self, tmp_path, monkeypatch):
        p = write(tmp_path, RHYTHM_FILE)
        install(monkeypatch, breakat=95)                       # pages break before the fill target
        code, _ = T.tune(str(p), T.FillTarget(1, 99, 100))
        assert code == 1 and p.read_text(encoding="utf-8") == RHYTHM_FILE

    def test_floor_failing_everywhere_restores(self, tmp_path, monkeypatch):
        p = write(tmp_path, RHYTHM_FILE)
        install(monkeypatch, breakat=10)
        assert T.tune(str(p), T.FillTarget(1, 90, 96))[0] == 1
        assert p.read_text(encoding="utf-8") == RHYTHM_FILE

    @pytest.mark.parametrize("when", [1, 3, 12], ids=["floor", "phase1", "phase2"])
    def test_interrupt_restores_and_propagates(self, tmp_path, monkeypatch, when):
        p = write(tmp_path, RHYTHM_FILE)
        monkeypatch.setattr(T, "preflight", lambda: PdfCheck(True, "pypdf"))
        calls = []

        def probe(typ, candidate, *a):
            calls.append(1)
            Path(typ).write_text(candidate, encoding="utf-8")
            if len(calls) == when:
                raise KeyboardInterrupt
            return True, 50                                    # under-filled everywhere: runs through both phases
        monkeypatch.setattr(T, "_probe_text", probe)
        with pytest.raises(KeyboardInterrupt):
            T.tune(str(p), T.FillTarget(1, 94, 96))
        assert p.read_text(encoding="utf-8") == RHYTHM_FILE

    def test_footer_line_reports_the_rhythm(self, tmp_path, monkeypatch, capsys):
        p = write(tmp_path, RHYTHM_FILE)
        install(monkeypatch)
        T.tune(str(p), T.FillTarget(1, 106, 108))
        ok_line = next(ln for ln in capsys.readouterr().out.splitlines() if ln.startswith("OK"))
        assert "rhythm %.3f" % (state(p)[0] or 0) in ok_line


    def test_spacing_cap_is_relative_to_the_spacing_at_rhythm_one(self, tmp_path, monkeypatch):
        text = RHYTHM_FILE.replace("rhythm = 1.000", "rhythm = 1.100").replace("spacing: 0.900em", "spacing: 1.100em")
        p = write(tmp_path, text)
        log = []
        install(monkeypatch, log=log)
        T.tune(str(p), T.FillTarget(1, 900, 1000))                           # unreachable: only the probes matter
        top = max(read_rhythm(c) or 0 for c in log)
        assert T.SPACING_CAP - 0.01 <= top <= T.SPACING_CAP + 1e-9   # unit spacing is 1.0em, so r stops at 1.24


class TestNoRhythmLine:
    def test_old_path_never_touches_a_rhythm_phase(self, tmp_path, monkeypatch, capsys):
        p = write(tmp_path, OLD_FILE)
        log = []
        install(monkeypatch, log=log)
        code, _ = T.tune(str(p), T.FillTarget(1, 94, 96))
        out = p.read_text(encoding="utf-8")
        assert code == 0 and "rhythm" not in out and "rhythm" not in capsys.readouterr().out
        assert all("rhythm" not in c for c in log)
        lead, spacing = read_par(out) or (0, 0)
        assert lead > 0.8 and spacing - lead == pytest.approx(0.1, abs=2e-3)
        assert doc_par_list(out)[1] == pytest.approx(lead - 0.3, abs=2e-3)   # under-floor gap kept, not widened or narrowed

    def test_a_rhythm_line_inside_a_block_comment_does_not_count(self, tmp_path, monkeypatch):
        text = "/*\n#let rhythm = 1.000\n*/\n" + OLD_FILE
        p = write(tmp_path, text)
        log = []
        install(monkeypatch, log=log)
        T.tune(str(p), T.FillTarget(1, 94, 96))
        assert all(c.startswith("/*\n#let rhythm = 1.000\n*/\n") for c in log)

    def test_a_commented_or_non_numeric_rhythm_line_does_not_count(self, tmp_path, monkeypatch):
        text = "// #let rhythm = 1.000\n#let rhythm = 1.0pt\n" + OLD_FILE
        p = write(tmp_path, text)
        log = []
        install(monkeypatch, log=log)
        T.tune(str(p), T.FillTarget(1, 94, 96))
        assert all(c.startswith("// #let rhythm = 1.000\n#let rhythm = 1.0pt\n") for c in log)


class TestTwoParRules:
    def test_write_targets_the_line_the_gate_reads(self):
        out = write_par(TWO_PAR, 0.75, 0.85)
        assert _doc_leading(out) == 0.75 and read_par(out) == (0.75, 0.85)
        assert "leading: 0.527em, spacing: 0.607em" in out        # page 1's declaration untouched

    def test_read_returns_the_last_rule(self):
        assert read_par(TWO_PAR) == (0.7, 0.8)

    def test_a_last_rule_the_tuner_cannot_rewrite_is_refused_not_misdirected(self):
        text = TWO_PAR + "#set par(leading: 14pt)\n"
        assert read_par(text) is None and write_par(text, 0.9, 1.0) == text

    def test_tuned_value_lands_on_the_measured_line(self, tmp_path, monkeypatch):
        p = write(tmp_path, TWO_PAR)
        install(monkeypatch, weights=(0, 100))                 # height = 100 * the gate's leading
        code, _ = T.tune(str(p), T.FillTarget(1, 74, 78))
        out = p.read_text(encoding="utf-8")
        assert code == 0 and 74 <= round(100 * (_doc_leading(out) or 0)) <= 78
        assert out.startswith("#set par(justify: false, leading: 0.527em, spacing: 0.607em)\n#set list(spacing: 0.400em)\n")

    def test_only_the_list_after_the_tuned_rule_is_scaled(self, tmp_path, monkeypatch):
        p = write(tmp_path, TWO_PAR)
        install(monkeypatch, weights=(0, 100))
        T.tune(str(p), T.FillTarget(1, 74, 78))
        out = p.read_text(encoding="utf-8")
        lead = _doc_leading(out) or 0
        assert "#set list(spacing: 0.400em)" in out
        assert doc_par_list(out)[1] == pytest.approx(lead - 0.1, abs=2e-3)   # under-floor gap kept

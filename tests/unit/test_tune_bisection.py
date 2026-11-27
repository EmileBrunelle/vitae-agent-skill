"""vitae.verify.tune.tune: bisection bounds, caps, restoration. The compile/measure probe and preflight are injected."""
from pathlib import Path

import pytest
from vitae.core.base import LEADING_WARN
from vitae.core.env import PdfCheck
from vitae.verify import tune as T

pytestmark = pytest.mark.usefixtures("tuner_original_compiles")

PAR = "#set par(leading: 0.80em, spacing: 0.90em)\nbody\n"   # delta = 0.10em


@pytest.fixture
def typ(tmp_path):
    p = tmp_path / "cv.typ"
    p.write_text(PAR, encoding="utf-8")
    return p


def install(monkeypatch, *, lstar, fill_of=lambda l: round(l * 100), preflight=None, log=None):
    """Pages hold iff leading <= lstar; fill grows with leading."""
    check = preflight or PdfCheck(True, "pypdf")
    monkeypatch.setattr(T, "preflight", lambda: check)

    def probe(typ_path, text, leading, spacing, expected, backend):
        if log is not None:
            log.append(leading)
        Path(typ_path).write_text("PROBE-JUNK", encoding="utf-8")   # like the real probe: rewrites in place
        return (True, fill_of(leading)) if leading <= lstar else (False, None)
    monkeypatch.setattr(T, "_probe", probe)


def written_leading(path):
    from vitae.verify.typst import _read_par
    par = _read_par(path.read_text(encoding="utf-8"))
    assert par is not None
    return par[0]


class TestSuccess:
    def test_lands_just_below_the_page_break(self, typ, monkeypatch):
        install(monkeypatch, lstar=0.93)
        code, _ = T.tune(str(typ), T.FillTarget(1, 80, 99))
        lead = written_leading(typ)
        assert code == 0 and 0.93 - 0.005 - 1e-9 <= lead <= 0.93 + 1e-9

    def test_spacing_keeps_the_familys_delta(self, typ, monkeypatch):
        from vitae.verify.typst import _read_par
        install(monkeypatch, lstar=0.93)
        T.tune(str(typ), T.FillTarget(1, 80, 99))
        par = _read_par(typ.read_text(encoding="utf-8"))
        assert par is not None
        lead, spacing = par
        assert spacing - lead == pytest.approx(0.10, abs=2e-3)

    def test_prefers_largest_probe_inside_target_over_overshooting_top(self, typ, monkeypatch):
        install(monkeypatch, lstar=0.99)             # the top of the interval (~99%) overshoots; probe 0.91 -> 91% is in target
        code, _ = T.tune(str(typ), T.FillTarget(1, 90, 93))
        fill = round(written_leading(typ) * 100)
        assert code == 0 and 90 <= fill <= 93

    def test_larger_feasible_interval_never_gives_a_smaller_leading(self, tmp_path, monkeypatch):
        results = []
        for lstar in (0.86, 0.90, 0.95):
            p = tmp_path / f"{lstar}.typ"
            p.write_text(PAR, encoding="utf-8")
            install(monkeypatch, lstar=lstar)
            assert T.tune(str(p), T.FillTarget(1, 0, 200))[0] == 0
            results.append(written_leading(p))
        assert results == sorted(results)


class TestFillTargetEdges:
    """The target band is inclusive at both ends."""

    @pytest.mark.parametrize("fill", [90, 96], ids=["exactly-fmin", "exactly-fmax"])
    def test_fill_on_the_band_edge_wins(self, typ, monkeypatch, fill):
        install(monkeypatch, lstar=0.93, fill_of=lambda l: fill)
        assert T.tune(str(typ), T.FillTarget(1, 90, 96))[0] == 0

    @pytest.mark.parametrize("fill", [89, 97], ids=["one-under", "one-over"])
    def test_fill_just_outside_the_band_loses(self, typ, monkeypatch, fill):
        install(monkeypatch, lstar=0.93, fill_of=lambda l: fill)
        assert T.tune(str(typ), T.FillTarget(1, 90, 96))[0] == 1

    def test_range_already_within_one_step_is_not_bisected(self, typ, monkeypatch):
        log = []
        install(monkeypatch, lstar=9.0, log=log)
        T.tune(str(typ), T.FillTarget(1, 0, 500), T.LeadingBounds(lo=0.50, hi=0.75, step=0.25))
        assert log == [0.50]   # only the floor probe


class TestBounds:
    def test_never_exceeds_the_double_spacing_cap_whatever_range_is_passed(self, typ, monkeypatch):
        install(monkeypatch, lstar=9.0)
        code, _ = T.tune(str(typ), T.FillTarget(1, 0, 500), T.LeadingBounds(lo=0.5, hi=3.0))
        assert code == 0 and written_leading(typ) <= LEADING_WARN + 1e-9

    def test_probes_stay_inside_the_requested_range(self, typ, monkeypatch):
        log = []
        install(monkeypatch, lstar=9.0, log=log)
        T.tune(str(typ), T.FillTarget(1, 0, 500), T.LeadingBounds(lo=0.70, hi=0.90))
        assert min(log) >= 0.70 - 1e-9 and max(log) <= 0.90 + 1e-9

    def test_family_already_above_the_cap_is_not_forced_down(self, tmp_path, monkeypatch):
        p = tmp_path / "hi.typ"
        p.write_text("#set par(leading: 1.10em, spacing: 1.20em)\n", encoding="utf-8")
        log = []
        install(monkeypatch, lstar=9.0, log=log)
        T.tune(str(p), T.FillTarget(1, 0, 500))
        assert min(log) >= 1.10 * 0.80 - 1e-9 and max(log) <= 1.10 + 1e-9
        assert max(log) > 1.05   # the search really reaches up to the family's own leading

    def test_bisection_stops_within_step(self, typ, monkeypatch):
        log = []
        install(monkeypatch, lstar=0.93, log=log)
        T.tune(str(typ), T.FillTarget(1, 80, 99), T.LeadingBounds(step=0.02))
        assert len(log) <= 7


class TestFailures:
    def test_missing_par_line_exits_2_without_touching_file(self, tmp_path, monkeypatch):
        p = tmp_path / "x.typ"
        p.write_text("no rhythm here\n", encoding="utf-8")
        install(monkeypatch, lstar=1.0)
        code, footer = T.tune(str(p), T.FillTarget(1, 80, 99))
        assert code == 2 and footer and p.read_text(encoding="utf-8") == "no rhythm here\n"

    def test_failed_preflight_exits_1_with_no_footer(self, typ, monkeypatch):
        install(monkeypatch, lstar=1.0, preflight=PdfCheck(False, None))
        assert T.tune(str(typ), T.FillTarget(1, 80, 99)) == (1, None)
        assert typ.read_text(encoding="utf-8") == PAR

    def test_content_too_long_even_at_the_floor_restores_file(self, typ, monkeypatch):
        install(monkeypatch, lstar=0.10)
        code, _ = T.tune(str(typ), T.FillTarget(1, 80, 99))
        assert code == 1 and typ.read_text(encoding="utf-8") == PAR

    def test_under_filled_page_is_refused_with_the_underfill_footer(self, typ, monkeypatch):
        install(monkeypatch, lstar=0.95, fill_of=lambda l: 60)
        code, footer = T.tune(str(typ), T.FillTarget(1, 90, 96))
        assert (code, footer) == (1, T._FOOTER_TUNE_UNDER)
        assert typ.read_text(encoding="utf-8") == PAR

    def test_unreachable_target_restores_original_rhythm(self, typ, monkeypatch):
        install(monkeypatch, lstar=0.95, fill_of=lambda l: 99)   # overshoots fmax everywhere
        code, footer = T.tune(str(typ), T.FillTarget(1, 80, 90))
        assert code == 1 and footer != T._FOOTER_TUNE_UNDER and typ.read_text(encoding="utf-8") == PAR

    def test_interrupt_mid_probe_restores_file_and_propagates(self, typ, monkeypatch):
        monkeypatch.setattr(T, "preflight", lambda: PdfCheck(True, "pypdf"))
        calls = []

        def probe(typ_path, *a):
            calls.append(1)
            Path(typ_path).write_text("JUNK", encoding="utf-8")
            if len(calls) == 2:
                raise KeyboardInterrupt
            return True, 90
        monkeypatch.setattr(T, "_probe", probe)
        with pytest.raises(KeyboardInterrupt):
            T.tune(str(typ), T.FillTarget(1, 80, 99))
        assert typ.read_text(encoding="utf-8") == PAR


class TestNarrowWindowIsNotSkipped:
    """Real parameters: default range [0.8*l0, max(1.3*l0, 1.10)] capped at LEADING_WARN (1.00em),
    step 0.005em, family bands 94-96 % or 92-94 % (2 % wide). 0.005em moves a 1-page fill by
    <0.5 %, so the band spans >= ~0.02em of leading, i.e. a few steps. With a realistic monotone
    fill (slope 60-100 %/em) whose page-break value L* overshoots fmax by 3-5 %, the old
    "bisect for the page break, then keep the largest in-band probe" visited only ~8 points on
    its way up to L* and could jump over the band (518 of 1066 swept cases failed). Bisecting on
    "pages hold and fill <= fmax" must find it whenever the band is above the floor."""

    @pytest.mark.parametrize("l0", [0.65, 0.85, 0.96])
    @pytest.mark.parametrize("slope", [60, 100])
    @pytest.mark.parametrize("band", [(94, 96), (92, 94)])
    @pytest.mark.parametrize("over", [3, 5])
    def test_band_below_an_overshooting_page_break_is_found(self, tmp_path, monkeypatch, l0, slope, band, over):
        fmin, fmax = band
        failures = []
        for i in range(60):
            lstar = 0.70 + 0.005 * i
            off = fmax + over - slope * lstar          # fill(L*) = fmax + over
            if lstar - (fmax + over - fmin) / slope < l0 * 0.80 + 0.01:
                continue                                # band under the search floor: not this test
            p = tmp_path / f"{i}.typ"
            p.write_text(f"#set par(leading: {l0}em, spacing: {l0 + 0.1}em)\n", encoding="utf-8")
            install(monkeypatch, lstar=lstar, fill_of=lambda l, off=off: round(off + slope * l))
            code, _ = T.tune(str(p), T.FillTarget(1, fmin, fmax))
            fill = round(off + slope * written_leading(p)) if code == 0 else None
            if code != 0 or not fmin <= fill <= fmax:
                failures.append(round(lstar, 3))
        assert not failures

    def test_85_to_90_window_below_the_page_break(self, typ, monkeypatch):
        install(monkeypatch, lstar=0.99, fill_of=lambda l: round(100 * l * 0.92))   # fill(L*) = 91
        code, _ = T.tune(str(typ), T.FillTarget(1, 85, 88))
        assert code == 0 and 85 <= round(100 * written_leading(typ) * 0.92) <= 88


class TestUnmeasuredFill:
    def test_unmeasured_probe_does_not_erase_a_measured_best(self, typ, monkeypatch):
        """Fill unreadable (None) from 0.92 up while pages still hold; every probe above 0.93 breaks the page."""
        install(monkeypatch, lstar=0.93, fill_of=lambda l: None if l >= 0.92 else round(l * 100))
        code, _ = T.tune(str(typ), T.FillTarget(1, 80, 99))
        assert code == 0 and 0.80 < written_leading(typ) < 0.92


class TestClampMessage:
    """The NOTE names the cap actually applied and the constants it comes from, not a number frozen in the text."""

    def _note(self, tmp_path, monkeypatch, capsys, par):
        p = tmp_path / "c.typ"
        p.write_text(f"#set par({par})\nbody\n", encoding="utf-8")
        install(monkeypatch, lstar=9.0)
        T.tune(str(p), T.FillTarget(1, 80, 99))
        return next(ln for ln in capsys.readouterr().out.splitlines() if ln.startswith("NOTE  upper bound clamped"))

    def test_gate_threshold_is_the_cap(self, tmp_path, monkeypatch, capsys):
        note = self._note(tmp_path, monkeypatch, capsys, "leading: 0.90em, spacing: 1.00em")
        assert f"clamped to {LEADING_WARN:.3f}em" in note and f"({LEADING_WARN:.2f}em)" in note
        assert "0.96" not in note

    def test_spacing_cap_is_the_cap_when_tighter(self, tmp_path, monkeypatch, capsys):
        note = self._note(tmp_path, monkeypatch, capsys, "leading: 0.70em, spacing: 1.20em")   # delta 0.50 -> 1.24 - 0.50
        assert f"clamped to {T.SPACING_CAP - 0.50:.3f}em" in note and f"({T.SPACING_CAP:.2f}em)" in note and "+0.500em" in note
        assert "0.96" not in note

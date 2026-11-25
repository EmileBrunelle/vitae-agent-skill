"""check_whitespace: canyon / hole / device-quorum / separation decisions, with the raster scans injected."""

import vitae.fill as measure_fill
from vitae.verify import layout


def run_gate(monkeypatch, runs, h=1000, ink=(), furniture=(), **kw):
    """White runs are laid out 100px apart; `ink` are (top, bottom) bands."""
    white, y = [], 50
    for r in runs:
        white.append((y, y + r))
        y += r + 100
    monkeypatch.setattr(measure_fill, "bands", lambda path: (h, white, list(ink)))
    monkeypatch.setattr(layout, "furniture_ink", lambda path, boxes: list(furniture))
    return list(layout.check_whitespace("page.png", **kw))


def fails(results):
    return [m for f, m in results if f]


def inside(runs, idx):
    """A 2px ink band wholly inside run `idx` (as laid out by run_gate)."""
    y = 50
    for i, r in enumerate(runs):
        if i == idx:
            return (y + 1, y + 3)
        y += r + 100


class TestPreconditions:
    def test_fewer_than_six_runs_is_not_a_text_page(self, monkeypatch):
        assert run_gate(monkeypatch, [10] * 5) == []

    def test_zero_median_is_skipped(self, monkeypatch):
        assert run_gate(monkeypatch, [0, 0, 0, 0, 0, 0, 5]) == []


class TestCanyon:
    """A white run taller than 5% of page height is a canyon, even at a section boundary."""

    def test_run_exactly_at_ceiling_is_not_a_canyon(self, monkeypatch):
        r = run_gate(monkeypatch, [10] * 5 + [50])  # 5% of 1000
        assert not [m for m in fails(r) if m.startswith("canyon")]

    def test_run_one_pixel_over_ceiling_is_a_canyon(self, monkeypatch):
        r = run_gate(monkeypatch, [10] * 5 + [51])
        assert [m for m in fails(r) if m.startswith("canyon")]


class TestHole:
    """A run over 3.5% of page height is a hole unless it is a boundary (>= 2x the median run)."""
    MED = [30] * 5   # median 30 -> boundary exemption starts at 60

    def test_run_exactly_at_hole_limit_is_fine(self, monkeypatch):
        assert not [m for m in fails(run_gate(monkeypatch, self.MED + [35])) if m.startswith("hole")]

    def test_run_just_over_hole_limit_inside_a_section_is_a_hole(self, monkeypatch):
        assert [m for m in fails(run_gate(monkeypatch, self.MED + [36])) if m.startswith("hole")]

    def test_run_at_twice_median_is_a_boundary_not_a_hole(self, monkeypatch):
        r = fails(run_gate(monkeypatch, [30] * 5 + [60]))
        assert not [m for m in r if m.startswith("hole")]

    def test_run_exactly_twice_median_above_hole_limit_is_a_boundary(self, monkeypatch):
        # h=2000: hole limit 70px, ceiling 100px; median 40 -> a 80px run is exactly 2x
        r = fails(run_gate(monkeypatch, [40] * 5 + [80], h=2000))
        assert not [m for m in r if m.startswith(("hole", "canyon"))]

    def test_run_just_under_twice_median_is_still_a_hole(self, monkeypatch):
        r = fails(run_gate(monkeypatch, [30] * 5 + [49]))
        assert [m for m in r if m.startswith("hole")]


class TestDeviceQuorum:
    """A boundary system needs DEVICE_QUORUM (2) ink bands AT section boundaries."""
    RUNS = [10, 10, 10, 10, 30, 30]   # two boundary-sized runs, median 10

    def msgs(self, results):
        return [m for _, m in results if m.startswith("boundar")]

    def test_two_devices_meet_the_quorum(self, monkeypatch):
        ink = [inside(self.RUNS, 4), inside(self.RUNS, 5)]
        r = run_gate(monkeypatch, self.RUNS, ink=ink)
        assert fails(r) == [] and "boundary devices: 2" in self.msgs(r)[0]

    def test_one_device_is_only_an_ornament_and_fails(self, monkeypatch):
        r = run_gate(monkeypatch, self.RUNS, ink=[inside(self.RUNS, 4)])
        assert any("boundaries carry no ink: 1" in m for m in fails(r))

    def test_no_device_fails(self, monkeypatch):
        r = run_gate(monkeypatch, self.RUNS)
        assert any("boundaries carry no ink: 0" in m for m in fails(r))

    def test_deviceless_family_is_exempt_from_the_fail(self, monkeypatch):
        r = run_gate(monkeypatch, self.RUNS, family="humanist-quiet")
        assert fails(r) == []
        assert any("EXEMPT" in m for _, m in r)

    def test_missing_pdftotext_reports_but_never_fails(self, monkeypatch):
        r = run_gate(monkeypatch, self.RUNS, degraded=True)
        assert fails(r) == []
        assert any("NOT MEASURED" in m for _, m in r)

    def test_furniture_near_a_boundary_counts_toward_quorum(self, monkeypatch):
        # furniture is reported in full-page rows; the gate shifts it by 2% of height (20px)
        runs = self.RUNS
        furn = [(a + 20, b + 20) for a, b in (inside(runs, 4), inside(runs, 5))]
        # make them NOT ink bands, only furniture
        r = run_gate(monkeypatch, runs, furniture=furn)
        assert fails(r) == []

    def test_furniture_duplicating_an_ink_band_is_counted_once(self, monkeypatch):
        band = inside(self.RUNS, 4)
        assert band is not None
        ink = [band]
        furn = [(band[0] + 20, band[1] + 20)]
        r = run_gate(monkeypatch, self.RUNS, ink=ink, furniture=furn)
        assert any("boundaries carry no ink: 1" in m for m in fails(r))


class TestSeparationRatio:
    """biggest-gap / median: over SEPARATION_CEILING (6.0) is flagged; under BOUNDARY_RATIO (2.0) is reported."""

    def sep(self, results):
        return [m for _, m in results if m.startswith("section separation")]

    def test_ratio_exactly_at_ceiling_is_not_over(self, monkeypatch):
        r = run_gate(monkeypatch, [10] * 5 + [60], h=10000)
        assert not any("OVER" in m for m in self.sep(r))

    def test_ratio_just_over_ceiling_is_flagged(self, monkeypatch):
        r = run_gate(monkeypatch, [10] * 5 + [61], h=10000)
        assert any("OVER" in m for m in self.sep(r))

    def test_ratio_below_boundary_ratio_is_reported_not_failed(self, monkeypatch):
        r = run_gate(monkeypatch, [10] * 5 + [19], h=10000)
        assert any("REPORTED, NOT FAILED" in m for m in self.sep(r))
        assert fails(r) == [m for m in fails(r) if "boundaries carry no ink" in m]

    def test_ratio_exactly_at_boundary_ratio_is_not_reported_as_low(self, monkeypatch):
        r = run_gate(monkeypatch, [10] * 5 + [20], h=10000)
        assert not any("REPORTED, NOT FAILED" in m for m in self.sep(r))

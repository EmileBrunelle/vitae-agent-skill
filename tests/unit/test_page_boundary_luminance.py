"""Luminance (vitae.core.colour) and pure helpers of vitae.verify.page: section-boundary location."""
import pytest
from vitae.core import colour
from vitae.verify import page


class TestPageLuminance:
    @pytest.mark.parametrize("rgb, expected", [
        ((0, 0, 0), 0.0), ((255, 255, 255), 1.0),
        ((255, 0, 0), 0.2126), ((0, 255, 0), 0.7152), ((0, 0, 255), 0.0722),
    ], ids=["black", "white", "red", "green", "blue"])
    def test_anchors(self, rgb, expected):
        assert colour.rel_luminance(rgb) == pytest.approx(expected, abs=1e-4)

    def test_channel_table_is_monotonic_and_covers_all_levels(self):
        assert len(colour._LIN) == 256
        assert all(a < b for a, b in zip(colour._LIN, colour._LIN[1:]))

    def test_agrees_with_palette_luminance_within_rounding(self):
        # the palette picker uses the one shared implementation
        from vitae.palette import _lum
        for rgb in [(10, 200, 30), (128, 128, 128), (250, 5, 90)]:
            assert colour.rel_luminance(rgb) == _lum(rgb)


class TestBoundaryInk:
    """An ink band is a boundary device when white above + band + white below spans >= BOUNDARY_RATIO x median gap."""

    def test_span_exactly_at_ratio_counts(self):
        # white 40..50 sits above the band 50..52: span = 10 + 2 = 12 = 2.0 x 6
        assert page.boundary_ink([(40, 50)], [(50, 52)], med=6.0) == [(50, 52)]

    def test_span_just_below_ratio_is_not_a_boundary(self):
        assert page.boundary_ink([(40, 50)], [(50, 52)], med=6.5) == []

    def test_band_inside_a_tall_white_run_counts(self):
        assert page.boundary_ink([(100, 130)], [(110, 112)], med=10.0) == [(110, 112)]

    def test_band_with_no_white_around_is_just_its_own_thickness(self):
        assert page.boundary_ink([(300, 330)], [(10, 12)], med=10.0) == []

    def test_no_bands_gives_empty(self):
        assert page.boundary_ink([(0, 50)], [], med=5.0) == []


class TestNearBoundary:
    """Furniture on a heading's own line counts when within one median gap of a white run >= BOUNDARY_ADJACENT x median."""
    WHITE = [(100, 130)]   # 30px run, med 10 -> needs >= 12

    @pytest.mark.parametrize("band, expected", [
        ((140, 145), True),    # exactly one median gap below the run
        ((141, 145), False),   # one pixel further
        ((85, 90), True),      # exactly one median gap above the run
        ((84, 89), False),     # one pixel further
        ((110, 112), True),    # inside the run
    ], ids=["below-at-limit", "below-past", "above-at-limit", "above-past", "inside"])
    def test_proximity(self, band, expected):
        assert page.near_boundary(band, self.WHITE, med=10.0) is expected

    @pytest.mark.parametrize("run_len, expected", [(12, True), (11, False)], ids=["run-at-1.2x", "run-below-1.2x"])
    def test_run_height_threshold(self, run_len, expected):
        assert page.near_boundary((100, 102), [(100, 100 + run_len)], med=10.0) is expected

    def test_no_white_runs_means_no_boundary(self):
        assert page.near_boundary((100, 102), [], med=10.0) is False

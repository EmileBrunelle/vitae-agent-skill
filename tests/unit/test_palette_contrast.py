"""WCAG contrast maths and palette guarantees of vitae.palette (pure, deterministic)."""
import pytest
from vitae import palette as P
from vitae.palette import contrast

BLACK, WHITE = (0, 0, 0), (255, 255, 255)


class TestRelativeLuminance:
    @pytest.mark.parametrize("rgb, expected", [
        (BLACK, 0.0), (WHITE, 1.0),
        ((255, 0, 0), 0.2126), ((0, 255, 0), 0.7152), ((0, 0, 255), 0.0722),
    ], ids=["black", "white", "red-weight", "green-weight", "blue-weight"])
    def test_anchors(self, rgb, expected):
        assert P._lum(rgb) == pytest.approx(expected, abs=1e-4)

    def test_mid_gray_follows_srgb_gamma_not_linear_half(self):
        assert P._lum((128, 128, 128)) == pytest.approx(0.2159, abs=1e-3)

    def test_low_channel_uses_linear_segment(self):
        # 10/255 is below the sRGB knee: v / 12.92
        assert P._lum((10, 10, 10)) == pytest.approx(10 / 255 / 12.92, rel=1e-6)

    def test_darker_colour_has_lower_luminance(self):
        assert P._lum((100, 100, 100)) < P._lum((101, 100, 100))


class TestContrastRatio:
    def test_black_on_white_is_21_to_1(self):
        assert contrast(BLACK, WHITE) == pytest.approx(21.0, abs=1e-6)

    def test_same_colour_is_1_to_1(self):
        assert contrast((12, 34, 56), (12, 34, 56)) == pytest.approx(1.0)

    @pytest.mark.parametrize("a, b", [
        (BLACK, WHITE), ((0, 0, 200), (250, 250, 0)), ((119, 119, 119), WHITE),
    ], ids=["bw", "blue-yellow", "gray-white"])
    def test_is_symmetric(self, a, b):
        assert contrast(a, b) == contrast(b, a)

    def test_never_below_one(self):
        assert contrast((50, 60, 70), (51, 60, 70)) >= 1.0

    def test_known_gray_767676_on_white_just_passes_aa(self):
        # #767676 is the lightest gray that reaches 4.5:1 on white
        assert contrast((0x76, 0x76, 0x76), WHITE) == pytest.approx(4.54, abs=0.01)
        assert contrast((0x77, 0x77, 0x77), WHITE) < 4.5


class TestHexAndMix:
    @pytest.mark.parametrize("rgb, expected", [
        (BLACK, "#000000"), (WHITE, "#ffffff"), ((1, 2, 255), "#0102ff"),
    ], ids=["black", "white", "zero-padded"])
    def test_hex_is_lowercase_zero_padded(self, rgb, expected):
        assert P._hex(rgb) == expected

    def test_mix_weight_one_returns_first(self):
        assert P._mix((10, 20, 30), WHITE, 1.0) == (10, 20, 30)

    def test_mix_weight_zero_returns_second(self):
        assert P._mix((10, 20, 30), WHITE, 0.0) == WHITE

    def test_mix_half_is_midpoint(self):
        assert P._mix(BLACK, WHITE, 0.5) == (128, 128, 128)


class TestHueGeometry:
    @pytest.mark.parametrize("a, b, expected", [
        (10, 10, 0), (0, 180, 180), (350, 10, 20), (10, 350, 20), (0, 359, 1),
    ], ids=["equal", "opposite", "wraps-forward", "wraps-back", "adjacent-wrap"])
    def test_separation_is_shortest_arc(self, a, b, expected):
        assert P._hue_sep(a, b) == expected

    @pytest.mark.parametrize("h", [0, 9, 36, 39, 71, 200, 359])
    def test_hue_outside_veto_is_kept(self, h):
        assert P._escape_hue_veto(h, anchor=(h + 180) % 360) == h

    @pytest.mark.parametrize("h", [10, 20, 35, 40, 55, 70])
    def test_vetoed_hue_escapes_and_keeps_separation(self, h):
        anchor = 200
        out = P._escape_hue_veto(h, anchor)
        assert out is not None
        assert not any(lo <= out <= hi for lo, hi in P.HUE_B_VETO)
        assert P._hue_sep(out, anchor) >= 55

    def test_veto_is_none_when_separation_is_unreachable(self):
        assert P._escape_hue_veto(20, anchor=20, min_sep=181) is None


class TestBuild:
    @pytest.mark.parametrize("level", sorted(P.DIAL))
    @pytest.mark.parametrize("family", ["swiss-grid", "color-band", "gutter-rail"])
    def test_every_role_clears_its_threshold(self, family, level):
        p = P.build(family, "Some Seed+field", level)
        failing = {k: v for k, v in p["checks"].items() if v[0] < v[1]}
        assert failing == {}

    def test_same_inputs_give_same_palette(self):
        assert P.build("swiss-grid", "s") == P.build("swiss-grid", "s")

    def test_different_seed_gives_different_accent(self):
        assert P.build("swiss-grid", "A")["accent"] != P.build("swiss-grid", "B")["accent"]

    def test_unknown_family_exits(self):
        with pytest.raises(SystemExit):
            P.build("no-such-family", "s")

    def test_unknown_audacity_exits(self):
        with pytest.raises(SystemExit):
            P.build("swiss-grid", "s", "loud")  # type: ignore[arg-type]  # "loud" is not an Audacity on purpose: build() must exit

    @pytest.mark.parametrize("level", sorted(P.DIAL))
    def test_accent_stays_outside_muddy_yellow_zone(self, level):
        for i in range(30):
            h = P.build("swiss-grid", f"k{i}", level)["hsl"][0]
            assert not P.EXCLUDE_HUE[0] <= h <= P.EXCLUDE_HUE[1]

    def test_sober_accent_reaches_6_to_1_on_white(self):
        for i in range(30):
            assert contrast(P.build("swiss-grid", f"k{i}", "sober")["accent"], WHITE) >= 6.0

    def test_duotone_pair_separates_in_grayscale(self):
        for i in range(30):
            p = P.build("color-band", f"k{i}")
            assert p["accent2"] is not None
            assert contrast(p["accent"], p["accent2"]) >= P.DUOTONE_SEP

    def test_monochrome_family_has_no_second_hue(self):
        assert P.build("swiss-grid", "s")["accent2"] is None

    def test_typst_block_names_every_role(self):
        out = P.typst(P.build("color-band", "s"))
        assert all(k in out for k in ("#let accent ", "#let accent2", "#let soft", "#let ink", "#let dark"))

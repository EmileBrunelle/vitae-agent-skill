"""`core.pixels` thresholds and `core.colour.contrast_from_lum`: behaviour at the boundary value and the difference
between the luma and the per-channel reading of "far from the background"."""
from __future__ import annotations

import pytest
from PIL import Image
from vitae.core.colour import contrast_from_lum, rel_luminance
from vitae.core.pixels import far_in_any_channel, far_in_luma, threshold_lut


def test_threshold_lut_boundary_both_directions() -> None:
    below, at_or_above = threshold_lut(100), threshold_lut(100, below=False)

    assert (below[99], below[100]) == (255, 0)
    assert (at_or_above[99], at_or_above[100]) == (0, 255)
    assert len(below) == len(at_or_above) == 256
    assert all(a != b for a, b in zip(below, at_or_above))   # exact complements


def test_contrast_from_lum_is_symmetric_and_spans_1_to_21() -> None:
    black, white = rel_luminance((0, 0, 0)), rel_luminance((255, 255, 255))

    assert contrast_from_lum(white, black) == contrast_from_lum(black, white) == pytest.approx(21.0)
    assert contrast_from_lum(0.3, 0.3) == 1.0


def test_far_from_background_luma_and_per_channel_differ_on_a_single_channel_tint() -> None:
    # a blue-only step of 55: far on one channel (>= 40), but only ~4 luma levels (0.0722 * 55)
    im = Image.new("RGB", (2, 1), (200, 200, 200))
    im.putpixel((1, 0), (200, 200, 255))

    assert far_in_any_channel(im, (200, 200, 200), 40).getbbox() == (1, 0, 2, 1)
    assert far_in_luma(im, (200, 200, 200), 40).getbbox() is None
    assert far_in_luma(im, (200, 200, 200), 4).getbbox() == (1, 0, 2, 1)

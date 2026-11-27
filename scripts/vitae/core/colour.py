"""sRGB colour maths shared by the palette picker and the page gates."""
from __future__ import annotations

from collections.abc import Iterable, Sequence

# sRGB channel value (0-255) to linear light. Knee 0.04045 is the IEC 61966-2-1 value (WCAG 2.2 notes that
# the 0.03928 of its older text was a typo; no 8-bit channel falls between the two).
_LIN = [((c / 255) / 12.92 if c / 255 <= 0.04045 else (((c / 255) + 0.055) / 1.055) ** 2.4)
        for c in range(256)]
# The three terms of rel_luminance, one 256-entry immutable table per channel: a colour's luminance is a sum of
# three lookups. Each entry is the same float product `rel_luminance` computes, so the sum is bit-identical.
_LUM_R = tuple(0.2126 * v for v in _LIN)
_LUM_G = tuple(0.7152 * v for v in _LIN)
_LUM_B = tuple(0.0722 * v for v in _LIN)


def rel_luminance(rgb: Sequence[int]) -> float:
    """WCAG relative luminance of an 8-bit sRGB colour: 0 for black, 1 for white."""
    return 0.2126 * _LIN[rgb[0]] + 0.7152 * _LIN[rgb[1]] + 0.0722 * _LIN[rgb[2]]


def counted_luminances(counted: Iterable[tuple[int, Sequence[int]]]) -> list[float]:
    """`rel_luminance` of the colour of each (count, 8-bit RGB colour) pair, as `Image.getcolors` gives them.
    Bit-identical to calling `rel_luminance` on each (same terms, same sum order) without a Python call per colour:
    the fast path for the hundreds of colours of one image box."""
    lr, lg, lb = _LUM_R, _LUM_G, _LUM_B
    return [lr[c[0]] + lg[c[1]] + lb[c[2]] for _, c in counted]


def contrast_from_lum(la: float, lb: float) -> float:
    """WCAG contrast ratio (1..21) of two relative luminances, in either order."""
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)

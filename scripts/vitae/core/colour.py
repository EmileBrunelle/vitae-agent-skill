"""sRGB colour maths shared by the palette picker and the page gates."""
from __future__ import annotations

from collections.abc import Sequence

# sRGB channel value (0-255) to linear light. Knee 0.04045 is the IEC 61966-2-1 value (WCAG 2.2 notes that
# the 0.03928 of its older text was a typo; no 8-bit channel falls between the two).
_LIN = [((c / 255) / 12.92 if c / 255 <= 0.04045 else (((c / 255) + 0.055) / 1.055) ** 2.4)
        for c in range(256)]


def rel_luminance(rgb: Sequence[int]) -> float:
    """WCAG relative luminance of an 8-bit sRGB colour: 0 for black, 1 for white."""
    return 0.2126 * _LIN[rgb[0]] + 0.7152 * _LIN[rgb[1]] + 0.0722 * _LIN[rgb[2]]


def contrast_from_lum(la: float, lb: float) -> float:
    """WCAG contrast ratio (1..21) of two relative luminances, in either order."""
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)

"""Typed pixel access over Pillow images: `Image.load()` is typed as one object that answers `px[x, y]` with a float
or a tuple depending on the image mode, so each mode gets its own view over the image bytes here, and `colour_counts`
validates `getcolors()` at the Pillow boundary."""
from __future__ import annotations

from PIL import Image


class GrayPixels:
    """`px[x, y]` of an "L" image: its luminance, 0..255."""
    __slots__ = ("_data", "_w", "_h")

    def __init__(self, im: Image.Image) -> None:
        if im.mode != "L":
            raise ValueError(f'gray_pixels needs an "L" image, got {im.mode!r}')
        self._w, self._h = im.size
        self._data = im.tobytes()

    def __getitem__(self, xy: tuple[int, int]) -> int:
        x, y = xy
        if not (0 <= x < self._w and 0 <= y < self._h):
            raise IndexError("image index out of range")
        return self._data[y * self._w + x]


def gray_pixels(im: Image.Image) -> GrayPixels:
    """Pixel access of an image already converted to "L"."""
    return GrayPixels(im)


def colour_counts(im: Image.Image, maxcolors: int) -> list[tuple[int, tuple[int, ...]]]:
    """`im.getcolors(maxcolors)` of a multi-band image as (count, colour) pairs: [] when it has more than `maxcolors`
    colours (Pillow's None) or no pixel; a single-band image (Pillow gives a bare number per colour) is a ValueError."""
    raw = im.getcolors(maxcolors) or []
    out = [(n, c) for n, c in raw if isinstance(c, tuple)]
    if len(out) != len(raw):
        raise ValueError(f"colour_counts needs a multi-band image, got {im.mode!r}")
    return out


def gray_profile(im: Image.Image) -> tuple[int, int, int]:
    """(lowest level, highest level, most common level) of a non-empty "L" image, all in Pillow's C code (no colour
    list): a tie for most common goes to the higher level. Any other mode is a ValueError."""
    if im.mode != "L":
        raise ValueError(f'gray_profile needs an "L" image, got {im.mode!r}')
    low, high = im.getextrema()
    if not (isinstance(low, int) and isinstance(high, int)):
        raise ValueError("gray_profile needs a non-empty image")
    counts = im.histogram()
    return low, high, 255 - counts[::-1].index(max(counts))

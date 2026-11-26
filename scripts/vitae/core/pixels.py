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


class RgbPixels:
    """`px[x, y]` of an "RGB" image: its (r, g, b)."""
    __slots__ = ("_data", "_w", "_h")

    def __init__(self, im: Image.Image) -> None:
        if im.mode != "RGB":
            raise ValueError(f'rgb_pixels needs an "RGB" image, got {im.mode!r}')
        self._w, self._h = im.size
        self._data = im.tobytes()

    def __getitem__(self, xy: tuple[int, int]) -> tuple[int, int, int]:
        x, y = xy
        if not (0 <= x < self._w and 0 <= y < self._h):
            raise IndexError("image index out of range")
        i = 3 * (y * self._w + x)
        d = self._data
        return d[i], d[i + 1], d[i + 2]


def gray_pixels(im: Image.Image) -> GrayPixels:
    """Pixel access of an image already converted to "L"."""
    return GrayPixels(im)


def rgb_pixels(im: Image.Image) -> RgbPixels:
    """Pixel access of an image already converted to "RGB"."""
    return RgbPixels(im)


def colour_counts(im: Image.Image, maxcolors: int) -> list[tuple[int, tuple[int, ...]]]:
    """`im.getcolors(maxcolors)` of a multi-band image as (count, colour) pairs: [] when it has more than `maxcolors`
    colours (Pillow's None) or no pixel; a single-band image (Pillow gives a bare number per colour) is a ValueError."""
    out: list[tuple[int, tuple[int, ...]]] = []
    for n, c in im.getcolors(maxcolors) or []:
        if not isinstance(c, tuple):
            raise ValueError(f"colour_counts needs a multi-band image, got {im.mode!r}")
        out.append((n, c))
    return out

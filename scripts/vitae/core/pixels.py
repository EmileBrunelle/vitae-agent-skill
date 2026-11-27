"""Typed pixel access over Pillow images: `Image.load()` is typed as one object that answers `px[x, y]` with a float
or a tuple depending on the image mode, so each mode gets its own view over the image bytes here, and `colour_counts`
validates `getcolors()` at the Pillow boundary."""
from __future__ import annotations

from PIL import Image, ImageChops


class GrayPixels:
    """`px[x, y]` of an "L" image: its luminance, 0..255."""
    __slots__ = ("_data", "_h", "_w")

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


def threshold_lut(n: int, *, below: bool = True) -> list[int]:
    """Lookup table for `Image.point` on an 8-bit band: 255 where the value is under `n` (`below`) or at least `n`
    (not `below`), else 0."""
    return [255 if (v < n) == below else 0 for v in range(256)]


def far_in_luma(im: Image.Image, base: tuple[int, ...], threshold: int) -> Image.Image:
    """"L" mask of the pixels of the RGB `im` whose difference from the colour `base`, taken as luma, is at least
    `threshold` (255 there, else 0). A tint far from `base` in one channel only can fall under it: see `far_in_any_channel`."""
    return ImageChops.difference(im, Image.new("RGB", im.size, base)).convert("L").point(threshold_lut(threshold, below=False))


def far_in_any_channel(im: Image.Image, base: tuple[int, ...], threshold: int) -> Image.Image:
    """RGB mask of the RGB `im`: each channel is 255 where it differs from the same channel of `base` by at least
    `threshold`, else 0, so the mask is blank (`getbbox()` is None) exactly when no pixel is that far on any channel."""
    return ImageChops.difference(im, Image.new("RGB", im.size, base)).point(threshold_lut(threshold, below=False) * 3)

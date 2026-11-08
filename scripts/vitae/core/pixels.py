"""Typed views of PIL's `Image.load()` pixel access: Pillow types it as one object that answers `px[x, y]` with an
int or a tuple depending on the image mode, so each mode gets its own minimal Protocol here."""
from __future__ import annotations

from typing import Protocol, cast

from PIL import Image


class GrayPixels(Protocol):
    """`px[x, y]` of an "L" image."""
    def __getitem__(self, xy: tuple[int, int]) -> int: ...


class RgbPixels(Protocol):
    """`px[x, y]` of an "RGB" image."""
    def __getitem__(self, xy: tuple[int, int]) -> tuple[int, int, int]: ...


def gray_pixels(im: Image.Image) -> GrayPixels:
    """Pixel access of an image already converted to "L"."""
    return cast(GrayPixels, im.load())


def rgb_pixels(im: Image.Image) -> RgbPixels:
    """Pixel access of an image already converted to "RGB"."""
    return cast(RgbPixels, im.load())

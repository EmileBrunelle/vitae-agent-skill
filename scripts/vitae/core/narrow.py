"""Narrowing helpers for values of unknown shape (parsed JSON/TOML, third-party returns).

`isinstance(v, list)` narrows `object` to `list[Unknown]`, which strict pyright then reports at every use;
these guards narrow to the element type the caller will actually check next."""
from __future__ import annotations

from typing import TypeGuard


def is_object_list(v: object) -> TypeGuard[list[object]]:
    return isinstance(v, list)


def is_object_tuple(v: object) -> TypeGuard[tuple[object, ...]]:
    return isinstance(v, tuple)


def is_object_dict(v: object) -> TypeGuard[dict[str, object]]:
    return isinstance(v, dict)

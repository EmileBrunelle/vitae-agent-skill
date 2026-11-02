"""Severity level of one gate line, shared by verify.py and the helper modules.

Kept import-free (stdlib only) so the helpers can use it without importing verify.
Each value is the exact word printed in the report, so f"{level}", ==, .ljust()
and JSON dumps behave as the plain strings they replaced.
"""

from __future__ import annotations

from enum import StrEnum


class Level(StrEnum):
    FAIL = "FAIL"
    WARN = "WARN"
    OK = "OK"
    INFO = "INFO"

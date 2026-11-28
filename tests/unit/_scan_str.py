"""A `str` that counts the C-level work the line-event counter cannot see: the characters its `find` scans and the
characters its slices copy. Deterministic, so a loaded runner cannot flip a complexity result."""
from typing import SupportsIndex


class ScanStr(str):
    """`scanned`: characters `find` looked at (up to the hit, or to the end when it fails) plus characters copied by
    slices; `calls`: number of `find` calls."""
    scanned = 0
    calls = 0

    @staticmethod
    def reset() -> None:
        ScanStr.scanned = ScanStr.calls = 0

    def find(self, sub: str, start: SupportsIndex | None = None, end: SupportsIndex | None = None, /) -> int:
        ScanStr.calls += 1
        begin = 0 if start is None else int(start)
        found = str.find(self, sub, start, end)
        ScanStr.scanned += (len(self) if found < 0 else found) - begin
        return found

    def __getitem__(self, key: SupportsIndex | slice, /) -> str:
        out = str.__getitem__(self, key)
        if isinstance(key, slice):
            ScanStr.scanned += len(out)
        return out

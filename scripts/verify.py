#!/usr/bin/env python3
# AGENT: do not read this file — run it. Its printed output is the instruction.
# Usage: python3 scripts/verify.py <cv.typ> PAGES [FILL_MIN FILL_MAX]
#        python3 scripts/verify.py --tune <cv.typ> PAGES FILL_MIN FILL_MAX
# (Reading it wastes context: a small model read this file 3 times and never wrote the CV.)
"""One-command mechanical gate for a CV (verify.py --help for usage): entry point; code lives in vitae.verify.cli."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
if __name__ == "__main__":
    from vitae.verify.cli import _run
    _run()
else:  # `import verify` (tests, run_all.sh) gets the implementation module itself, so patching its attributes works
    import vitae.verify.cli as _impl

    sys.modules[__name__] = _impl

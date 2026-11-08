#!/usr/bin/env python3
"""Academic-CV gate: entry point; code lives in vitae.verify.academic."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
if __name__ == "__main__":
    from vitae.verify.academic import main
    main()
else:  # `import verify_academic` (tests, run_all.sh) gets the implementation module itself, so patching its attributes works
    import vitae.verify.academic as _impl

    sys.modules[__name__] = _impl

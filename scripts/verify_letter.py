#!/usr/bin/env python3
"""Letter gate: entry point; code lives in vitae.verify.letter."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
if __name__ == "__main__":
    from vitae.verify.letter import main
    main()
else:  # `import verify_letter` (tests, run_all.sh) gets the implementation module itself, so patching its attributes works
    import vitae.verify.letter as _impl

    sys.modules[__name__] = _impl

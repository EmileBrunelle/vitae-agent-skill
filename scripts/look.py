#!/usr/bin/env python3
"""Visual-inspection helper: entry point; code lives in vitae.look."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
if __name__ == "__main__":
    from vitae.look import main
    main()
else:  # `import look` (tests, run_all.sh) gets the implementation module itself, so patching its attributes works
    import vitae.look as _impl

    sys.modules[__name__] = _impl

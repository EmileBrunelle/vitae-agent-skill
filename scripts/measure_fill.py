#!/usr/bin/env python3
"""Page-fill and whitespace measurer: entry point; code lives in vitae.fill."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
if __name__ == "__main__":
    from vitae.fill import main
    main()
else:  # `import measure_fill` (tests, run_all.sh) gets the implementation module itself, so patching its attributes works
    import vitae.fill as _impl

    sys.modules[__name__] = _impl

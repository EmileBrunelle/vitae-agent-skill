#!/usr/bin/env python3
"""Palette generator: entry point; code lives in vitae.palette."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
if __name__ == "__main__":
    from vitae.palette import main
    main()
else:  # `import gen_palette` (tests, run_all.sh) gets the implementation module itself, so patching its attributes works
    import vitae.palette as _impl

    sys.modules[__name__] = _impl

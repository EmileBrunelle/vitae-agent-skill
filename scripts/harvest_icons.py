#!/usr/bin/env python3
"""Icon harvester: entry point; code lives in vitae.icons."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
if __name__ == "__main__":
    from vitae.icons import main
    main()
else:  # `import harvest_icons` (tests, run_all.sh) gets the implementation module itself, so patching its attributes works
    import vitae.icons as _impl

    sys.modules[__name__] = _impl

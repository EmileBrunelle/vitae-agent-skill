#!/usr/bin/env python3
"""Design picker: entry point; code lives in vitae.design.pick."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
if __name__ == "__main__":
    from vitae.design.pick import main
    main()
else:  # `import pick_design` (tests, run_all.sh) gets the implementation module itself, so patching its attributes works
    import vitae.design.pick as _impl

    sys.modules[__name__] = _impl

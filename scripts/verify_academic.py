#!/usr/bin/env python3
"""Academic-CV gate: entry point; code lives in vitae.verify.academic.cli."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
if __name__ == "__main__":
    from vitae.verify.academic.cli import main
    main()

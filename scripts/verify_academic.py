#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["typst==0.15.0", "pypdfium2>=5", "Pillow>=13", "pypdf>=7"]
# ///
"""Academic-CV gate: entry point; code lives in vitae.verify.academic.cli."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
if __name__ == "__main__":
    from vitae.verify.academic.cli import main
    main()

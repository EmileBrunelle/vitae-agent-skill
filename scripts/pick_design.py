#!/usr/bin/env python3
"""Design picker: entry point; code lives in vitae.design.cli."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
if __name__ == "__main__":
    from vitae.design.cli import main
    main()

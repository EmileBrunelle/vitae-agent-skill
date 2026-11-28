#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["typst>=0.15.2,<0.16", "pypdfium2>=5", "Pillow>=13", "pypdf>=7", "pikepdf>=10.8.0; sys_platform != 'darwin' or platform_machine != 'x86_64'"]
# ///
"""Letter gate: entry point; code lives in vitae.verify.letter."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
if __name__ == "__main__":
    from vitae.verify.letter import main
    main()

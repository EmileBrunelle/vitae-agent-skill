"""Put scripts/ on sys.path so tests import the façades (`verify`, `look`, ...) and the `vitae` package.

Importing these modules has no side effect: main() is behind __main__. Shared path constants live in `_paths`.
"""
import sys

from _paths import SCRIPTS

sys.path.insert(0, str(SCRIPTS))

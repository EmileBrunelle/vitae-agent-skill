"""Shared by the verify.py self-test gate modules."""

from __future__ import annotations

import os

# the façade scripts/verify.py: what a user runs (and what the subprocess calls spawn)
VERIFY_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), "verify.py")

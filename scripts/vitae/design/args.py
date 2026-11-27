"""Command-line pieces shared by the design and palette CLIs."""
from __future__ import annotations

import argparse

from vitae.design.tables import AUDACITIES


def add_audacity_arg(parser: argparse.ArgumentParser) -> None:
    """`--audacity`: the colour dial, one of AUDACITIES, default sober."""
    parser.add_argument("--audacity", default="sober", choices=AUDACITIES)

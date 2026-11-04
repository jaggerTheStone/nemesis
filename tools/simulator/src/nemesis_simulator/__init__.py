"""Agent-based corridor simulator (I0.10): passengers, vehicles, stations, reports."""

import random

__version__ = "0.0.0"


def make_rng(seed: int) -> random.Random:
    """Returns the random generator used by a run; a fixed seed makes runs reproducible."""
    return random.Random(seed)

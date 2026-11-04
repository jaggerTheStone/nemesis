"""Wait-time formulas of docs/ALGORITHMES.md (sections 1.2 and 1.3).

Used here to give the fictional wait profiles values consistent with the model the
engine will use; the simulator (I0.10) will test the same formulas.
"""

from __future__ import annotations

import math


def gamma_cdf(shape: int, x: float) -> float:
    """CDF of Gamma(shape, rate 1) for an integer shape (Erlang distribution)."""
    if shape <= 0:
        return 1.0
    if x <= 0:
        return 0.0
    term, total = 1.0, 1.0
    for index in range(1, shape):
        term *= x / index
        total += term
    return 1.0 - math.exp(-x) * total


def gamma_quantile(shape: int, probability: float) -> float:
    """Quantile of Gamma(shape, rate 1) by bisection; 0 for shape 0."""
    if shape <= 0:
        return 0.0
    low, high = 0.0, 1.0
    while gamma_cdf(shape, high) < probability:
        high *= 2
    for _ in range(100):
        middle = (low + high) / 2
        if gamma_cdf(shape, middle) < probability:
            low = middle
        else:
            high = middle
    return (low + high) / 2


def regime_a_seconds(
    remaining_seats: int, passengers_per_minute: float, departure_delay_min: float = 1.0
) -> tuple[int, int]:
    """Regime A, vehicles waiting for passengers: p50 and p80 in seconds.

    The new passenger boards at once; the vehicle leaves when the other
    `remaining_seats - 1` seats are taken: Gamma(r - 1, λp) + d0.
    """
    shape = max(remaining_seats - 1, 0)
    p50 = gamma_quantile(shape, 0.5) / passengers_per_minute + departure_delay_min
    p80 = gamma_quantile(shape, 0.8) / passengers_per_minute + departure_delay_min
    return round(p50 * 60), round(p80 * 60)


def regime_b_seconds(headway_s: float, free_seat_probability: float) -> tuple[int, int]:
    """Regime B, roadside: exponential wait with useful rate q / H."""
    rate_per_s = free_seat_probability / headway_s
    return round(math.log(2) / rate_per_s), round(math.log(5) / rate_per_s)

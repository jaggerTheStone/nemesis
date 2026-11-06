"""Closed formulas of the waits (ALGORITHMES.md 1.2 and 1.3), to compare with the simulator.

Shapes are whole numbers here (seats, vehicles), so the Gamma laws are Erlang laws, whose
distribution function is closed: F(x) = 1 − Σ_{i<k} e^(−λx) (λx)^i / i!.

Regime A comes in two versions:
- « documented »: ALGORITHMES.md 1.2 as written. Case 1 (a vehicle has a seat for the
  newcomer): W ~ min(Gamma(r − 1, λp) + d0, Tmax). Case 2: n more vehicles are needed and
  W ~ Gamma(n, λv) + d0, as if each vehicle left as soon as it arrived;
- « corrected »: the vehicle the newcomer boards leaves when it is full, so after both its
  own arrival T_n ~ Gamma(n, λv) and the arrival A_m ~ Gamma(m, λp) of the m passengers
  still needed to fill it, or Tmax after its first passenger:
  W = min(max(T_n, A_m) + d0, T_n + Tmax), with T_0 = 0 and the remaining Tmax of the
  vehicle loading now when n = 0. T_n and A_m are independent, so
  P(W ≤ x) = F_T(x − Tmax) + [F_T(x − d0) − F_T(x − Tmax)]⁺ · F_A(x − d0).
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass

LN2 = math.log(2.0)
LN5 = math.log(5.0)


def at_least(k: int, mean: float) -> float:
    """P(N ≥ k) for N of Poisson law with this mean: the k-th event has happened."""
    if k <= 0:
        return 1.0
    if mean <= 0:
        return 0.0
    log_mean = math.log(mean)
    tail = 0.0
    for i in range(k):
        tail += math.exp(-mean + i * log_mean - math.lgamma(i + 1))
    return max(0.0, min(1.0, 1.0 - tail))


def erlang_cdf(k: int, rate: float, x: float) -> float:
    """P(Gamma(k, rate) ≤ x); Gamma(0) is 0."""
    if k <= 0:
        return 1.0 if x >= 0 else 0.0
    if x <= 0:
        return 0.0
    return at_least(k, rate * x)


class Cumulative:
    """Λ(t) = ∫ rate, for a rate constant between given times (time-varying Poisson).

    The k-th event after t0 comes before t0 + x with probability P(N ≥ k), N of mean
    Λ(t0 + x) − Λ(t0): the Erlang law with λx replaced by the integral of the rate.
    """

    def __init__(self, times: list[float], rate: Callable[[float], float]) -> None:
        self.times = sorted(times)
        self.rates = [rate(t) for t in self.times]
        self.cum = [0.0]
        for i in range(1, len(self.times)):
            self.cum.append(self.cum[-1] + self.rates[i - 1] * (self.times[i] - self.times[i - 1]))

    def at(self, t: float) -> float:
        from bisect import bisect_right

        i = max(bisect_right(self.times, t) - 1, 0)
        return self.cum[i] + self.rates[i] * (t - self.times[i])

    def mean(self, t0: float, x: float) -> float:
        return self.at(t0 + max(x, 0.0)) - self.at(t0)


def _cdf_k(k: int, rate: float, x: float, profile: tuple[Cumulative, float] | None) -> float:
    """Erlang at a constant rate, or along a rate profile from a start time."""
    if k <= 0:
        return 1.0 if x >= 0 else 0.0
    if x <= 0:
        return 0.0
    if profile is None:
        return at_least(k, rate * x)
    cumulative, t0 = profile
    return at_least(k, cumulative.mean(t0, x))


def quantile(cdf: Callable[[float], float], q: float, upper: float = 3600.0) -> float:
    """Smallest x with cdf(x) ≥ q, by bisection, to the tenth of a second."""
    lo, hi = 0.0, upper
    while cdf(hi) < q:
        lo, hi = hi, hi * 2
        if hi > 1e7:
            return math.inf
    while hi - lo > 0.1:
        mid = (lo + hi) / 2
        if cdf(mid) >= q:
            hi = mid
        else:
            lo = mid
    return hi


@dataclass(frozen=True)
class HeadState:
    """What the head station looks like to a passenger who arrives (regime A)."""

    queue_ahead: int
    vehicles_present: int
    free_front: int
    front_loading: bool
    loading_elapsed_s: float | None
    seats: int
    rate_passengers: float  # per second
    rate_vehicles: float  # per second
    d0: float
    t_max: float
    # Rate profiles from the arrival time, for the corrected formula « along the profile ».
    passengers_profile: tuple[Cumulative, float] | None = None
    vehicles_profile: tuple[Cumulative, float] | None = None


@dataclass(frozen=True)
class Plan:
    """Which vehicle the newcomer boards: n vehicles still to come, m passengers to wait for."""

    case: int
    n: int
    m: int
    t_max_left: float
    r: int


def plan(state: HeadState) -> Plan:
    c = state.seats
    position = state.queue_ahead + 1
    free_front = state.free_front if state.front_loading else 0
    behind = c * (state.vehicles_present - 1) if state.vehicles_present >= 1 else 0
    if position <= free_front:
        elapsed = state.loading_elapsed_s or 0.0
        return Plan(1, 0, free_front - position, max(state.t_max - elapsed, 0.0), free_front)
    rest = position - free_front
    if rest <= behind:
        m = math.ceil(rest / c) * c - rest
        return Plan(1, 0, m, state.t_max, c)
    n = math.ceil((rest - behind) / c)
    return Plan(2, n, n * c - (rest - behind), state.t_max, c)


def documented_a(state: HeadState) -> tuple[float, float]:
    """(p50, p80) of ALGORITHMES.md 1.2 as written."""
    p = plan(state)
    d0, t_max = state.d0, state.t_max
    if p.case == 1:
        r = p.r
        if r <= 1:
            return d0, d0

        def cdf(x: float) -> float:
            return 1.0 if x >= t_max else erlang_cdf(r - 1, state.rate_passengers, x - d0)

    else:

        def cdf(x: float) -> float:
            return erlang_cdf(p.n, state.rate_vehicles, x - d0)

    return quantile(cdf, 0.5), quantile(cdf, 0.8)


def corrected_a(state: HeadState, *, along_profile: bool = False) -> tuple[float, float]:
    """(p50, p80) when the vehicle must also fill up (module docstring).

    With `along_profile`, the rates are those of the coming slots rather than the rates
    at the arrival time: a long wait spans the end of a peak or of a rain.
    """
    p = plan(state)
    d0, t_max = state.d0, state.t_max
    lp, lv = state.rate_passengers, state.rate_vehicles
    pp = state.passengers_profile if along_profile else None
    pv = state.vehicles_profile if along_profile else None
    if p.n == 0:
        tau = p.t_max_left

        def cdf(x: float) -> float:
            return 1.0 if x >= tau else _cdf_k(p.m, lp, x - d0, pp)

    else:

        def cdf(x: float) -> float:
            gone = _cdf_k(p.n, lv, x - t_max, pv)
            arrived = _cdf_k(p.n, lv, x - d0, pv)
            return gone + max(arrived - gone, 0.0) * _cdf_k(p.m, lp, x - d0, pp)

    return quantile(cdf, 0.5), quantile(cdf, 0.8)


def queued_b(rate: float, mean_free: float, ahead: int) -> tuple[float, float]:
    """(p50, p80) at a roadside stop where `ahead` people already wait for the same seats.

    Approximation: useful passages (with at least one free seat) come at rate λpassage × q
    and bring on average `mean_free` seats; the newcomer needs about
    k = ⌈(ahead + 1) / mean_free⌉ of them, so W ~ Gamma(k, λpassage × q). With nobody
    ahead, k = 1 and this is the exponential of ALGORITHMES.md 1.3.
    """
    if rate <= 0:
        return math.inf, math.inf
    k = max(1, math.ceil((ahead + 1) / max(mean_free, 1.0)))

    def cdf(x: float) -> float:
        return erlang_cdf(k, rate, x)

    return quantile(cdf, 0.5), quantile(cdf, 0.8)


def documented_b(rate: float) -> tuple[float, float]:
    """(p50, p80) of ALGORITHMES.md 1.3: exponential wait of rate λpassage × q."""
    if rate <= 0:
        return math.inf, math.inf
    return LN2 / rate, LN5 / rate

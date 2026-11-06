"""Closed formulas against the simulator: coverage of the 50th and 80th percentiles.

For every passenger who left, the formula is given the true state of the system on their
arrival and the true rates (an oracle): what is measured is the error of the formula
itself, not of the estimation of its inputs.
- Regime A: rates of the scenario at the arrival time, rain included.
- Regime B: λpassage × q for each line that serves the passenger's destination. q is the
  share of passages with a free seat within ±45 min of the arrival. λpassage is the rate
  of the scenario for passing lines; for the head line it emerges from the departures, and
  is counted over the same window. Counting over a short window would bias the prediction
  upwards: the wait varies as 1/λ, and E[1/λ̂] > 1/λ when λ̂ rests on a few passages.

A passenger who gave up at the roadside after waiting w is a censored observation: the
true wait exceeds w. If w is at least the predicted percentile, the passenger counts as
not covered; otherwise the outcome is unknown and the passenger is left out (counted).

Coverage is judged as in ALGORITHMES.md 1.8: the 95 % Wilson interval is compared with
the band [78 %, 82 %]. Passengers of the same vehicle are not independent, so the
interval is too narrow; several seeds give an honest picture.
"""

from __future__ import annotations

import math
from bisect import bisect_left, bisect_right
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from typing import Any

from nemesis_simulator.formulas import (
    Cumulative,
    HeadState,
    corrected_a,
    documented_a,
    documented_b,
    plan,
    queued_b,
)
from nemesis_simulator.reports import METRES_PER_DEGREE, Report
from nemesis_simulator.sim import Passenger, Truth

BAND = (0.78, 0.82)
WINDOW_S = 90 * 60
#: Plausibility rule (partie 7.4): a report more than 150 m from its stop is rejected.
PLAUSIBLE_M = 150.0


def wilson(successes: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return 0.0, 1.0
    p = successes / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return max(0.0, centre - half), min(1.0, centre + half)


def verdict(low: float, high: float) -> str:
    """« calibrée » unless the whole interval is outside the band (ALGORITHMES.md 1.8)."""
    if high < BAND[0]:
        return "trop optimiste"
    if low > BAND[1]:
        return "trop prudente"
    return "calibrée"


@dataclass
class Tally:
    n: int = 0
    under_p50: int = 0
    under_p80: int = 0
    censored_left_out: int = 0
    ratio_p80: list[float] = field(default_factory=list)

    def add(self, wait: float, censored: bool, p50: float, p80: float) -> None:
        if censored:
            if wait < p80:
                self.censored_left_out += 1
                return
            self.n += 1
            self.under_p50 += int(wait < p50)
            return
        self.n += 1
        self.under_p50 += int(wait <= p50)
        self.under_p80 += int(wait <= p80)

    def summary(self) -> dict[str, Any]:
        low, high = wilson(self.under_p80, self.n)
        return {
            "n": self.n,
            "coverage_p50": round(self.under_p50 / self.n, 4) if self.n else None,
            "coverage_p80": round(self.under_p80 / self.n, 4) if self.n else None,
            "wilson_p80": [round(low, 4), round(high, 4)],
            "verdict": verdict(low, high) if self.n else "sans données",
            "censored_left_out": self.censored_left_out,
        }


class Groups:
    def __init__(self) -> None:
        self.tallies: dict[str, Tally] = {}

    def add(
        self, names: Iterable[str], wait: float, censored: bool, p50: float, p80: float
    ) -> None:
        for name in names:
            self.tallies.setdefault(name, Tally()).add(wait, censored, p50, p80)

    def summary(self) -> dict[str, Any]:
        return {name: tally.summary() for name, tally in sorted(self.tallies.items())}


def head_state(
    truth: Truth, p: Passenger, profiles: tuple[Cumulative, Cumulative] | None = None
) -> HeadState:
    h = truth.scenario.head
    return HeadState(
        queue_ahead=p.queue_ahead,
        vehicles_present=p.vehicles_present,
        free_front=p.free_front,
        front_loading=p.front_loading,
        loading_elapsed_s=p.loading_elapsed_s,
        seats=h.seats,
        rate_passengers=p.rate_passengers,
        rate_vehicles=p.rate_vehicles,
        d0=h.fill_to_departure_s,
        t_max=h.max_loading_s,
        passengers_profile=(profiles[0], p.arrival_s) if profiles else None,
        vehicles_profile=(profiles[1], p.arrival_s) if profiles else None,
    )


def rate_profiles(truth: Truth) -> tuple[Cumulative, Cumulative]:
    """Passenger and vehicle rates of the head station over the day, rain included."""
    s = truth.scenario
    times = [float(t) for t in s.boundaries()]
    return Cumulative(times, s.head_passenger_rate), Cumulative(times, s.head_vehicle_rate)


def _conditions(truth: Truth, p: Passenger) -> list[str]:
    s = truth.scenario
    names = ["tous"]
    if s.raining(p.arrival_s):
        names.append("pluie")
    names.append("pointe" if s.is_peak(p.arrival_s) else "creuse")
    return names


class PassageIndex:
    """Passages per (stop, line), to count λpassage and q around a time."""

    def __init__(self, truth: Truth) -> None:
        self.times: dict[tuple[str, str], list[float]] = {}
        self.seats: dict[tuple[str, str], list[int]] = {}
        for passage in sorted(truth.passages, key=lambda x: x.t_s):
            key = (passage.stop, passage.line)
            self.times.setdefault(key, []).append(passage.t_s)
            self.seats.setdefault(key, []).append(passage.free_seats)
        self.start, self.end = truth.scenario.start, truth.scenario.end
        self.scenario = truth.scenario
        self.passing = {p.line: p for p in truth.scenario.passing}

    def useful(self, stop: str, line: str, t: float) -> tuple[float, float, int]:
        """Within the window around t (clipped to the day): λpassage × q per second, the
        mean free seats of the passages that have some, and the number of those passages."""
        times = self.times.get((stop, line), [])
        low = max(self.start, t - WINDOW_S / 2)
        high = min(self.end, low + WINDOW_S)
        low = high - WINDOW_S
        a, b = bisect_left(times, low), bisect_right(times, high)
        everything = self.seats[(stop, line)][a:b] if b > a else []
        seats = [f for f in everything if f > 0]
        if not seats:
            return 0.0, 0.0, 0
        q = len(seats) / len(everything)
        passing = self.passing.get(line)
        rate = (
            self.scenario.passing_rate(passing, t)
            if passing is not None
            else len(everything) / (high - low)
        )
        return rate * q, sum(seats) / len(seats), len(seats)


def evaluate(truths: Iterable[Truth]) -> dict[str, Any]:
    a_doc, a_cor, a_pro, b_doc, b_que = Groups(), Groups(), Groups(), Groups(), Groups()
    unpredictable_b = 0
    runs = 0
    for truth in truths:
        runs += 1
        index = PassageIndex(truth)
        profiles = rate_profiles(truth)
        for p in truth.passengers:
            if p.regime == "A":
                if p.wait_s is None:
                    continue
                state = head_state(truth, p, profiles)
                route = plan(state)
                names = _conditions(truth, p)
                names.append(f"cas {route.case}")
                if route.case == 2:
                    names.append("cas 2, n = 1" if route.n == 1 else "cas 2, n ≥ 2")
                predictions = (
                    (a_doc, documented_a(state)),
                    (a_cor, corrected_a(state)),
                    (a_pro, corrected_a(state, along_profile=True)),
                )
                for groups, (p50, p80) in predictions:
                    groups.add(names, p.wait_s, False, p50, p80)
            else:
                useful = [index.useful(p.stop, line, p.arrival_s) for line in p.lines]
                rate = sum(u[0] for u in useful)
                count = sum(u[2] for u in useful)
                mean_free = sum(u[1] * u[2] for u in useful) / count if count else 0.0
                if rate <= 0:
                    unpredictable_b += 1
                    continue
                if p.wait_s is not None:
                    wait, censored = p.wait_s, False
                elif p.abandoned_s is not None:
                    wait, censored = p.abandoned_s - p.arrival_s, True
                else:
                    continue
                names = _conditions(truth, p)
                names.append(p.stop)
                names.append("seul à attendre" if p.queue_ahead == 0 else "d'autres attendent")
                b_doc.add(names, wait, censored, *documented_b(rate))
                b_que.add(names, wait, censored, *queued_b(rate, mean_free, p.queue_ahead))
    return {
        "runs": runs,
        "band": list(BAND),
        "regime_a_documented": a_doc.summary(),
        "regime_a_corrected": a_cor.summary(),
        "regime_a_corrected_profile": a_pro.summary(),
        "regime_b_documented": b_doc.summary(),
        "regime_b_queued": b_que.summary(),
        "regime_b_without_passage": unpredictable_b,
    }


def distance_m(a: dict[str, float], lat: float, lon: float) -> float:
    dy = (a["lat"] - lat) * METRES_PER_DEGREE
    dx = (a["lon"] - lon) * METRES_PER_DEGREE * math.cos(math.radians(lat))
    return math.hypot(dx, dy)


def plausibility(truth: Truth, reports: list[Report]) -> dict[str, Any]:
    """What the 150 m rule alone catches (partie 7.4), and what it wrongly rejects."""
    s = truth.scenario
    by_id = {}
    for code in s.stop_codes:
        from nemesis_simulator.reports import fixture_id

        by_id[fixture_id("stop", code)] = s.stop(code)
    counts: dict[str, int] = {}

    def bump(key: str) -> None:
        counts[key] = counts.get(key, 0) + 1

    for report in reports:
        if report.duplicate:
            bump("renvois (même identifiant)")
            continue
        stop = by_id[report.request["stop_id"]]
        far = distance_m(report.request["location"], stop.lat, stop.lon) > PLAUSIBLE_M
        if report.honest:
            bump("honnêtes rejetés à tort" if far else "honnêtes acceptés")
        else:
            bump(f"fraude {report.fraud} : {'rejetée' if far else 'acceptée'}")
    return dict(sorted(counts.items()))


def markdown(result: dict[str, Any], extra: Callable[[], list[str]] | None = None) -> str:
    lines = [
        "# Formules fermées contre le simulateur",
        "",
        f"{result['runs']} journée(s) simulée(s). Bande visée pour le p80 : 78 à 82 % "
        "(ALGORITHMES.md 1.8). Intervalle de Wilson à 95 %, trop étroit car les passagers "
        "d'un même véhicule ne sont pas indépendants.",
        "",
    ]
    titles = {
        "regime_a_documented": "Régime A, formule d'ALGORITHMES.md 1.2",
        "regime_a_corrected": "Régime A, formule corrigée (remplissage du véhicule)",
        "regime_a_corrected_profile": "Régime A, formule corrigée, débits des tranches à venir",
        "regime_b_documented": "Régime B, formule d'ALGORITHMES.md 1.3",
        "regime_b_queued": "Régime B, avec les personnes qui attendent déjà",
    }
    for key, title in titles.items():
        lines += [
            f"## {title}",
            "",
            "| Groupe | n | ≤ p50 | ≤ p80 | Wilson p80 | Verdict | Censurés écartés |",
            "|---|---|---|---|---|---|---|",
        ]
        for name, row in result[key].items():
            low, high = row["wilson_p80"]
            p50 = "—" if row["coverage_p50"] is None else f"{row['coverage_p50']:.1%}"
            p80 = "—" if row["coverage_p80"] is None else f"{row['coverage_p80']:.1%}"
            lines.append(
                f"| {name} | {row['n']} | {p50} | {p80} | {low:.1%} à {high:.1%} "
                f"| {row['verdict']} | {row['censored_left_out']} |"
            )
        lines.append("")
    lines.append(
        f"Passagers du régime B sans passage utile dans la fenêtre : "
        f"{result['regime_b_without_passage']}."
    )
    if extra:
        lines += ["", *extra()]
    return "\n".join(lines) + "\n"

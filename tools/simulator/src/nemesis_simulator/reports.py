"""Reports sent by the simulated people, in the format of the API (ContributionRequest).

They are drawn from the ground truth with their own random stream, so that changing how
people report never changes the traffic. Each report carries what the server would see
(the request, its reception time, the kind of source and a pseudonym) and, separately,
the truth: the true value, the honesty of the report, its delay, whether it is a resend.

Payload conventions (H-033):
- `file`: {"level": "peu" | "moyen" | "beaucoup" | "tres_long"};
- `vehicules_presents`: {"vehicles": "aucun" | "1_2" | "3_plus"};
- `attente_reelle`: {"wait_s": int};
- `prix_paye`: {"amount_xof": int};
- `vehicule_plein`: {}.
"""

from __future__ import annotations

import math
import random
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from nemesis_simulator.scenario import Scenario, Stop
from nemesis_simulator.sim import Passenger, Truth

#: Same identifiers as the fictional city of the database (data/pipelines, fixtures/sql.py).
FIXTURES_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_URL, "https://example.org/nemesis/fixtures-fictives")

#: Queue categories (ALGORITHMES.md 1.2): upper bound of each, people waiting.
QUEUE_LEVELS = (("peu", 5), ("moyen", 20), ("beaucoup", 50), ("tres_long", math.inf))
VEHICLE_LEVELS = (("aucun", 0), ("1_2", 2), ("3_plus", math.inf))

METRES_PER_DEGREE = 111_320.0


def fixture_id(kind: str, code: str) -> str:
    return str(uuid.uuid5(FIXTURES_NAMESPACE, f"{kind}:{code}"))


def level(value: int, levels: tuple[tuple[str, float], ...]) -> str:
    return next(name for name, upper in levels if value <= upper)


@dataclass(frozen=True)
class Report:
    """One report as received by the server, with its truth."""

    received_s: float
    request: dict[str, Any]
    source_kind: str
    contributor: str
    # Truth, never sent to the server.
    observed_s: float
    honest: bool
    fraud: str | None
    true_value: str
    duplicate: bool

    def envelope(self, scenario: Scenario) -> dict[str, Any]:
        return {
            "received_at": timestamp(scenario, self.received_s),
            "source_kind": self.source_kind,
            "contributor": self.contributor,
            "request": self.request,
        }


def timestamp(scenario: Scenario, seconds: float) -> str:
    """ISO 8601 in UTC, which is also Abidjan's time (Africa/Abidjan, UTC+0)."""
    day = datetime.fromisoformat(scenario.date).replace(tzinfo=UTC)
    moment = day + timedelta(seconds=round(seconds))
    return moment.isoformat().replace("+00:00", "Z")


class Reporter:
    def __init__(self, truth: Truth) -> None:
        self.truth = truth
        self.s = truth.scenario
        self.p = truth.scenario.reports
        self.rng = random.Random(f"{truth.seed}:signalements")
        self.reports: list[Report] = []
        self._head_times = [t for t, _, _ in truth.head_states]

    # Helpers ---------------------------------------------------------------------------

    def _uuid(self) -> str:
        return str(uuid.UUID(int=self.rng.getrandbits(128), version=4))

    def _near(self, stop: Stop, metres: float, *, exact: bool = False) -> dict[str, float]:
        """A position in a random direction: GPS noise of scale `metres`, or at that distance."""
        angle = self.rng.uniform(0, 2 * math.pi)
        distance = metres * self.rng.uniform(0.9, 1.1) if exact else abs(self.rng.gauss(0, metres))
        lat = stop.lat + distance * math.cos(angle) / METRES_PER_DEGREE
        lon = stop.lon + distance * math.sin(angle) / (
            METRES_PER_DEGREE * math.cos(math.radians(stop.lat))
        )
        return {"lat": round(lat, 6), "lon": round(lon, 6)}

    def _delay(self) -> float:
        if self.rng.random() < self.p.offline_share:
            return self.rng.uniform(60, self.p.offline_delay_max_s)
        return self.rng.expovariate(1.0 / self.p.send_delay_mean_s)

    def _head_state(self, t: float) -> tuple[int, int]:
        from bisect import bisect_right

        index = max(bisect_right(self._head_times, t) - 1, 0)
        _, queue, vehicles = self.truth.head_states[index]
        return queue, vehicles

    def _emit(
        self,
        kind: str,
        observed_s: float,
        stop: str,
        line: str | None,
        payload: dict[str, Any],
        *,
        source_kind: str,
        contributor: str,
        true_value: str,
        honest: bool = True,
        fraud: str | None = None,
        location: dict[str, float] | None = None,
    ) -> None:
        stop_info = self.s.stop(stop)
        request: dict[str, Any] = {
            "id": self._uuid(),
            "kind": kind,
            "observed_at": timestamp(self.s, observed_s),
            "city": self.s.city,
            "stop_id": fixture_id("stop", stop),
            "location": location or self._near(stop_info, self.p.accuracy_m),
            "accuracy_m": self.p.accuracy_m,
            "payload": payload,
        }
        if line is not None:
            request["route_id"] = fixture_id("route", line)
            request["direction_id"] = 0
        received = observed_s + self._delay()
        report = Report(
            received,
            request,
            source_kind,
            contributor,
            observed_s,
            honest,
            fraud,
            true_value,
            False,
        )
        self.reports.append(report)
        if self.rng.random() < self.p.duplicate_share:
            # Resent after a cut: same identifier, received later.
            again = Report(
                received + self.rng.uniform(30, 600),
                request,
                source_kind,
                contributor,
                observed_s,
                honest,
                fraud,
                true_value,
                True,
            )
            self.reports.append(again)

    def _slip(self, name: str, levels: tuple[tuple[str, float], ...]) -> str:
        """A category, sometimes reported as a neighbouring one."""
        names = [n for n, _ in levels]
        if self.rng.random() >= self.p.category_error:
            return name
        index = names.index(name) + self.rng.choice((-1, 1))
        return names[min(max(index, 0), len(names) - 1)]

    # Who reports what ------------------------------------------------------------------

    def run(self) -> list[Report]:
        for passenger in self.truth.passengers:
            if self.rng.random() < self.p.app_share:
                self._passenger(passenger)
        self._station_manager()
        self._full_vehicles()
        self._fraud()
        self.reports.sort(key=lambda r: (r.received_s, r.request["id"], r.duplicate))
        return self.reports

    def _passenger(self, p: Passenger) -> None:
        who = f"sim-u{p.id:05d}"
        common = {"source_kind": "usager", "contributor": who}
        line = p.line or (p.lines[0] if p.lines else None)
        if p.regime == "A":
            seen = p.arrival_s + self.rng.uniform(5, 60)
            queue, vehicles = self._head_state(seen)
            if self.rng.random() < self.p.queue_on_arrival:
                true = level(queue, QUEUE_LEVELS)
                self._emit(
                    "file",
                    seen,
                    p.stop,
                    line,
                    {"level": self._slip(true, QUEUE_LEVELS)},
                    true_value=true,
                    **common,
                )
            if self.rng.random() < self.p.vehicles_on_arrival:
                true = level(vehicles, VEHICLE_LEVELS)
                self._emit(
                    "vehicules_presents",
                    seen,
                    p.stop,
                    line,
                    {"vehicles": self._slip(true, VEHICLE_LEVELS)},
                    true_value=true,
                    **common,
                )
        wait = p.wait_s
        if (
            wait is not None
            and p.depart_s is not None
            and self.rng.random() < self.p.wait_on_boarding
        ):
            sigma = self.p.wait_error_sigma
            said = wait * self.rng.lognormvariate(-sigma * sigma / 2, sigma)
            self._emit(
                "attente_reelle",
                p.depart_s,
                p.stop,
                p.line,
                {"wait_s": int(round(said / 60) * 60)},
                true_value=str(round(wait)),
                **common,
            )
        if p.alight_s is not None and p.line and self.rng.random() < self.p.fare_on_alighting:
            p10, p50, p90 = self.s.fares[p.line][self.s.condition(p.board_s or p.arrival_s)]
            amount = self.rng.triangular(p10, p90, p50) if p90 > p10 else p50
            paid = int(round(amount / 25) * 25)
            self._emit(
                "prix_paye",
                p.alight_s,
                p.destination,
                p.line,
                {"amount_xof": paid},
                true_value=str(paid),
                location=self._near(self.s.stop(p.destination), 25),
                **common,
            )

    def _station_manager(self) -> None:
        """A verified station manager at the head station, exact, every 10 min on average."""
        s = self.s
        t = s.start + self.rng.expovariate(1.0 / self.p.station_manager_every_s)
        while t < s.end:
            queue, vehicles = self._head_state(t)
            for kind, payload, true in (
                ("file", {"level": level(queue, QUEUE_LEVELS)}, level(queue, QUEUE_LEVELS)),
                (
                    "vehicules_presents",
                    {"vehicles": level(vehicles, VEHICLE_LEVELS)},
                    level(vehicles, VEHICLE_LEVELS),
                ),
            ):
                self._emit(
                    kind,
                    t,
                    s.head.stop,
                    s.head.line,
                    payload,
                    source_kind="chef_de_gare",
                    contributor="sim-chef-flamboyants",
                    true_value=true,
                    location=self._near(s.stop(s.head.stop), 10),
                )
            t += self.rng.expovariate(1.0 / self.p.station_manager_every_s)

    def _full_vehicles(self) -> None:
        """Waiting passengers with the app who see a full vehicle of their line go by."""
        waiting: dict[str, list[Passenger]] = {}
        for p in self.truth.passengers:
            if p.regime == "B":
                waiting.setdefault(p.stop, []).append(p)
        app = {p.id for ps in waiting.values() for p in ps if self.rng.random() < self.p.app_share}
        for passage in self.truth.passages:
            if passage.free_seats > 0:
                continue
            for p in waiting.get(passage.stop, []):
                end = p.depart_s if p.depart_s is not None else p.abandoned_s
                if (
                    p.id in app
                    and passage.line in p.lines
                    and p.arrival_s <= passage.t_s
                    and (end is None or passage.t_s < end)
                    and self.rng.random() < self.p.full_vehicle_seen
                ):
                    self._emit(
                        "vehicule_plein",
                        passage.t_s,
                        passage.stop,
                        passage.line,
                        {},
                        source_kind="usager",
                        contributor=f"sim-u{p.id:05d}",
                        true_value="plein",
                    )

    def _fraud(self) -> None:
        """Fraudsters: a « very long » queue reported from afar, or an inflated fare."""
        s = self.s
        head = s.stop(s.head.stop)
        for index in range(self.p.fraudsters):
            who = f"sim-f{index:02d}"
            t = s.start + self.rng.expovariate(self.p.fraud_reports_per_hour / 3600)
            while t < s.end:
                if self.rng.random() < 0.5:
                    queue, _ = self._head_state(t)
                    self._emit(
                        "file",
                        t,
                        s.head.stop,
                        s.head.line,
                        {"level": "tres_long"},
                        source_kind="usager",
                        contributor=who,
                        honest=False,
                        fraud="file_a_distance",
                        true_value=level(queue, QUEUE_LEVELS),
                        location=self._near(head, self.p.fraud_distance_m, exact=True),
                    )
                else:
                    _, p50, p90 = s.fares[s.head.line][s.condition(t)]
                    self._emit(
                        "prix_paye",
                        t,
                        "grand-marche",
                        s.head.line,
                        {"amount_xof": 3 * p90},
                        source_kind="usager",
                        contributor=who,
                        honest=False,
                        fraud="prix_gonfle",
                        true_value=str(p50),
                    )
                t += self.rng.expovariate(self.p.fraud_reports_per_hour / 3600)


def reports(truth: Truth) -> list[Report]:
    return Reporter(truth).run()

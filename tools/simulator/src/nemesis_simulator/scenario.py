"""Scenario of a simulated corridor, read from a TOML file (scenarios/*.toml).

Times are seconds since midnight of the scenario day. Profiles are piecewise constant:
a value holds from its time to the next one.
"""

from __future__ import annotations

import tomllib
from bisect import bisect_right
from dataclasses import dataclass, field
from pathlib import Path

SCENARIOS = Path(__file__).resolve().parents[2] / "scenarios"
DEFAULT_SCENARIO = SCENARIOS / "corridor-g1.toml"


def clock(text: str) -> int:
    """« HH:MM » to seconds since midnight."""
    hours, minutes = text.split(":")
    return int(hours) * 3600 + int(minutes) * 60


def hhmm(seconds: float) -> str:
    total = int(seconds) // 60
    return f"{total // 60:02d}:{total % 60:02d}"


@dataclass(frozen=True)
class Profile:
    """Piecewise constant value of the time of day."""

    times: tuple[int, ...]
    values: tuple[float, ...]

    @classmethod
    def parse(cls, points: list[list[object]]) -> Profile:
        pairs = sorted((clock(str(t)), float(v)) for t, v in points)  # type: ignore[arg-type]
        if not pairs:
            raise ValueError("profil vide")
        return cls(tuple(t for t, _ in pairs), tuple(v for _, v in pairs))

    def at(self, t: float) -> float:
        index = bisect_right(self.times, t) - 1
        return self.values[max(index, 0)]


@dataclass(frozen=True)
class Stop:
    code: str
    name: str
    lat: float
    lon: float


@dataclass(frozen=True)
class Head:
    stop: str
    line: str
    seats: int
    fill_to_departure_s: float
    max_loading_s: float
    max_waiting_vehicles: int
    vehicle_headway_s: Profile
    vehicle_headway_cv: float
    passengers_per_min: Profile
    destinations: dict[str, float]


@dataclass(frozen=True)
class Passing:
    line: str
    seats: int
    stops: tuple[str, ...]
    headway_s: Profile
    headway_cv: float
    free_seats_mean: Profile
    alight_probability: float


@dataclass(frozen=True)
class Roadside:
    stops: tuple[str, ...]
    passengers_per_min: Profile
    destinations: dict[str, float]
    patience_s: tuple[float, float]
    boarding: str


@dataclass(frozen=True)
class Travel:
    segment_s: tuple[float, ...]
    traffic_factor: Profile
    noise_sigma: float


@dataclass(frozen=True)
class Rain:
    start: int
    end: int
    vehicle_rate_factor: float
    passenger_rate_factor: float
    travel_factor: float


@dataclass(frozen=True)
class Reports:
    app_share: float
    queue_on_arrival: float
    vehicles_on_arrival: float
    wait_on_boarding: float
    fare_on_alighting: float
    full_vehicle_seen: float
    category_error: float
    wait_error_sigma: float
    send_delay_mean_s: float
    offline_share: float
    offline_delay_max_s: float
    duplicate_share: float
    accuracy_m: float
    station_manager_every_s: float
    fraudsters: int
    fraud_reports_per_hour: float
    fraud_distance_m: float


@dataclass(frozen=True)
class Scenario:
    name: str
    city: str
    date: str
    start: int
    end: int
    is_fictional: bool
    peak: tuple[tuple[int, int], ...]
    stops: tuple[Stop, ...]
    head: Head
    passing: tuple[Passing, ...]
    roadside: Roadside
    travel: Travel
    rain: tuple[Rain, ...]
    fares: dict[str, dict[str, tuple[int, int, int]]]
    reports: Reports
    path: Path = field(default=DEFAULT_SCENARIO, compare=False)

    @property
    def stop_codes(self) -> tuple[str, ...]:
        return tuple(s.code for s in self.stops)

    def stop(self, code: str) -> Stop:
        return next(s for s in self.stops if s.code == code)

    def index(self, code: str) -> int:
        return self.stop_codes.index(code)

    def raining(self, t: float) -> Rain | None:
        return next((r for r in self.rain if r.start <= t < r.end), None)

    def is_peak(self, t: float) -> bool:
        return any(a <= t < b for a, b in self.peak)

    def condition(self, t: float) -> str:
        """Fare condition (ext_fare_estimates.txt): rain first, then peak."""
        if self.raining(t):
            return "pluie"
        return "pointe" if self.is_peak(t) else "normale"

    def boundaries(self) -> list[int]:
        """Times where a rate may change: profile points, rain, 15-min slots."""
        points = set(range(self.start - self.start % 900, self.end + 4 * 3600, 900))
        for profile in (
            self.head.vehicle_headway_s,
            self.head.passengers_per_min,
            self.roadside.passengers_per_min,
            *(p.headway_s for p in self.passing),
        ):
            points.update(profile.times)
        for rain in self.rain:
            points.update((rain.start, rain.end))
        return sorted(points)

    def head_passenger_rate(self, t: float) -> float:
        """Passengers per second at the head station, rain included."""
        rain = self.raining(t)
        factor = rain.passenger_rate_factor if rain else 1.0
        return self.head.passengers_per_min.at(t) * factor / 60.0

    def head_vehicle_rate(self, t: float) -> float:
        """Empty vehicles per second arriving at the head station, rain included."""
        rain = self.raining(t)
        factor = rain.vehicle_rate_factor if rain else 1.0
        return factor / self.head.vehicle_headway_s.at(t)

    def roadside_passenger_rate(self, t: float) -> float:
        rain = self.raining(t)
        factor = rain.passenger_rate_factor if rain else 1.0
        return self.roadside.passengers_per_min.at(t) * factor / 60.0

    def passing_rate(self, passing: Passing, t: float) -> float:
        rain = self.raining(t)
        factor = rain.vehicle_rate_factor if rain else 1.0
        return factor / passing.headway_s.at(t)

    def with_changes(self, **changes: object) -> Scenario:
        """Copy with some fields replaced (tests and variants)."""
        from dataclasses import replace

        return replace(self, **changes)  # type: ignore[arg-type]


def _fares(raw: dict[str, dict[str, list[int]]]) -> dict[str, dict[str, tuple[int, int, int]]]:
    out: dict[str, dict[str, tuple[int, int, int]]] = {}
    for line, conditions in raw.items():
        out[line] = {}
        for condition, values in conditions.items():
            p10, p50, p90 = (int(v) for v in values)
            if not p10 <= p50 <= p90:
                raise ValueError(f"tarif {line} {condition} : p10 ≤ p50 ≤ p90 attendu")
            out[line][condition] = (p10, p50, p90)
    return out


def load(path: Path = DEFAULT_SCENARIO) -> Scenario:
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    meta = data["scenario"]
    if not meta.get("is_fictional", False):
        raise ValueError("le simulateur ne produit que des données fictives (règle 1)")
    stops = tuple(
        Stop(s["code"], s["name"], float(s["lat"]), float(s["lon"])) for s in data["stops"]
    )
    codes = {s.code for s in stops}
    head = data["head"]
    roadside = data["roadside"]
    scenario = Scenario(
        name=meta["name"],
        city=meta["city"],
        date=meta["date"],
        start=clock(meta["start"]),
        end=clock(meta["end"]),
        is_fictional=True,
        peak=tuple((clock(a), clock(b)) for a, b in meta["peak"]),
        stops=stops,
        head=Head(
            stop=head["stop"],
            line=head["line"],
            seats=int(head["seats"]),
            fill_to_departure_s=float(head["fill_to_departure_s"]),
            max_loading_s=float(head["max_loading_s"]),
            max_waiting_vehicles=int(head["max_waiting_vehicles"]),
            vehicle_headway_s=Profile.parse(head["vehicle_headway_s"]),
            vehicle_headway_cv=float(head["vehicle_headway_cv"]),
            passengers_per_min=Profile.parse(head["passengers_per_min"]),
            destinations={k: float(v) for k, v in head["destinations"].items()},
        ),
        passing=tuple(
            Passing(
                line=p["line"],
                seats=int(p["seats"]),
                stops=tuple(p["stops"]),
                headway_s=Profile.parse(p["headway_s"]),
                headway_cv=float(p["headway_cv"]),
                free_seats_mean=Profile.parse(p["free_seats_mean"]),
                alight_probability=float(p["alight_probability"]),
            )
            for p in data.get("passing", [])
        ),
        roadside=Roadside(
            stops=tuple(roadside["stops"]),
            passengers_per_min=Profile.parse(roadside["passengers_per_min"]),
            destinations={k: float(v) for k, v in roadside["destinations"].items()},
            patience_s=(float(roadside["patience_s"][0]), float(roadside["patience_s"][1])),
            boarding=str(roadside["boarding"]),
        ),
        travel=Travel(
            segment_s=tuple(float(s) for s in data["travel"]["segment_s"]),
            traffic_factor=Profile.parse(data["travel"]["traffic_factor"]),
            noise_sigma=float(data["travel"]["noise_sigma"]),
        ),
        rain=tuple(
            Rain(
                start=clock(r["start"]),
                end=clock(r["end"]),
                vehicle_rate_factor=float(r["vehicle_rate_factor"]),
                passenger_rate_factor=float(r["passenger_rate_factor"]),
                travel_factor=float(r["travel_factor"]),
            )
            for r in data.get("rain", [])
        ),
        fares=_fares(data["fares"]),
        reports=_reports(data["reports"]),
        path=path,
    )
    _check(scenario, codes)
    return scenario


def _check(s: Scenario, codes: set[str]) -> None:
    named = [s.head.stop, *s.head.destinations, *s.roadside.stops, *s.roadside.destinations]
    for p in s.passing:
        named.extend(p.stops)
    unknown = sorted(set(named) - codes)
    if unknown:
        raise ValueError(f"arrêts inconnus du scénario : {unknown}")
    if len(s.travel.segment_s) != len(s.stops) - 1:
        raise ValueError("un temps de parcours par segment entre arrêts consécutifs")
    if s.stops[0].code != s.head.stop:
        raise ValueError("le corridor commence à la gare de tête")
    if s.roadside.boarding not in ("aleatoire", "fifo"):
        raise ValueError("roadside.boarding : « aleatoire » ou « fifo »")
    if s.head.fill_to_departure_s > s.head.max_loading_s:
        raise ValueError("d0 doit rester sous Tmax")
    for line in [s.head.line, *(p.line for p in s.passing)]:
        if line not in s.fares:
            raise ValueError(f"tarifs manquants pour la ligne {line}")


def _reports(raw: dict[str, float]) -> Reports:
    values = {k: float(v) for k, v in raw.items()}
    return Reports(**{**values, "fraudsters": int(values["fraudsters"])})  # type: ignore[arg-type]

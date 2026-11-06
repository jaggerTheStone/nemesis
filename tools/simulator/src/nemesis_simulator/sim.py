"""Discrete-event simulation of a corridor (I0.10, PHASE-0.md).

- Passengers arrive by Poisson processes whose rate is constant over each 15-min slot.
- At the head station (regime A), empty vehicles arrive one after another, load in turn
  from a first-come first-served queue, and leave when full after a delay d0, or Tmax
  after their first passenger.
- Along the corridor (regime B), vehicles of the head line and of passing lines stop
  where someone alights or boards; roadside passengers take the first vehicle with a free
  seat that serves their destination, in random order when there are more of them than
  seats.
- Rain lowers the vehicle supply, raises the demand and slows the traffic.

The run records the ground truth: every passenger with the state of the system when they
arrived, every vehicle passage, and the queue at the head station over time.
"""

from __future__ import annotations

import heapq
import math
import random
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field

from nemesis_simulator.scenario import Passing, Scenario

#: Vehicles keep arriving this long after the end, so that late passengers leave.
DRAIN_S = 2 * 3600


@dataclass
class Passenger:
    id: int
    stop: str
    regime: str
    arrival_s: float
    destination: str
    lines: tuple[str, ...]
    # State seen on arrival (ground truth, for the closed formulas).
    queue_ahead: int
    vehicles_present: int = 0
    free_front: int = 0
    front_loading: bool = False
    loading_elapsed_s: float | None = None
    rate_passengers: float = 0.0
    rate_vehicles: float = 0.0
    board_s: float | None = None
    # When the vehicle left with the passenger: the end of the wait (regime A: boarding
    # is immediate, the vehicle leaves when full).
    depart_s: float | None = None
    line: str | None = None
    vehicle: int | None = None
    alight_s: float | None = None
    # Gave up waiting at the roadside: the wait is censored at this time.
    abandoned_s: float | None = None

    @property
    def wait_s(self) -> float | None:
        return None if self.depart_s is None else self.depart_s - self.arrival_s


@dataclass
class Vehicle:
    id: int
    line: str
    seats: int
    onboard: list[int] = field(default_factory=list)
    # Riders from outside the corridor (passing lines), who alight at random.
    through: int = 0
    first_boarding_s: float | None = None
    full: bool = False
    departed: bool = False

    @property
    def free(self) -> int:
        return self.seats - len(self.onboard) - self.through


@dataclass(frozen=True)
class Passage:
    t_s: float
    stop: str
    line: str
    vehicle: int
    free_seats: int
    boarded: int
    waiting: int


@dataclass(frozen=True)
class Departure:
    t_s: float
    vehicle: int
    line: str
    reason: str
    onboard: int


@dataclass
class Truth:
    scenario: Scenario
    seed: int
    passengers: list[Passenger] = field(default_factory=list)
    passages: list[Passage] = field(default_factory=list)
    departures: list[Departure] = field(default_factory=list)
    # (time, queue length, vehicles present) at each change, at the head station.
    head_states: list[tuple[float, int, int]] = field(default_factory=list)
    # Vehicles that found the head station's rank full and went elsewhere.
    turned_away: int = 0
    events: int = 0


def gamma_interval(rng: random.Random, mean: float, cv: float) -> float:
    """Interval of mean `mean` and coefficient of variation `cv` (1 gives Poisson)."""
    if cv <= 0:
        return mean
    if abs(cv - 1.0) < 1e-9:
        return rng.expovariate(1.0 / mean)
    shape = 1.0 / (cv * cv)
    return rng.gammavariate(shape, mean / shape)


class Clock:
    """Operational time of a rate that changes over the day: Λ(t) = ∫ rate.

    A renewal process of varying rate is drawn with intervals of mean 1 in operational
    time, mapped back through Λ⁻¹. The rate then changes as soon as the profile does,
    even in the middle of an interval.
    """

    def __init__(self, times: list[float], rate: Callable[[float], float], horizon: float) -> None:
        self.times = sorted(t for t in times if t <= horizon) + [horizon]
        self.rates = [rate(t) for t in self.times]
        self.cum = [0.0]
        for i in range(1, len(self.times)):
            self.cum.append(self.cum[-1] + self.rates[i - 1] * (self.times[i] - self.times[i - 1]))

    def forward(self, t: float, operational: float) -> float:
        """The time t' > t with Λ(t') − Λ(t) = operational (inf past the horizon)."""
        from bisect import bisect_right

        i = max(bisect_right(self.times, t) - 1, 0)
        target = self.cum[i] + self.rates[i] * (t - self.times[i]) + operational
        while i + 1 < len(self.times) and self.cum[i + 1] < target:
            i += 1
        if i + 1 >= len(self.times):
            return math.inf
        rate = self.rates[i]
        return self.times[i] + (target - self.cum[i]) / rate if rate > 0 else self.times[i + 1]


def poisson(rng: random.Random, mean: float) -> int:
    """Poisson variate (Knuth; the means of the scenarios are small)."""
    if mean <= 0:
        return 0
    limit, k, product = math.exp(-mean), 0, rng.random()
    while product > limit:
        k += 1
        product *= rng.random()
    return k


def weighted(rng: random.Random, weights: dict[str, float]) -> str:
    codes = list(weights)
    return rng.choices(codes, weights=[weights[c] for c in codes])[0]


class Simulation:
    def __init__(self, scenario: Scenario, seed: int) -> None:
        self.s = scenario
        self.rng = random.Random(seed)
        self.truth = Truth(scenario, seed)
        self.queue: deque[int] = deque()
        self.lane: deque[Vehicle] = deque()
        self.waiting: dict[str, list[int]] = {code: [] for code in scenario.roadside.stops}
        self.vehicles: dict[int, Vehicle] = {}
        self._heap: list[tuple[float, int, Callable[[], None]]] = []
        self._seq = 0
        self._now = 0.0
        self._boundaries = scenario.boundaries()
        horizon = scenario.end + DRAIN_S
        self._head_clock = Clock(self._boundaries, scenario.head_vehicle_rate, horizon)
        self._passing_clocks = {
            p.line: Clock(self._boundaries, lambda t, p=p: scenario.passing_rate(p, t), horizon)
            for p in scenario.passing
        }
        head_line = scenario.stop_codes
        self.serves: dict[str, tuple[str, ...]] = {scenario.head.line: head_line}
        for p in scenario.passing:
            self.serves[p.line] = p.stops

    # Event queue -----------------------------------------------------------------------

    def at(self, t: float, action: Callable[[], None]) -> None:
        self._seq += 1
        heapq.heappush(self._heap, (t, self._seq, action))

    def run(self) -> Truth:
        s = self.s
        self._arrivals(s.start, s.end, s.head_passenger_rate, self.head_passenger)
        for code in s.roadside.stops:
            self._arrivals(
                s.start, s.end, s.roadside_passenger_rate, lambda c=code: self.roadside_passenger(c)
            )
        self.at(s.start, self.head_vehicle)
        for p in s.passing:
            self.at(s.start, lambda p=p: self.passing_vehicle(p))
        self._record_head()
        while self._heap:
            t, _, action = heapq.heappop(self._heap)
            self._now = t
            self.truth.events += 1
            action()
        return self.truth

    def _arrivals(
        self,
        start: float,
        end: float,
        rate: Callable[[float], float],
        action: Callable[[], None],
    ) -> None:
        """Schedules a Poisson process whose rate is constant between boundaries."""
        t = start
        index = 0
        while t < end:
            while index < len(self._boundaries) and self._boundaries[index] <= t:
                index += 1
            next_change = self._boundaries[index] if index < len(self._boundaries) else end
            r = rate(t)
            dt = self.rng.expovariate(r) if r > 0 else math.inf
            if t + dt >= min(next_change, end):
                t = min(next_change, end)
                continue
            t += dt
            self.at(t, action)

    def _record_head(self) -> None:
        self.truth.head_states.append((self._now, len(self.queue), len(self.lane)))

    # Head station, regime A -------------------------------------------------------------

    def head_vehicle(self) -> None:
        s = self.s
        if len(self.lane) < s.head.max_waiting_vehicles:
            vehicle = self._new_vehicle(s.head.line, s.head.seats)
            self.lane.append(vehicle)
            if len(self.lane) == 1:
                self._load_front()
            self._record_head()
        else:
            self.truth.turned_away += 1
        step = gamma_interval(self.rng, 1.0, s.head.vehicle_headway_cv)
        following = self._head_clock.forward(self._now, step)
        if following < math.inf:
            self.at(following, self.head_vehicle)

    def _new_vehicle(self, line: str, seats: int) -> Vehicle:
        vehicle = Vehicle(len(self.vehicles), line, seats)
        self.vehicles[vehicle.id] = vehicle
        return vehicle

    def _load_front(self) -> None:
        """The front vehicle takes passengers from the queue, first come first served."""
        if not self.lane:
            return
        front = self.lane[0]
        while self.queue and front.free > 0:
            self._board_head(front, self.queue.popleft())

    def _board_head(self, vehicle: Vehicle, pid: int) -> None:
        passenger = self.truth.passengers[pid]
        passenger.board_s = self._now
        passenger.line = vehicle.line
        passenger.vehicle = vehicle.id
        vehicle.onboard.append(pid)
        if vehicle.first_boarding_s is None:
            vehicle.first_boarding_s = self._now
            self.at(self._now + self.s.head.max_loading_s, lambda v=vehicle: self._timeout(v))
        if vehicle.free == 0 and not vehicle.full:
            vehicle.full = True
            self.at(
                self._now + self.s.head.fill_to_departure_s,
                lambda v=vehicle: self._leave(v, "plein"),
            )

    def _timeout(self, vehicle: Vehicle) -> None:
        if not vehicle.full and not vehicle.departed:
            self._leave(vehicle, "attente_max")

    def _leave(self, vehicle: Vehicle, reason: str) -> None:
        vehicle.departed = True
        self.lane.remove(vehicle)
        for pid in vehicle.onboard:
            self.truth.passengers[pid].depart_s = self._now
        self.truth.departures.append(
            Departure(self._now, vehicle.id, vehicle.line, reason, len(vehicle.onboard))
        )
        self.at(self._now + self._segment(0), lambda: self._reach(vehicle, 1))
        self._load_front()
        self._record_head()

    def head_passenger(self) -> None:
        s = self.s
        front = self.lane[0] if self.lane else None
        loading = front is not None and not front.full
        passenger = Passenger(
            id=len(self.truth.passengers),
            stop=s.head.stop,
            regime="A",
            arrival_s=self._now,
            destination=weighted(self.rng, s.head.destinations),
            lines=(s.head.line,),
            queue_ahead=len(self.queue),
            vehicles_present=len(self.lane),
            free_front=front.free if front is not None and loading else 0,
            front_loading=loading,
            loading_elapsed_s=(
                self._now - front.first_boarding_s
                if front is not None and loading and front.first_boarding_s is not None
                else None
            ),
            rate_passengers=s.head_passenger_rate(self._now),
            rate_vehicles=s.head_vehicle_rate(self._now),
        )
        self.truth.passengers.append(passenger)
        if front is not None and loading and not self.queue:
            self._board_head(front, passenger.id)
        else:
            self.queue.append(passenger.id)
        self._record_head()

    # Along the corridor, regime B -------------------------------------------------------

    def _segment(self, index: int) -> float:
        s = self.s
        base = s.travel.segment_s[index] * s.travel.traffic_factor.at(self._now)
        rain = s.raining(self._now)
        if rain:
            base *= rain.travel_factor
        sigma = s.travel.noise_sigma
        return base * self.rng.lognormvariate(-sigma * sigma / 2, sigma)

    def _reach(self, vehicle: Vehicle, index: int) -> None:
        """The vehicle reaches stop `index` of the corridor."""
        s = self.s
        code = s.stop_codes[index]
        stops = self.serves[vehicle.line]
        staying = []
        for pid in vehicle.onboard:
            if self.truth.passengers[pid].destination == code:
                self.truth.passengers[pid].alight_s = self._now
            else:
                staying.append(pid)
        vehicle.onboard = staying
        if vehicle.through:
            passing = next(p for p in s.passing if p.line == vehicle.line)
            alighting = sum(
                1 for _ in range(vehicle.through) if self.rng.random() < passing.alight_probability
            )
            vehicle.through -= alighting
        if code in self.waiting:
            self._board_roadside(vehicle, code, stops)
        position = stops.index(code)
        if position + 1 < len(stops):
            nxt = s.index(stops[position + 1])
            travel = sum(self._segment(i) for i in range(index, nxt))
            self.at(self._now + travel, lambda: self._reach(vehicle, nxt))
        else:
            # End of the corridor for this vehicle: those still on board get off here.
            for pid in vehicle.onboard:
                self.truth.passengers[pid].alight_s = self._now
            vehicle.onboard = []

    def _board_roadside(self, vehicle: Vehicle, code: str, stops: tuple[str, ...]) -> None:
        here = stops.index(code)
        downstream = set(stops[here + 1 :])
        waiting = self.waiting[code]
        eligible = [pid for pid in waiting if self.truth.passengers[pid].destination in downstream]
        free = max(vehicle.free, 0)
        if len(eligible) <= free:
            boarding = eligible
        elif self.s.roadside.boarding == "fifo":
            boarding = eligible[:free]
        else:
            boarding = self.rng.sample(eligible, free)
        for pid in boarding:
            passenger = self.truth.passengers[pid]
            passenger.board_s = self._now
            passenger.depart_s = self._now
            passenger.line = vehicle.line
            passenger.vehicle = vehicle.id
            vehicle.onboard.append(pid)
        if boarding:
            chosen = set(boarding)
            self.waiting[code] = [pid for pid in waiting if pid not in chosen]
        self.truth.passages.append(
            Passage(self._now, code, vehicle.line, vehicle.id, free, len(boarding), len(eligible))
        )

    def roadside_passenger(self, code: str) -> None:
        s = self.s
        here = s.index(code)
        weights = {d: w for d, w in s.roadside.destinations.items() if s.index(d) > here}
        destination = weighted(self.rng, weights)
        lines = tuple(
            line
            for line, stops in self.serves.items()
            if code in stops
            and destination in stops
            and stops.index(destination) > stops.index(code)
        )
        passenger = Passenger(
            id=len(self.truth.passengers),
            stop=code,
            regime="B",
            arrival_s=self._now,
            destination=destination,
            lines=lines,
            # People already waiting for at least one of the same lines.
            queue_ahead=sum(
                1
                for pid in self.waiting[code]
                if set(self.truth.passengers[pid].lines) & set(lines)
            ),
            rate_passengers=s.roadside_passenger_rate(self._now),
        )
        self.truth.passengers.append(passenger)
        self.waiting[code].append(passenger.id)
        low, high = s.roadside.patience_s
        self.at(self._now + self.rng.uniform(low, high), lambda: self._give_up(passenger))

    def _give_up(self, passenger: Passenger) -> None:
        if passenger.board_s is None:
            passenger.abandoned_s = self._now
            self.waiting[passenger.stop].remove(passenger.id)

    def passing_vehicle(self, passing: Passing) -> None:
        s = self.s
        vehicle = self._new_vehicle(passing.line, passing.seats)
        free = min(passing.seats, poisson(self.rng, passing.free_seats_mean.at(self._now)))
        vehicle.through = passing.seats - free
        entry = s.index(passing.stops[0])
        travel = sum(self._segment(i) for i in range(entry))
        self.at(self._now + travel, lambda: self._reach(vehicle, entry))
        step = gamma_interval(self.rng, 1.0, passing.headway_cv)
        following = self._passing_clocks[passing.line].forward(self._now, step)
        if following < math.inf:
            self.at(following, lambda: self.passing_vehicle(passing))


def simulate(scenario: Scenario, seed: int) -> Truth:
    return Simulation(scenario, seed).run()

"""Description of the fictional city « Lagune-Fictive » and everything derived from it.

Everything here is invented (rule 1.3.1): names carry « (fictif) », the city lies
in the open sea in the Gulf of Guinea (H-027), and every exported record carries
is_fictional = true. Prices, headways and waits are plausible orders of magnitude
for tests, never claims about any real network.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

from nemesis_pipelines.fixtures.geo import distance_m, interpolate
from nemesis_pipelines.fixtures.waits import regime_a_seconds, regime_b_seconds

SEED = 20261104
CITY_CODE = "lagune-fictive"
CITY_NAME = "Lagune-Fictive"
FICTIONAL = " (fictif)"
CITY_BBOX = (-4.06, 1.94, -3.94, 2.06)
STOP_SPACING_M = 1200.0
DAY_TYPES = ("ouvrable", "samedi", "dimanche")
DAY_FACTORS = {"ouvrable": 1.0, "samedi": 1.3, "dimanche": 1.6}
SLOT_S = 15 * 60

# --- Declarations ------------------------------------------------------------------------

AREAS = (
    ("nord", "Lagune-Fictive Nord", (-4.06, 2.025, -3.94, 2.06)),
    ("centre", "Lagune-Fictive Centre", (-4.06, 1.976, -3.94, 2.025)),
    ("sud", "Lagune-Fictive Sud", (-4.06, 1.94, -3.94, 1.976)),
)

# code, name, lon, lat, kind
STATIONS = (
    ("flamboyants", "Gare des Flamboyants", -4.020, 2.045, "gare_artisanale"),
    ("palmiers", "Gare des Palmiers", -3.965, 2.040, "gare_artisanale"),
    ("cocotiers", "Gare des Cocotiers", -4.040, 2.005, "gare_artisanale"),
    ("baobab", "Gare du Baobab", -4.000, 2.010, "gare_artisanale"),
    ("grand-marche", "Gare du Grand Marché", -3.980, 1.995, "gare_artisanale"),
    ("lagune-sud", "Gare de la Lagune-Sud", -4.010, 1.955, "gare_artisanale"),
    ("embarcadere-nord", "Embarcadère Nord", -3.990, 1.986, "embarcadere"),
    ("embarcadere-sud", "Embarcadère Sud", -3.990, 1.966, "embarcadere"),
    ("pont", "Arrêt du Pont", -4.045, 1.978, "arret_informel"),
)

STATION_ALIASES = {
    "flamboyants": (
        ("Gare des Flamboyants", "nom"),
        ("gare flamboyant", "orthographe"),
        ("Flambo", "abreviation"),
    ),
    "palmiers": (
        ("Gare des Palmiers", "nom"),
        ("gare palmier", "orthographe"),
        ("G. Palmiers", "abreviation"),
    ),
    "cocotiers": (
        ("Gare des Cocotiers", "nom"),
        ("gare cocotier", "orthographe"),
        ("Coco", "abreviation"),
    ),
    "baobab": (
        ("Gare du Baobab", "nom"),
        ("gare baobab", "orthographe"),
        ("Ancienne gare du Baobab", "ancien_nom"),
    ),
    "grand-marche": (
        ("Gare du Grand Marché", "nom"),
        ("gare grand marche", "orthographe"),
        ("Gd Marché", "abreviation"),
    ),
    "lagune-sud": (
        ("Gare de la Lagune-Sud", "nom"),
        ("gare lagune sud", "orthographe"),
        ("Lag-Sud", "abreviation"),
    ),
    "embarcadere-nord": (("Embarcadère Nord", "nom"), ("embarcadere nord", "orthographe")),
    "embarcadere-sud": (("Embarcadère Sud", "nom"), ("embarcadere sud", "orthographe")),
    "pont": (("Arrêt du Pont", "nom"), ("arret pont", "orthographe")),
}

# Fictional plural tree and plant names for generated informal stops.
INFORMAL_NAMES = (
    "Manguiers",
    "Fromagers",
    "Acacias",
    "Hibiscus",
    "Bougainvilliers",
    "Tecks",
    "Karités",
    "Avocatiers",
    "Goyaviers",
    "Citronniers",
    "Orangers",
    "Papayers",
    "Bambous",
    "Lauriers",
    "Frangipaniers",
    "Jacarandas",
    "Eucalyptus",
    "Filaos",
    "Kapokiers",
    "Irokos",
    "Ébéniers",
    "Acajous",
    "Rôniers",
    "Raphias",
    "Caïlcédrats",
    "Nérés",
    "Sambas",
    "Frakés",
    "Tamariniers",
    "Badamiers",
)
INFORMAL_PREFIXES = ("Carrefour des", "Arrêt des", "Rond-point des")

# code, category, name, near station, (dlon, dlat), aliases
PLACES = (
    (
        "grand-marche",
        "marche",
        "Grand Marché",
        "grand-marche",
        (0.001, 0.0008),
        (("Grand Marché", "nom"), ("grand marche", "orthographe"), ("Gd Marché", "abreviation")),
    ),
    (
        "pharmacie-lagune",
        "pharmacie",
        "Pharmacie de la Lagune",
        "baobab",
        (-0.0015, -0.001),
        (
            ("Pharmacie de la Lagune", "nom"),
            ("pharmacie lagune", "orthographe"),
            ("Pharma Lagune", "abreviation"),
        ),
    ),
    (
        "eglise-nord",
        "eglise",
        "Église du Quartier Nord",
        "flamboyants",
        (0.002, 0.001),
        (("Église du Quartier Nord", "nom"), ("eglise quartier nord", "orthographe")),
    ),
    (
        "mosquee-centre",
        "mosquee",
        "Mosquée du Centre",
        "baobab",
        (0.0012, 0.0015),
        (("Mosquée du Centre", "nom"), ("mosquee centre", "orthographe")),
    ),
    (
        "ecole-palmiers",
        "ecole",
        "École primaire des Palmiers",
        "palmiers",
        (-0.001, 0.0012),
        (
            ("École primaire des Palmiers", "nom"),
            ("ecole palmiers", "orthographe"),
            ("EPP Palmiers", "abreviation"),
        ),
    ),
    (
        "maquis-fromagers",
        "maquis",
        "Maquis des Trois Fromagers",
        "cocotiers",
        (0.0011, -0.0009),
        (("Maquis des Trois Fromagers", "nom"), ("maquis 3 fromagers", "abreviation")),
    ),
    (
        "carrefour-pont",
        "carrefour",
        "Carrefour du Pont",
        "pont",
        (0.0008, 0.0006),
        (("Carrefour du Pont", "nom"), ("carrefour pont", "orthographe")),
    ),
    (
        "dispensaire-sud",
        "batiment_public",
        "Dispensaire de la Lagune-Sud",
        "lagune-sud",
        (0.0012, 0.0004),
        (("Dispensaire de la Lagune-Sud", "nom"), ("dispensaire lagune sud", "orthographe")),
    ),
)

OPERATORS = (
    ("regie", "Régie des transports de Lagune-Fictive", "public"),
    ("artisanal", "Transport artisanal de Lagune-Fictive", "generique"),
)


@dataclass(frozen=True)
class RouteSpec:
    code: str
    mode: str
    short_name: str
    long_name: str
    operator: str
    network: str
    waypoints: tuple[str, ...]
    route_color: str
    text_color: str
    body_color: str
    color_pattern: str | None
    announced_as: str | None
    express: bool = False


ROUTES = (
    RouteSpec(
        "g1",
        "gbaka",
        "G1",
        "Flamboyants–Grand Marché",
        "artisanal",
        "gbaka",
        ("flamboyants", "baobab", "grand-marche"),
        "1F4E79",
        "FFFFFF",
        "blanc",
        "bande bleue",
        "Grand Marché ! Grand Marché !",
    ),
    RouteSpec(
        "g2",
        "gbaka",
        "G2",
        "Palmiers–Grand Marché",
        "artisanal",
        "gbaka",
        ("palmiers", "grand-marche"),
        "2E75B6",
        "FFFFFF",
        "blanc",
        "bande bleue",
        "Palmiers ! Palmiers !",
    ),
    RouteSpec(
        "g3",
        "gbaka",
        "G3",
        "Cocotiers–Lagune-Sud",
        "artisanal",
        "gbaka",
        ("cocotiers", "pont", "lagune-sud"),
        "203864",
        "FFFFFF",
        "blanc",
        "bande verte",
        "Lagune-Sud ! Lagune-Sud !",
    ),
    RouteSpec(
        "g4",
        "gbaka",
        "G4",
        "Flamboyants–Lagune-Sud",
        "artisanal",
        "gbaka",
        ("flamboyants", "cocotiers", "pont", "lagune-sud"),
        "0B3D91",
        "FFFFFF",
        "blanc",
        "bande rouge",
        "Lagune-Sud par le pont !",
    ),
    RouteSpec(
        "w1",
        "woro_communal",
        "W1",
        "Flamboyants–Palmiers",
        "artisanal",
        "woro-communal",
        ("flamboyants", "palmiers"),
        "FFD966",
        "000000",
        "jaune",
        None,
        None,
    ),
    RouteSpec(
        "w2",
        "woro_communal",
        "W2",
        "Baobab–Embarcadère Nord",
        "artisanal",
        "woro-communal",
        ("baobab", "grand-marche", "embarcadere-nord"),
        "A9D18E",
        "000000",
        "vert",
        None,
        None,
    ),
    RouteSpec(
        "w3",
        "woro_communal",
        "W3",
        "Lagune-Sud–Embarcadère Sud",
        "artisanal",
        "woro-communal",
        ("lagune-sud", "embarcadere-sud"),
        "9DC3E6",
        "000000",
        "bleu",
        None,
        None,
    ),
    RouteSpec(
        "i1",
        "woro_intercommunal",
        "I1",
        "Baobab–Lagune-Sud",
        "artisanal",
        "woro-intercommunal",
        ("baobab", "cocotiers", "pont", "lagune-sud"),
        "C9B18B",
        "000000",
        "beige",
        "bande marron",
        None,
    ),
    RouteSpec(
        "i2",
        "woro_intercommunal",
        "I2",
        "Palmiers–Cocotiers",
        "artisanal",
        "woro-intercommunal",
        ("palmiers", "baobab", "cocotiers"),
        "D6C29E",
        "000000",
        "beige",
        "bande marron",
        None,
    ),
    RouteSpec(
        "b1",
        "bus_sotra",
        "B1",
        "Flamboyants–Lagune-Sud par le pont",
        "regie",
        "regie-bus",
        ("flamboyants", "baobab", "cocotiers", "pont", "lagune-sud"),
        "E46C0A",
        "000000",
        "orange",
        None,
        None,
    ),
    RouteSpec(
        "e1",
        "bus_express",
        "E1",
        "Palmiers–Grand Marché direct",
        "regie",
        "regie-express",
        ("palmiers", "grand-marche"),
        "C00000",
        "FFFFFF",
        "orange",
        "bande rouge",
        None,
        express=True,
    ),
    RouteSpec(
        "l1",
        "bateau_bus",
        "L1",
        "Embarcadère Nord–Embarcadère Sud",
        "regie",
        "regie-bateau",
        ("embarcadere-nord", "embarcadere-sud"),
        "00B0F0",
        "000000",
        "blanc",
        None,
        None,
        express=True,
    ),
)

# Per mode: speed (km/h), dwell at each stop (s), seats choices, departs when full,
# free-seat probability at roadside (peak, off-peak), headway minutes per band kind.
MODES = {
    "gbaka": (
        18,
        30,
        (18, 22, 25, 32),
        True,
        (0.25, 0.6),
        {"debut": 10, "pointe": 5, "creuse": 8, "soir": 15},
    ),
    "woro_communal": (
        20,
        15,
        (4,),
        True,
        (0.2, 0.5),
        {"debut": 6, "pointe": 3, "creuse": 5, "soir": 8},
    ),
    "woro_intercommunal": (
        22,
        15,
        (4,),
        True,
        (0.2, 0.5),
        {"debut": 8, "pointe": 4, "creuse": 7, "soir": 12},
    ),
    "bus_sotra": (
        15,
        30,
        (80,),
        False,
        (0.5, 0.85),
        {"debut": 20, "pointe": 12, "creuse": 20, "soir": 30},
    ),
    "bus_express": (
        25,
        30,
        (80,),
        False,
        (0.6, 0.9),
        {"debut": 30, "pointe": 15, "creuse": 30, "soir": 40},
    ),
    "bateau_bus": (18, 120, (100,), False, (0.9, 1.0), {"pointe": 20, "creuse": 40, "soir": 40}),
}

# Service bands: (start, end, kind). Boats run 06:00 to 20:00 only.
BANDS = (
    ("05:00", "06:00", "debut"),
    ("06:00", "09:00", "pointe"),
    ("09:00", "16:30", "creuse"),
    ("16:30", "20:00", "pointe"),
    ("20:00", "22:00", "soir"),
)

# Typical fares (fictional, XOF) per network: base within one area, extra per area crossed.
FARES = {
    "gbaka": (200, 100),
    "woro-communal": (200, 0),
    "woro-intercommunal": (300, 100),
    "regie-bus": (150, 0),
    "regie-express": (300, 0),
    "regie-bateau": (250, 0),
}
CONDITIONS = {"normale": 1.0, "pointe": 1.25, "pluie": 1.5, "nuit": 1.25, "fete": 1.5}

# --- Derived model ------------------------------------------------------------------------


@dataclass(frozen=True)
class Stop:
    code: str
    name: str
    lon: float
    lat: float
    kind: str
    area: str
    aliases: tuple[tuple[str, str], ...]
    boarding_radius_m: int
    lighting: str


@dataclass(frozen=True)
class Place:
    code: str
    category: str
    name: str
    lon: float
    lat: float
    area: str
    aliases: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class Pattern:
    code: str
    route: RouteSpec
    direction: int
    stops: tuple[str, ...]
    distances_m: tuple[float, ...]
    times_s: tuple[int, ...]

    @property
    def headsign(self) -> str:
        return self.stops[-1]


@dataclass(frozen=True)
class Frequency:
    pattern: str
    day_type: str
    start_s: int
    end_s: int
    band: str
    headway_s: int


@dataclass(frozen=True)
class ServiceProfile:
    pattern: str
    stop: str
    day_type: str
    slot_s: int
    headway_s: int
    headway_cv: float
    departs_when_full: bool
    seats: int
    n_obs: int


@dataclass(frozen=True)
class WaitProfile:
    pattern: str
    stop: str
    day_type: str
    slot_s: int
    regime: str
    p50_s: int
    p80_s: int
    n_obs: int
    n_contributors: int
    confidence: str


@dataclass(frozen=True)
class FareEstimate:
    route: str
    from_area: str
    to_area: str
    condition: str
    p10: int
    p50: int
    p90: int
    n_obs: int
    n_contributors: int
    confidence: str


@dataclass(frozen=True)
class Reliability:
    pattern: str
    day_type: str
    slot_s: int
    service_probability: float
    n_obs: int


@dataclass
class City:
    stops: dict[str, Stop] = field(default_factory=dict)
    places: list[Place] = field(default_factory=list)
    patterns: list[Pattern] = field(default_factory=list)
    frequencies: list[Frequency] = field(default_factory=list)
    service_profiles: list[ServiceProfile] = field(default_factory=list)
    wait_profiles: list[WaitProfile] = field(default_factory=list)
    fare_estimates: list[FareEstimate] = field(default_factory=list)
    reliability: list[Reliability] = field(default_factory=list)
    seats: dict[str, int] = field(default_factory=dict)
    headway_cv: dict[str, float] = field(default_factory=dict)

    @property
    def routes(self) -> tuple[RouteSpec, ...]:
        return ROUTES


def area_of(lon: float, lat: float) -> str:
    for code, _, (lon_min, lat_min, lon_max, lat_max) in AREAS:
        if lon_min <= lon <= lon_max and lat_min <= lat < lat_max:
            return code
    raise ValueError(f"point outside the city: {lon}, {lat}")


def hhmm_to_s(value: str) -> int:
    hours, minutes = value.split(":")
    return int(hours) * 3600 + int(minutes) * 60


def round_to_50(value: float, direction: str = "nearest") -> int:
    if direction == "down":
        return max(50, int(math.floor(value / 50) * 50))
    if direction == "up":
        return int(math.ceil(value / 50) * 50)
    return max(50, int(round(value / 50) * 50))


def confidence_for(contributors: int) -> str:
    if contributors >= 50:
        return "elevee"
    if contributors >= 20:
        return "moyenne"
    return "faible"


def _informal_stops(city: City, rng: random.Random) -> dict[tuple[str, str], list[str]]:
    """Creates the informal stops of every segment between two waypoints, once."""
    segments: dict[tuple[str, str], list[str]] = {}
    counter = 0
    for route in ROUTES:
        if route.express:
            continue
        for start, end in zip(route.waypoints, route.waypoints[1:], strict=False):
            key = tuple(sorted((start, end)))
            if key in segments:
                continue
            a, b = city.stops[key[0]], city.stops[key[1]]
            length = distance_m(a.lon, a.lat, b.lon, b.lat)
            count = max(0, round(length / STOP_SPACING_M) - 1)
            codes = []
            for index in range(1, count + 1):
                lon, lat = interpolate((a.lon, a.lat), (b.lon, b.lat), index / (count + 1))
                lon += rng.uniform(-0.0004, 0.0004)
                lat += rng.uniform(-0.0004, 0.0004)
                noun = INFORMAL_NAMES[counter % len(INFORMAL_NAMES)]
                prefix = INFORMAL_PREFIXES[counter % len(INFORMAL_PREFIXES)]
                name = f"{prefix} {noun}"
                code = f"arret-{counter + 1:02d}"
                city.stops[code] = Stop(
                    code=code,
                    name=name + FICTIONAL,
                    lon=round(lon, 6),
                    lat=round(lat, 6),
                    kind="arret_informel",
                    area=area_of(lon, lat),
                    aliases=((name, "nom"), (noun.lower(), "abreviation")),
                    boarding_radius_m=rng.choice((60, 80, 100, 120)),
                    lighting=rng.choice(("oui", "non", "inconnu")),
                )
                codes.append(code)
                counter += 1
            segments[key] = codes
    return segments


def _pattern_stops(route: RouteSpec, segments: dict[tuple[str, str], list[str]]) -> list[str]:
    stops = [route.waypoints[0]]
    for start, end in zip(route.waypoints, route.waypoints[1:], strict=False):
        if not route.express:
            between = segments[tuple(sorted((start, end)))]
            stops.extend(between if start < end else list(reversed(between)))
        stops.append(end)
    return stops


def build_city(seed: int = SEED) -> City:
    """Builds the whole fictional city deterministically from `seed`."""
    rng = random.Random(seed)
    city = City()

    for code, name, lon, lat, kind in STATIONS:
        city.stops[code] = Stop(
            code=code,
            name=name + FICTIONAL,
            lon=lon,
            lat=lat,
            kind=kind,
            area=area_of(lon, lat),
            aliases=STATION_ALIASES[code],
            boarding_radius_m=40 if kind == "embarcadere" else 60,
            lighting="oui",
        )

    for code, category, name, near, (dlon, dlat), aliases in PLACES:
        station = city.stops[near]
        lon, lat = round(station.lon + dlon, 6), round(station.lat + dlat, 6)
        city.places.append(
            Place(code, category, name + FICTIONAL, lon, lat, area_of(lon, lat), aliases)
        )
    for code, name, lon, lat, kind in STATIONS:
        if kind != "arret_informel":
            city.places.append(
                Place(
                    f"lieu-{code}",
                    "gare",
                    name + FICTIONAL,
                    lon,
                    lat,
                    area_of(lon, lat),
                    STATION_ALIASES[code],
                )
            )

    segments = _informal_stops(city, rng)

    for route in ROUTES:
        speed_kmh, dwell_s, seat_choices, _, _, _ = MODES[route.mode]
        city.seats[route.code] = rng.choice(seat_choices)
        city.headway_cv[route.code] = (
            round(rng.uniform(0.6, 0.9), 2) if route.operator == "artisanal" else 0.3
        )
        forward = _pattern_stops(route, segments)
        for direction, stops in enumerate((forward, list(reversed(forward)))):
            distances, times = [0.0], [0]
            for previous, current in zip(stops, stops[1:], strict=False):
                a, b = city.stops[previous], city.stops[current]
                leg = distance_m(a.lon, a.lat, b.lon, b.lat)
                distances.append(round(distances[-1] + leg, 1))
                times.append(times[-1] + round(leg / (speed_kmh / 3.6)) + dwell_s)
            city.patterns.append(
                Pattern(
                    f"{route.code}-{direction}",
                    route,
                    direction,
                    tuple(stops),
                    tuple(distances),
                    tuple(times),
                )
            )

    _service(city, rng)
    _fares(city, rng)
    return city


def _service(city: City, rng: random.Random) -> None:
    for pattern in city.patterns:
        route = pattern.route
        _, _, _, departs_when_full, (q_peak, q_offpeak), headways = MODES[route.mode]
        line_factor = rng.uniform(0.9, 1.1)
        seats = city.seats[route.code]
        roadside = pattern.stops[1] if len(pattern.stops) > 2 else None
        for day_type in DAY_TYPES:
            for start, end, band in BANDS:
                if band not in headways:
                    continue
                if route.mode == "bateau_bus" and (start < "06:00" or start >= "20:00"):
                    continue
                headway_s = round(headways[band] * DAY_FACTORS[day_type] * line_factor * 60)
                start_s, end_s = hhmm_to_s(start), hhmm_to_s(end)
                city.frequencies.append(
                    Frequency(pattern.code, day_type, start_s, end_s, band, headway_s)
                )
                for slot_s in range(start_s, end_s, SLOT_S):
                    city.service_profiles.append(
                        ServiceProfile(
                            pattern.code,
                            pattern.stops[0],
                            day_type,
                            slot_s,
                            headway_s,
                            city.headway_cv[route.code],
                            departs_when_full,
                            seats,
                            rng.randint(5, 60),
                        )
                    )
                    if day_type != "ouvrable":
                        continue
                    city.reliability.append(
                        Reliability(
                            pattern.code,
                            day_type,
                            slot_s,
                            0.95 if band in ("pointe", "creuse") else 0.8,
                            rng.randint(5, 60),
                        )
                    )
                    q = q_peak if band == "pointe" else q_offpeak
                    if departs_when_full:
                        passengers_per_min = seats / (headway_s / 60)
                        origin = regime_a_seconds(max(seats // 2, 1), passengers_per_min)
                        origin_regime = "A"
                    else:
                        origin = regime_b_seconds(headway_s, 1.0)
                        origin_regime = "B"
                    measured = [(pattern.stops[0], origin_regime, origin)]
                    if roadside:
                        measured.append((roadside, "B", regime_b_seconds(headway_s, q)))
                    for stop, regime, (p50, p80) in measured:
                        contributors = rng.randint(8, 70)
                        city.wait_profiles.append(
                            WaitProfile(
                                pattern.code,
                                stop,
                                day_type,
                                slot_s,
                                regime,
                                p50,
                                p80,
                                contributors + rng.randint(0, 40),
                                contributors,
                                confidence_for(contributors),
                            )
                        )


def _fares(city: City, rng: random.Random) -> None:
    for route in ROUTES:
        base, per_area = FARES[route.network]
        forward = next(p for p in city.patterns if p.route is route and p.direction == 0)
        areas = []
        for code in forward.stops:
            area = city.stops[code].area
            if area not in areas:
                areas.append(area)
        pairs = sorted({(a, b) for a in areas for b in areas})
        order = [code for code, _, _ in AREAS]
        for from_area, to_area in pairs:
            crossed = abs(order.index(from_area) - order.index(to_area))
            typical = base + per_area * crossed
            for condition, factor in CONDITIONS.items():
                if route.operator == "regie":
                    p10 = p50 = p90 = typical
                else:
                    p50 = round_to_50(typical * factor)
                    p10 = round_to_50(p50 * 0.85, "down")
                    p90 = round_to_50(p50 * 1.3, "up")
                contributors = rng.randint(20, 80)
                city.fare_estimates.append(
                    FareEstimate(
                        route.code,
                        from_area,
                        to_area,
                        condition,
                        p10,
                        p50,
                        p90,
                        contributors + rng.randint(0, 60),
                        contributors,
                        confidence_for(contributors),
                    )
                )


def typical_fare(route: RouteSpec, from_area: str, to_area: str) -> int:
    """Fare written to GTFS-Fares v2: the « normale » p50 of the fictional estimates."""
    base, per_area = FARES[route.network]
    order = [code for code, _, _ in AREAS]
    return base + per_area * abs(order.index(from_area) - order.index(to_area))

"""Fictional OpenStreetMap extract of Lagune-Fictive (I0.7), in OSM XML.

Built from the same description as the fictional GTFS, so that the OSM import, the
place promotion, the tiles and the GTFS ↔ OSM gap report can be tested end to end
without any real data. Every element carries `fictional=yes` and every name ends with
« (fictif) ».

The extract departs from the GTFS on purpose, and only in the ways listed in
DIVERGENCES: the gap report must find exactly these gaps.
"""

from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass, field
from xml.sax.saxutils import quoteattr

from nemesis_pipelines.fixtures.city import CITY_BBOX, CITY_NAME, FICTIONAL, OPERATORS, City

METRES_PER_DEGREE = 111_320.0

# Deliberate gaps between this extract and the fictional GTFS (checked by the tests).
MOVED_NEAR = ("arret-05", 35.0)  # moved 35 m east: still matched, reported as moved
MOVED_FAR = ("arret-08", 150.0)  # moved 150 m north: no longer matched on either side
RENAMED = ("arret-11", "Arrêt du Vieux Fromager" + FICTIONAL)
MISSING_STOP = "arret-14"  # mapped in the GTFS only
EXTRA_STOP = ("Arrêt du Nouveau Marché" + FICTIONAL, -3.975, 2.030)  # OSM only
MISSING_ROUTE = "w3"  # both directions absent from OSM
DETOUR_ROUTE = "g3"  # its longest leg makes a 400 m detour in OSM
DETOUR_OFFSET_M = 400.0
EXTRA_ROUTE = ("W9", "Palmiers–Embarcadère Nord", "palmiers", "embarcadere-nord")  # OSM only

DIVERGENCES = {
    "arret_deplace": [MOVED_NEAR[0]],
    "arret_absent_osm": [MISSING_STOP, MOVED_FAR[0]],
    "arret_absent_gtfs": [EXTRA_STOP[0], f"{MOVED_FAR[0]} déplacé"],
    "nom_different": [RENAMED[0]],
    "ligne_absente_osm": [f"{MISSING_ROUTE}-0", f"{MISSING_ROUTE}-1"],
    "trace_different": [f"{DETOUR_ROUTE}-0", f"{DETOUR_ROUTE}-1"],
    "ligne_absente_gtfs": [EXTRA_ROUTE[0]],
}

OSM_ROUTE = {
    "gbaka": "minibus",
    "woro_communal": "share_taxi",
    "woro_intercommunal": "share_taxi",
    "bus_sotra": "bus",
    "bus_express": "bus",
    "bateau_bus": "ferry",
}
ROAD_CLASS = {"minibus": "secondary", "share_taxi": "tertiary", "bus": "primary"}
POI_TAGS = {
    "marche": {"amenity": "marketplace"},
    "pharmacie": {"amenity": "pharmacy"},
    "eglise": {"amenity": "place_of_worship", "religion": "christian"},
    "mosquee": {"amenity": "place_of_worship", "religion": "muslim"},
    "maquis": {"amenity": "restaurant"},
    "ecole": {"amenity": "school"},
    "batiment_public": {"amenity": "townhall"},
    "carrefour": {"highway": "traffic_signals"},
}
# Alias kinds of the fixtures → OSM name keys (values joined with « ; »).
ALIAS_KEYS = {"orthographe": "alt_name", "abreviation": "short_name", "ancien_nom": "old_name"}


@dataclass
class _Element:
    id: int
    tags: dict[str, str]


@dataclass
class _Node(_Element):
    lon: float
    lat: float


@dataclass
class _Way(_Element):
    nodes: list[int]


@dataclass
class _Relation(_Element):
    members: list[tuple[str, int, str]]


@dataclass
class _Extract:
    nodes: list[_Node] = field(default_factory=list)
    ways: list[_Way] = field(default_factory=list)
    relations: list[_Relation] = field(default_factory=list)

    def node(self, lon: float, lat: float, tags: dict[str, str] | None = None) -> int:
        identifier = len(self.nodes) + 1
        self.nodes.append(_Node(identifier, _fictional(tags), round(lon, 7), round(lat, 7)))
        return identifier

    def way(self, nodes: list[int], tags: dict[str, str]) -> int:
        identifier = len(self.ways) + 1
        self.ways.append(_Way(identifier, _fictional(tags), nodes))
        return identifier

    def relation(self, members: list[tuple[str, int, str]], tags: dict[str, str]) -> int:
        identifier = len(self.relations) + 1
        self.relations.append(_Relation(identifier, _fictional(tags), members))
        return identifier


def _fictional(tags: dict[str, str] | None) -> dict[str, str]:
    return {**(tags or {}), "fictional": "yes"}


def offset(lon: float, lat: float, east_m: float, north_m: float) -> tuple[float, float]:
    """Point moved by (east_m, north_m) metres (short distances)."""
    dlat = north_m / METRES_PER_DEGREE
    dlon = east_m / (METRES_PER_DEGREE * math.cos(math.radians(lat)))
    return lon + dlon, lat + dlat


def _names(name: str, aliases: Iterable[tuple[str, str]]) -> dict[str, str]:
    tags = {"name": name}
    grouped: dict[str, list[str]] = {}
    for alias, kind in aliases:
        key = ALIAS_KEYS.get(kind)
        if key and alias != name:
            grouped.setdefault(key, []).append(alias)
    tags.update({key: ";".join(values) for key, values in grouped.items()})
    return tags


def build_extract(city: City) -> _Extract:
    extract = _Extract()
    stops = city.stops

    # Stops: stations, landings and informal stops, with the deliberate gaps.
    platform: dict[str, int] = {}
    for code, stop in stops.items():
        if code == MISSING_STOP:
            continue
        lon, lat = stop.lon, stop.lat
        if code == MOVED_NEAR[0]:
            lon, lat = offset(lon, lat, MOVED_NEAR[1], 0.0)
        elif code == MOVED_FAR[0]:
            lon, lat = offset(lon, lat, 0.0, MOVED_FAR[1])
        name = RENAMED[1] if code == RENAMED[0] else stop.name
        if stop.kind == "embarcadere":
            tags = {"amenity": "ferry_terminal", "public_transport": "station"}
        elif stop.kind == "gare_artisanale":
            tags = {"amenity": "bus_station", "public_transport": "station"}
        else:
            tags = {"public_transport": "platform", "highway": "bus_stop"}
        aliases = () if code == RENAMED[0] else stop.aliases
        platform[code] = extract.node(lon, lat, {**tags, **_names(name, aliases)})
    platform[EXTRA_STOP[0]] = extract.node(
        EXTRA_STOP[1],
        EXTRA_STOP[2],
        {"public_transport": "platform", "highway": "bus_stop", "name": EXTRA_STOP[0]},
    )

    # Road and ferry ways: one per leg between consecutive stops, shared by the routes.
    road_node: dict[str, int] = {}

    def at_stop(code: str) -> int:
        if code not in road_node:
            stop = stops[code]
            road_node[code] = extract.node(stop.lon, stop.lat)
        return road_node[code]

    legs: dict[tuple[str, str], int] = {}
    detour_legs: dict[tuple[str, str], int] = {}

    def leg(a: str, b: str, route: str, detour: bool = False) -> int:
        key = (min(a, b), max(a, b))
        cache = detour_legs if detour else legs
        if key not in cache:
            nodes = [at_stop(key[0])]
            if detour:
                start, end = stops[key[0]], stops[key[1]]
                mid_lon, mid_lat = (start.lon + end.lon) / 2, (start.lat + end.lat) / 2
                nodes.append(extract.node(*offset(mid_lon, mid_lat, 0.0, DETOUR_OFFSET_M)))
            nodes.append(at_stop(key[1]))
            tags = {"route": "ferry"} if route == "ferry" else {"highway": ROAD_CLASS[route]}
            cache[key] = extract.way(nodes, tags)
        return cache[key]

    def longest_leg(sequence: tuple[str, ...]) -> tuple[str, str]:
        pairs = list(zip(sequence, sequence[1:], strict=False))
        lengths = [
            math.dist((stops[a].lon, stops[a].lat), (stops[b].lon, stops[b].lat)) for a, b in pairs
        ]
        a, b = pairs[lengths.index(max(lengths))]
        return (min(a, b), max(a, b))

    detour_key = longest_leg(next(p.stops for p in city.patterns if p.code == f"{DETOUR_ROUTE}-0"))

    # Route relations (one per direction) and route masters.
    operators = {code: name for code, name, _ in OPERATORS}
    masters: dict[str, list[int]] = {}
    for pattern in city.patterns:
        route = pattern.route
        if route.code == MISSING_ROUTE:
            continue
        mode = OSM_ROUTE[route.mode]
        members: list[tuple[str, int, str]] = [
            ("node", platform[code], "platform")
            for code in pattern.stops
            if code in platform and code != MISSING_STOP
        ]
        for a, b in zip(pattern.stops, pattern.stops[1:], strict=False):
            detour = route.code == DETOUR_ROUTE and (min(a, b), max(a, b)) == detour_key
            members.append(("way", leg(a, b, mode, detour), ""))
        first, last = stops[pattern.stops[0]], stops[pattern.stops[-1]]
        relation = extract.relation(
            members,
            {
                "type": "route",
                "route": mode,
                "ref": route.short_name,
                "name": f"{route.short_name} : {first.name} → {last.name}",
                "from": first.name,
                "to": last.name,
                "network": route.network,
                "operator": operators[route.operator] + FICTIONAL,
                "colour": f"#{route.route_color}",
            },
        )
        masters.setdefault(route.code, []).append(relation)
    for route_code, relations in masters.items():
        route = next(r for r in (p.route for p in city.patterns) if r.code == route_code)
        extract.relation(
            [("relation", relation, "") for relation in relations],
            {
                "type": "route_master",
                "route_master": OSM_ROUTE[route.mode],
                "ref": route.short_name,
                "name": route.long_name + FICTIONAL,
                "network": route.network,
            },
        )

    # A share-taxi line that only OSM knows.
    ref, long_name, start, end = EXTRA_ROUTE
    way = leg(start, end, "share_taxi")
    extract.relation(
        [
            ("node", platform[start], "platform"),
            ("way", way, ""),
            ("node", platform[end], "platform"),
        ],
        {
            "type": "route",
            "route": "share_taxi",
            "ref": ref,
            "name": f"{ref} : {long_name}{FICTIONAL}",
            "network": "woro-communal",
        },
    )

    # Landmarks, and a footway from each landmark to the nearest stop.
    for place in city.places:
        if place.category == "gare":
            continue  # the stations above already carry the name
        tags = {**POI_TAGS[place.category], **_names(place.name, place.aliases)}
        poi = extract.node(place.lon, place.lat, tags)
        nearest = min(
            (code for code in stops if code != MISSING_STOP),
            key=lambda code: math.dist((stops[code].lon, stops[code].lat), (place.lon, place.lat)),
        )
        extract.way([poi, at_stop(nearest)], {"highway": "footway"})

    # Administrative boundary of the fictional city.
    lon_min, lat_min, lon_max, lat_max = CITY_BBOX
    corners = [
        extract.node(lon, lat)
        for lon, lat in (
            (lon_min, lat_min),
            (lon_max, lat_min),
            (lon_max, lat_max),
            (lon_min, lat_max),
        )
    ]
    ring = extract.way([*corners, corners[0]], {})
    extract.relation(
        [("way", ring, "outer")],
        {
            "type": "boundary",
            "boundary": "administrative",
            "admin_level": "8",
            "name": CITY_NAME + FICTIONAL,
        },
    )
    return extract


def _tags_xml(tags: dict[str, str]) -> list[str]:
    return [f"    <tag k={quoteattr(k)} v={quoteattr(v)}/>" for k, v in sorted(tags.items())]


def osm_xml(city: City) -> str:
    extract = build_extract(city)
    lon_min, lat_min, lon_max, lat_max = CITY_BBOX
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<osm version="0.6" generator="nemesis-fixtures (données fictives, I0.7)">',
        f'  <bounds minlat="{lat_min}" minlon="{lon_min}" maxlat="{lat_max}" maxlon="{lon_max}"/>',
    ]
    for node in extract.nodes:
        opening = f'  <node id="{node.id}" version="1" lat="{node.lat:.7f}" lon="{node.lon:.7f}"'
        lines += [opening + ">", *_tags_xml(node.tags), "  </node>"]
    for way in extract.ways:
        lines.append(f'  <way id="{way.id}" version="1">')
        lines += [f'    <nd ref="{ref}"/>' for ref in way.nodes]
        lines += [*_tags_xml(way.tags), "  </way>"]
    for relation in extract.relations:
        lines.append(f'  <relation id="{relation.id}" version="1">')
        lines += [
            f'    <member type={quoteattr(kind)} ref="{ref}" role={quoteattr(role)}/>'
            for kind, ref, role in relation.members
        ]
        lines += [*_tags_xml(relation.tags), "  </relation>"]
    lines.append("</osm>")
    return "\n".join(lines) + "\n"

"""Data embedded in the clickable prototype (I0.11), all fictional, used offline.

- `pack/`: the routing engine's city pack (I0.9), with only the GTFS files the engine
  reads, and `gtfs` next to `pack.json` so that the folder can be copied as is;
- `city.json`: stops, lines, places, fares and usual waits, for the screens;
- `map.json`: streets and line shapes as GeoJSON, for the map without tiles.

Identifiers are those of the database (`sql.ident`), so that a report made in the app
names the same stop as on the server.
"""

from __future__ import annotations

import csv
import io
import json
from collections import defaultdict
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

from nemesis_pipelines.fixtures.city import (
    AREAS,
    CITY_BBOX,
    CITY_CODE,
    CITY_NAME,
    DAY_TYPES,
    City,
)
from nemesis_pipelines.fixtures.sql import ident

ASSETS = Path("apps/mobile/assets/fictif")

#: GTFS files the engine reads (services/routing, gtfs.rs).
ENGINE_FILES = (
    "calendar.txt",
    "calendar_dates.txt",
    "ext_fare_estimates.txt",
    "ext_stop_aliases.txt",
    "ext_wait_profiles.txt",
    "frequencies.txt",
    "routes.txt",
    "shapes.txt",
    "stop_areas.txt",
    "stop_times.txt",
    "stops.txt",
    "trips.txt",
)

#: Where the demo user stands: near the Gare des Flamboyants, without GPS.
DEMO_POSITION = {"lat": 2.0438, "lon": -4.0182}

#: Road classes drawn on the map, from the largest.
ROAD_CLASSES = ("primary", "secondary", "tertiary", "residential", "footway", "ferry")


def _fictional(name: str) -> str:
    return name if name.endswith("(fictif)") else f"{name} (fictif)"


def _dump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True) + "\n"


def _rows(text: str) -> list[dict[str, str]]:
    return list(csv.DictReader(io.StringIO(text)))


def city_json(city: City, network_version: str) -> str:
    serving: dict[str, set[str]] = defaultdict(set)
    terminals: dict[str, list[str]] = {}
    for pattern in city.patterns:
        for stop in pattern.stops:
            serving[stop].add(pattern.route.code)
        if pattern.direction == 0:
            terminals[pattern.route.code] = [pattern.stops[0], pattern.stops[-1]]
    stops = [
        {
            "code": s.code,
            "id": ident("stop", s.code),
            "name": _fictional(s.name),
            "kind": s.kind,
            "lat": round(s.lat, 6),
            "lon": round(s.lon, 6),
            "area": s.area,
            "aliases": [alias for alias, _ in s.aliases],
            "lighting": s.lighting,
            "lines": sorted(serving[s.code]),
            "hours": ["05:00", "22:00"],
        }
        for s in sorted(city.stops.values(), key=lambda s: s.code)
    ]
    lines = [
        {
            "code": r.code,
            "id": ident("route", r.code),
            "short_name": r.short_name,
            "long_name": _fictional(r.long_name),
            "mode": r.mode,
            "network": r.network,
            "color": r.route_color,
            "text_color": r.text_color,
            "body_color": r.body_color,
            "color_pattern": r.color_pattern,
            "announced_as": r.announced_as,
            "terminals": terminals.get(r.code, []),
        }
        for r in city.routes
    ]
    places = [
        {
            "code": p.code,
            "category": p.category,
            "name": _fictional(p.name),
            "lat": round(p.lat, 6),
            "lon": round(p.lon, 6),
            "aliases": [alias for alias, _ in p.aliases],
        }
        for p in city.places
    ]
    fares = [
        [f.route, f.from_area, f.to_area, f.condition, f.p10, f.p50, f.p90, f.confidence]
        for f in city.fare_estimates
        if f.condition in ("normale", "pointe")
    ]
    # Usual waits by 15-min slot: [slot start (s), p50 (s), p80 (s), contributors].
    grouped: dict[tuple[str, str, str], list[Any]] = defaultdict(list)
    regimes: dict[tuple[str, str, str], str] = {}
    for w in city.wait_profiles:
        key = (w.stop, w.pattern, w.day_type)
        grouped[key].append([w.slot_s, w.p50_s, w.p80_s, w.n_contributors])
        regimes[key] = w.regime
    waits = [
        {
            "stop": stop,
            "pattern": pattern,
            "line": pattern.rsplit("-", 1)[0],
            "day_type": day,
            "regime": regimes[(stop, pattern, day)],
            "slots": sorted(slots),
        }
        for (stop, pattern, day), slots in sorted(grouped.items())
    ]
    return _dump(
        {
            "city": {
                "code": CITY_CODE,
                "id": ident("city", CITY_CODE),
                "name": _fictional(CITY_NAME),
                "is_fictional": True,
                "network_version": network_version,
                "bbox": list(CITY_BBOX),
                "areas": {code: _fictional(name) for code, name, _ in AREAS},
                "day_types": list(DAY_TYPES),
            },
            "position": DEMO_POSITION,
            "stops": stops,
            "lines": lines,
            "places": places,
            "fares": fares,
            "waits": waits,
        }
    )


def map_json(osm_xml: str, gtfs: dict[str, str]) -> str:
    root = ElementTree.fromstring(osm_xml)
    nodes = {
        n.get("id"): (float(n.get("lon", 0)), float(n.get("lat", 0))) for n in root.iter("node")
    }
    roads = []
    for way in root.iter("way"):
        tags = {t.get("k", ""): t.get("v", "") for t in way.findall("tag")}
        kind = "ferry" if tags.get("route") == "ferry" else tags.get("highway")
        if kind not in ROAD_CLASSES:
            continue
        coordinates = [
            [round(nodes[nd.get("ref")][0], 6), round(nodes[nd.get("ref")][1], 6)]
            for nd in way.findall("nd")
            if nd.get("ref") in nodes
        ]
        if len(coordinates) >= 2:
            roads.append(
                {
                    "type": "Feature",
                    "properties": {"class": kind},
                    "geometry": {"type": "LineString", "coordinates": coordinates},
                }
            )
    routes = {r["route_id"]: r for r in _rows(gtfs["routes.txt"])}
    shape_route = {}
    for trip in _rows(gtfs["trips.txt"]):
        if trip["direction_id"] == "0":
            shape_route[trip["shape_id"]] = trip["route_id"]
    points: dict[str, list[tuple[int, list[float]]]] = defaultdict(list)
    for row in _rows(gtfs["shapes.txt"]):
        if row["shape_id"] in shape_route:
            points[row["shape_id"]].append(
                (
                    int(row["shape_pt_sequence"]),
                    [round(float(row["shape_pt_lon"]), 6), round(float(row["shape_pt_lat"]), 6)],
                )
            )
    lines = []
    for shape, pts in sorted(points.items()):
        route = routes[shape_route[shape]]
        lines.append(
            {
                "type": "Feature",
                "properties": {
                    "line": route["route_id"],
                    "short_name": route["route_short_name"],
                    "color": f"#{route['route_color']}",
                },
                "geometry": {"type": "LineString", "coordinates": [c for _, c in sorted(pts)]},
            }
        )
    return _dump(
        {
            "roads": {"type": "FeatureCollection", "features": roads},
            "lines": {"type": "FeatureCollection", "features": lines},
        }
    )


def mobile_files(
    city: City,
    gtfs: dict[str, str],
    osm_xml: str,
    pack: dict[str, str],
    network_version: str,
) -> dict[Path, str]:
    """Files under apps/mobile/assets/fictif, relative to the repository root."""
    files: dict[Path, str] = {}
    for name in ENGINE_FILES:
        if name in gtfs:
            files[ASSETS / "pack" / "gtfs" / name] = gtfs[name]
    for name, content in pack.items():
        files[ASSETS / "pack" / name] = content
    files[ASSETS / "city.json"] = city_json(city, network_version)
    files[ASSETS / "map.json"] = map_json(osm_xml, gtfs)
    return files

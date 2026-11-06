"""City pack of the routing engine: OSM walking graph (I0.9)."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from nemesis_pipelines.fixtures.city import build_city
from nemesis_pipelines.fixtures.osm import MISSING_ROUTE
from nemesis_pipelines.pack.walkgraph import (
    build_graph,
    distance_m,
    walkable,
    ways_from_geojsonseq,
    ways_from_osm_xml,
)


def test_walking_rules_follow_the_osm_style() -> None:
    assert walkable({"highway": "residential"})
    assert walkable({"highway": "trunk"})  # boulevards are walked along in Abidjan
    assert not walkable({"highway": "motorway"})
    assert walkable({"highway": "motorway", "foot": "yes"})
    assert not walkable({"highway": "footway", "access": "private"})
    assert not walkable({"highway": "pedestrian", "area": "yes"})
    assert not walkable({"building": "yes"})


def test_ways_are_cut_at_intersections_and_ends_only() -> None:
    # A west-east street of three vertices crossed in its middle by a north-south one.
    west, middle, east = (5.3, -4.002), (5.3, -4.0), (5.3, -3.998)
    north, south = (5.302, -4.0), (5.298, -4.0)
    bend = (5.3, -4.0015)  # a plain vertex 55 m from the end: it must not become a node
    graph = build_graph([[west, bend, middle, east], [north, middle, south]])
    # Ends and crossing, plus intermediate nodes: no piece of street longer than 200 m.
    assert {west, east, north, south, middle} <= set(graph.nodes)
    assert all(m <= 200 for *_, m in graph.edges)
    assert bend not in graph.nodes
    total = sum(m for *_, m in graph.edges)
    expected = distance_m(west, east) + distance_m(north, south)
    assert abs(total - expected) < 0.5


def test_parallel_ways_keep_the_shortest() -> None:
    # Two short ways between the same two nodes (a street and a detour around a block).
    a, b, detour = (5.3, -4.0), (5.3, -3.9995), (5.3003, -3.99975)
    graph = build_graph([[a, b], [a, detour, b]])
    assert len(graph.edges) == 1
    assert abs(graph.edges[0][2] - distance_m(a, b)) < 0.5


def test_osmium_geojson_sequences_are_read(tmp_path: Path) -> None:
    path = tmp_path / "voies.geojsonseq"
    features = [
        {
            "type": "Feature",
            "properties": {"highway": "residential"},
            "geometry": {"type": "LineString", "coordinates": [[-4.0, 5.3], [-3.99, 5.3]]},
        },
        {
            "type": "Feature",
            "properties": {"highway": "motorway"},
            "geometry": {"type": "LineString", "coordinates": [[-4.0, 5.31], [-3.99, 5.31]]},
        },
    ]
    path.write_text("".join("\x1e" + json.dumps(f) + "\n" for f in features), encoding="utf-8")
    assert list(ways_from_geojsonseq(path)) == [[(5.3, -4.0), (5.3, -3.99)]]


def test_the_fictional_pack_links_every_stop_to_the_walking_graph(repository: Path) -> None:
    pack = repository / "data/fixtures_fictives/pack"
    meta = json.loads((pack / "pack.json").read_text(encoding="utf-8"))
    assert meta["is_fictional"] and meta["gtfs"] == "../gtfs"
    with (pack / "walk_nodes.csv").open(encoding="utf-8") as handle:
        nodes = [(float(r["lat"]), float(r["lon"])) for r in csv.DictReader(handle)]
    with (pack / meta["gtfs"] / "stops.txt").open(encoding="utf-8") as handle:
        stops = {
            r["stop_id"]: (float(r["stop_lat"]), float(r["stop_lon"]))
            for r in csv.DictReader(handle)
        }
    far = {sid for sid, s in stops.items() if min(distance_m(s, n) for n in nodes) >= 5}
    # Off the walking graph: exactly the stops that no road line of the fictional OSM
    # reaches (the line missing on purpose, and the boat landing on its far side). The
    # engine walks to them in a straight line.
    city = build_city()
    by_road = {
        stop
        for pattern in city.patterns
        if pattern.route.code != MISSING_ROUTE and pattern.route.mode != "bateau_bus"
        for stop in pattern.stops
    }
    assert far == set(stops) - by_road
    assert far == {"arret-20", "embarcadere-sud"}
    graph = build_graph(
        ways_from_osm_xml(
            (repository / "data/fixtures_fictives/osm/lagune-fictive.osm").read_text(
                encoding="utf-8"
            )
        )
    )
    assert graph.nodes_csv() == (pack / "walk_nodes.csv").read_text(encoding="utf-8")

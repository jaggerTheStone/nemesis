"""OpenStreetMap walking graph of a city pack (ALGORITHMES.md 2.1, « Marche »).

Walkable ways are cut at their shared vertices (intersections) and at their ends:
those points become the graph nodes, and each piece between two of them an edge
weighted by its length. The graph is undirected: one-way streets bind vehicles,
not pedestrians. Written as two CSV files read by routing-core.
"""

from __future__ import annotations

import csv
import io
import json
import math
import xml.etree.ElementTree as ElementTree
from collections import Counter
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path

# Same rules as the osm2pgsql style (osm/nemesis.lua): roads closed to pedestrians.
NOT_WALKABLE = {
    "motorway",
    "motorway_link",
    "construction",
    "proposed",
    "raceway",
    "bus_guideway",
    "platform",
    "elevator",
}

Coordinate = tuple[float, float]  # (lat, lon), rounded to 7 decimals like OSM
NODE_SPACING_M = 100.0


def walkable(tags: dict[str, str]) -> bool:
    highway = tags.get("highway")
    if not highway or tags.get("area") == "yes":
        return False
    if tags.get("foot") in ("yes", "designated"):
        return True
    if highway in NOT_WALKABLE or tags.get("foot") == "no":
        return False
    return tags.get("access") not in ("no", "private")


def distance_m(a: Coordinate, b: Coordinate) -> float:
    p1, p2 = math.radians(a[0]), math.radians(b[0])
    dp, dl = p2 - p1, math.radians(b[1] - a[1])
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * 6_371_000 * math.asin(math.sqrt(h))


@dataclass
class WalkGraph:
    nodes: list[Coordinate]
    edges: list[tuple[int, int, float]]

    def nodes_csv(self) -> str:
        out = io.StringIO()
        writer = csv.writer(out, lineterminator="\n")
        writer.writerow(["node", "lat", "lon"])
        writer.writerows([i, f"{lat:.7f}", f"{lon:.7f}"] for i, (lat, lon) in enumerate(self.nodes))
        return out.getvalue()

    def edges_csv(self) -> str:
        out = io.StringIO()
        writer = csv.writer(out, lineterminator="\n")
        writer.writerow(["from", "to", "metres"])
        writer.writerows([a, b, f"{m:.1f}"] for a, b, m in self.edges)
        return out.getvalue()


def densify(line: list[Coordinate], step_m: float) -> list[Coordinate]:
    """Adds points on straight stretches longer than `step_m` (geometry unchanged)."""
    out = [line[0]]
    for a, b in zip(line, line[1:], strict=False):
        length = distance_m(a, b)
        pieces = math.ceil(length / step_m) if length > step_m else 1
        for i in range(1, pieces):
            f = i / pieces
            out.append((round(a[0] + (b[0] - a[0]) * f, 7), round(a[1] + (b[1] - a[1]) * f, 7)))
        out.append(b)
    return out


def build_graph(ways: Iterable[list[Coordinate]]) -> WalkGraph:
    """Nodes at intersections, at ends, and about every `NODE_SPACING_M` along a way, so
    that any point of a street is within reach of a node (the engine attaches points to
    their nearest node)."""
    lines = [[(round(lat, 7), round(lon, 7)) for lat, lon in way] for way in ways]
    lines = [densify(line, NODE_SPACING_M) for line in lines if len(line) >= 2]
    usage: Counter[Coordinate] = Counter()
    for line in lines:
        usage.update(set(line))
    junctions = {c for c, n in usage.items() if n >= 2}
    for line in lines:
        junctions.update((line[0], line[-1]))
        since = 0.0
        for previous, current in zip(line, line[1:], strict=False):
            since += distance_m(previous, current)
            if current in junctions:
                since = 0.0
            elif since >= NODE_SPACING_M:
                junctions.add(current)
                since = 0.0
    ordered = sorted(junctions)
    index = {c: i for i, c in enumerate(ordered)}
    best: dict[tuple[int, int], float] = {}
    for line in lines:
        start, length = line[0], 0.0
        for previous, current in zip(line, line[1:], strict=False):
            length += distance_m(previous, current)
            if current in index:
                a, b = sorted((index[start], index[current]))
                if a != b and length < best.get((a, b), math.inf):
                    best[(a, b)] = length
                start, length = current, 0.0
    edges = sorted((a, b, m) for (a, b), m in best.items())
    used = sorted({n for a, b, _ in edges for n in (a, b)})
    renumber = {old: new for new, old in enumerate(used)}
    return WalkGraph(
        nodes=[ordered[i] for i in used],
        edges=[(renumber[a], renumber[b], m) for a, b, m in edges],
    )


def ways_from_osm_xml(text: str) -> Iterator[list[Coordinate]]:
    """Walkable ways of an OSM XML document (the fictional extract)."""
    root = ElementTree.fromstring(text)
    nodes = {
        n.get("id"): (float(n.get("lat", 0)), float(n.get("lon", 0))) for n in root.iter("node")
    }
    for way in root.iter("way"):
        tags = {t.get("k", ""): t.get("v", "") for t in way.findall("tag")}
        if walkable(tags):
            yield [nodes[nd.get("ref")] for nd in way.findall("nd") if nd.get("ref") in nodes]


def ways_from_geojsonseq(path: Path) -> Iterator[list[Coordinate]]:
    """Walkable ways of `osmium export -f geojsonseq` (one feature per line)."""
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip().lstrip("\x1e")
            if not line:
                continue
            feature = json.loads(line)
            geometry = feature.get("geometry") or {}
            if geometry.get("type") != "LineString" or not walkable(feature.get("properties", {})):
                continue
            yield [(lat, lon) for lon, lat in geometry["coordinates"]]

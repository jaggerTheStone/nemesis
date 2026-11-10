"""Calcule, sur le vrai réseau de rues d'Abidjan, les tracés du scénario de la maquette.

Usage : python itineraires.py <extrait.osm.pbf> <couches.json> <sortie.json>

Les tracés suivent les rues et les liaisons lagunaires d'OpenStreetMap. Tout le reste
(lignes, modes, durées, prix, affluence) est simulé et présenté comme tel par la maquette.
"""

from __future__ import annotations

import heapq
import json
import math
import sys
from collections import defaultdict

import frame
import osmium
from shapely.geometry import LineString

SPEED_KMH = {
    "motorway": 55,
    "motorway_link": 40,
    "trunk": 45,
    "trunk_link": 35,
    "primary": 35,
    "primary_link": 30,
    "secondary": 30,
    "secondary_link": 25,
    "tertiary": 25,
    "tertiary_link": 22,
    "residential": 18,
    "unclassified": 18,
    "living_street": 10,
    "pedestrian": 5,
}
WALKABLE = set(SPEED_KMH) - {"motorway", "motorway_link"}


def build_graph(path: str):
    coords: dict[int, tuple[float, float]] = {}
    drive: dict[int, list] = defaultdict(list)
    walk: dict[int, list] = defaultdict(list)
    for way in osmium.FileProcessor(path).with_locations():
        if not way.is_way():
            continue
        hw = way.tags.get("highway")
        if hw not in SPEED_KMH:
            continue
        oneway = way.tags.get("oneway") in ("yes", "1") or hw in ("motorway", "motorway_link")
        nodes = [(n.ref, n.location) for n in way.nodes if n.location.valid()]
        for (a, la), (b, lb) in zip(nodes, nodes[1:], strict=False):
            pa = frame.project(la.lon, la.lat)
            pb = frame.project(lb.lon, lb.lat)
            coords[a], coords[b] = pa, pb
            metres = math.dist(pa, pb) * 9.5
            seconds = metres / (SPEED_KMH[hw] / 3.6)
            drive[a].append((b, seconds))
            if not oneway:
                drive[b].append((a, seconds))
            if hw in WALKABLE:
                walk[a].append((b, metres / 1.25))
                walk[b].append((a, metres / 1.25))
    return coords, drive, walk


def nearest(coords, graph, point):
    return min((n for n in graph), key=lambda n: math.dist(coords[n], point))


def dijkstra(graph, source, target):
    dist = {source: 0.0}
    prev: dict[int, int] = {}
    heap = [(0.0, source)]
    while heap:
        d, u = heapq.heappop(heap)
        if u == target:
            break
        if d > dist.get(u, math.inf):
            continue
        for v, w in graph[u]:
            nd = d + w
            if nd < dist.get(v, math.inf):
                dist[v], prev[v] = nd, u
                heapq.heappush(heap, (nd, v))
    path = [target]
    while path[-1] != source:
        path.append(prev[path[-1]])
    return path[::-1], dist[target]


def route(coords, graph, a, b, tolerance=0.6):
    na, nb = nearest(coords, graph, a), nearest(coords, graph, b)
    nodes, seconds = dijkstra(graph, na, nb)
    line = LineString([coords[n] for n in nodes]).simplify(tolerance)
    pts = [[round(x, 1), round(y, 1)] for x, y in line.coords]
    return {"points": pts, "seconds": round(seconds), "metres": round(line.length * 9.5)}


def ferry_between(layers, a, b):
    best = None
    for line in layers["ferry"]:
        for pts in (line, line[::-1]):
            score = math.dist(pts[0], a) + math.dist(pts[-1], b)
            if best is None or score < best[0]:
                best = (score, pts)
    pts = best[1]
    return {"points": pts, "metres": round(LineString(pts).length * 9.5)}


def main() -> None:
    pbf, layers_path, target = sys.argv[1:4]
    with open(layers_path, encoding="utf-8") as f:
        layers = json.load(f)
    coords, drive, walk = build_graph(pbf)
    home = (535, 1290)
    dest = (935, 1392)
    ferry_yop = (768, 1514)
    ferry_plateau = (968, 1473)
    adjame = (835, 962)
    home_node = nearest(coords, walk, home)
    dest_node = nearest(coords, walk, dest)
    H, D = coords[home_node], coords[dest_node]
    bus_home, bus_dest = (560, 1262), (930, 1372)
    out = {
        "home": [round(H[0], 1), round(H[1], 1)],
        "dest": [round(D[0], 1), round(D[1], 1)],
        "options": {
            "rapide": [
                {"mode": "walk", **route(coords, walk, H, (548, 1300))},
                {"mode": "woro", **route(coords, drive, (548, 1300), ferry_yop)},
                {"mode": "bateau", **ferry_between(layers, ferry_yop, ferry_plateau)},
                {"mode": "walk", **route(coords, walk, ferry_plateau, D)},
            ],
            "eco": [
                {"mode": "walk", **route(coords, walk, H, bus_home)},
                {"mode": "bus", **route(coords, drive, bus_home, bus_dest)},
                {"mode": "walk", **route(coords, walk, bus_dest, D)},
            ],
            "gbaka": [
                {"mode": "walk", **route(coords, walk, H, bus_home)},
                {"mode": "gbaka", **route(coords, drive, bus_home, adjame)},
                {"mode": "woro", **route(coords, drive, adjame, (918, 1320))},
                {"mode": "walk", **route(coords, walk, (918, 1320), D)},
            ],
        },
        "vehicles": [
            {"mode": "gbaka", **route(coords, drive, (334, 982), adjame, 1.0)},
            {"mode": "gbaka", **route(coords, drive, adjame, (305, 1292), 1.0)},
            {"mode": "bus", **route(coords, drive, (387, 1093), (930, 1372), 1.0)},
            {"mode": "bateau", **ferry_between(layers, ferry_yop, ferry_plateau)},
            {"mode": "bateau", **ferry_between(layers, (762, 1519), (980, 1512))},
            {"mode": "woro", **route(coords, drive, (524, 1272), (624, 1159), 1.0)},
            {"mode": "woro", **route(coords, drive, (879, 1311), (835, 962), 1.0)},
            {"mode": "bus", **route(coords, drive, adjame, (1224, 967), 1.0)},
            {"mode": "woro", **route(coords, drive, (305, 1292), (560, 1262), 1.0)},
            {"mode": "gbaka", **route(coords, drive, (750, 931), (387, 1093), 1.0)},
        ],
    }
    with open(target, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
    for name, legs in out["options"].items():
        print(name, [(leg["mode"], leg["metres"], leg.get("seconds")) for leg in legs])
    print("vehicles", [(v["mode"], v["metres"], len(v["points"])) for v in out["vehicles"]])


if __name__ == "__main__":
    main()

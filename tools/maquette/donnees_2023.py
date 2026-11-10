"""Prépare les données réelles de la maquette yafohi : le corridor Yopougon – Adjamé – Plateau
d'après le GTFS 2023 de DigitalTransport4Africa, et des trajets calculés par le vrai moteur.

Usage : python donnees_2023.py <gtfs.zip> <pack réel> <binaire routing> <sortie.json>

Évaluation interne seulement (H-030) : la maquette présente ces lignes comme « de 2023, à
confirmer », jamais comme l'état actuel. Le GTFS n'a ni prix ni fréquences par heure.
"""

from __future__ import annotations

import csv
import heapq
import io
import json
import math
import subprocess
import sys
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

import frame

WHEN = "2023-06-13T07:30"  # a Tuesday covered by the 2023 calendar
CORRIDOR = (140, 760, 1010, 1570)  # frame pixels: Yopougon, Attécoubé, Adjamé, Le Plateau
HOME = (533.4, 1287.8)
PLACES = [
    ("plateau", "Le Plateau", "Quartier · Abidjan", 935.3, 1391.9),
    ("forum", "Marché du forum", "Marché · Adjamé", 905, 1248),
    ("forum-marches", "Forum des Marchés", "Marché · Adjamé", 855, 1109),
    ("gare-adjame", "Gare d’Adjamé", "Gare · Adjamé", 835, 962),
    ("hopital-adjame", "Hôpital général d’Adjamé", "Hôpital · Adjamé", 878, 1067),
    ("williamsville", "Marché de Williamsville", "Marché · Adjamé", 919, 872),
    ("attecoube", "Marché d’Attécoubé", "Marché · Attécoubé", 768, 1071),
    ("siporex", "Marché Siporex 1", "Marché · Yopougon", 291, 980),
    ("selmer", "Marché Selmer", "Marché · Yopougon", 368, 1166),
    ("koute", "Marché de Kouté", "Marché · Yopougon", 345, 1341),
    ("hopital-yop", "Hôpital général de Yopougon-Attié", "Hôpital · Yopougon", 233, 1154),
]


def read(z: zipfile.ZipFile, name: str) -> list[dict]:
    return list(csv.DictReader(io.TextIOWrapper(z.open(name), encoding="utf-8-sig")))


def mode_and_label(long_name: str) -> tuple[str, str]:
    kind, _, label = long_name.partition(" : ")
    return ("gbaka" if kind.startswith("gbaka") else "woro"), (label or long_name).strip()


def in_corridor(x: float, y: float) -> bool:
    return CORRIDOR[0] <= x <= CORRIDOR[2] and CORRIDOR[1] <= y <= CORRIDOR[3]


def simplify(points: list[tuple[float, float]], tolerance: float) -> list[tuple[float, float]]:
    """Douglas-Peucker, iterative."""
    if len(points) < 3:
        return points
    keep = [False] * len(points)
    keep[0] = keep[-1] = True
    stack = [(0, len(points) - 1)]
    while stack:
        a, b = stack.pop()
        (ax, ay), (bx, by) = points[a], points[b]
        dx, dy = bx - ax, by - ay
        norm = math.hypot(dx, dy) or 1e-9
        best, index = 0.0, -1
        for i in range(a + 1, b):
            px, py = points[i]
            d = abs(dy * (px - ax) - dx * (py - ay)) / norm
            if d > best:
                best, index = d, i
        if best > tolerance and index > 0:
            keep[index] = True
            stack += [(a, index), (index, b)]
    return [p for p, k in zip(points, keep, strict=True) if k]


def cut(pts: list[tuple[float, float]], p: tuple[float, float], q: tuple[float, float]):
    """The shortest stretch of a shape from near `p` to near `q`, in the shape's direction.

    Shapes of round trips pass twice near the same stop: taking the nearest point to each
    stop can draw the whole loop for a 6-minute ride.
    """
    along = [0.0]
    for a, b in zip(pts, pts[1:], strict=False):
        along.append(along[-1] + math.dist(a, b))

    def near(x):
        best = min(math.dist(s, x) for s in pts)
        return [k for k, s in enumerate(pts) if math.dist(s, x) <= best + 12]

    pairs = [(along[j] - along[i], i, j) for i in near(p) for j in near(q) if i <= j]
    if not pairs:
        pairs = [(along[i] - along[j], j, i) for i in near(p) for j in near(q) if j < i]
        _, a, b = min(pairs)
        return pts[a : b + 1][::-1]
    _, a, b = min(pairs)
    return pts[a : b + 1]


def path_d(points: list[tuple[float, float]]) -> str:
    return "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in points)


class WalkGraph:
    def __init__(self, pack: Path) -> None:
        self.xy: dict[int, tuple[float, float]] = {}
        with open(pack / "walk_nodes.csv", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                self.xy[int(row["node"])] = frame.project(float(row["lon"]), float(row["lat"]))
        self.adj: dict[int, list[tuple[int, float]]] = defaultdict(list)
        with open(pack / "walk_edges.csv", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                a, b, m = int(row["from"]), int(row["to"]), float(row["metres"])
                self.adj[a].append((b, m))
                self.adj[b].append((a, m))

    def nearest(self, p: tuple[float, float]) -> int:
        return min(self.adj, key=lambda n: math.dist(self.xy[n], p))

    def path(self, a: tuple[float, float], b: tuple[float, float]) -> list[tuple[float, float]]:
        s, t = self.nearest(a), self.nearest(b)
        dist, prev, heap = {s: 0.0}, {}, [(0.0, s)]
        while heap:
            d, u = heapq.heappop(heap)
            if u == t:
                break
            if d > dist.get(u, math.inf):
                continue
            for v, w in self.adj[u]:
                if d + w < dist.get(v, math.inf):
                    dist[v], prev[v] = d + w, u
                    heapq.heappush(heap, (d + w, v))
        if t not in dist:
            return [a, b]
        nodes = [t]
        while nodes[-1] != s:
            nodes.append(prev[nodes[-1]])
        return [a, *(self.xy[n] for n in reversed(nodes)), b]


def main() -> None:
    gtfs_zip, pack, binary, target = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3], sys.argv[4]
    z = zipfile.ZipFile(gtfs_zip)
    routes = {r["route_id"]: r for r in read(z, "routes.txt")}
    trips = read(z, "trips.txt")
    trip_by_id = {t["trip_id"]: t for t in trips}
    stops = {s["stop_id"]: s for s in read(z, "stops.txt")}
    headway = {f["trip_id"]: int(f["headway_secs"]) for f in read(z, "frequencies.txt")}
    shapes: dict[str, list[tuple[int, tuple[float, float]]]] = defaultdict(list)
    for row in read(z, "shapes.txt"):
        xy = frame.project(float(row["shape_pt_lon"]), float(row["shape_pt_lat"]))
        shapes[row["shape_id"]].append((int(row["shape_pt_sequence"]), xy))
    shape_pts = {k: [p for _, p in sorted(v)] for k, v in shapes.items()}
    stop_xy = {
        k: frame.project(float(s["stop_lon"]), float(s["stop_lat"])) for k, s in stops.items()
    }
    trip_stops: dict[str, list[str]] = defaultdict(list)
    for row in read(z, "stop_times.txt"):
        trip_stops[row["trip_id"]].append(row["stop_id"])

    # Lines of the corridor: at least two stops inside it.
    lines, served = {}, defaultdict(set)
    for t in trips:
        inside = [s for s in trip_stops[t["trip_id"]] if s in stop_xy and in_corridor(*stop_xy[s])]
        if len(inside) < 2:
            continue
        r = routes[t["route_id"]]
        mode, label = mode_and_label(r["route_long_name"])
        for s in inside:
            served[s].add(t["route_id"])
        if t["route_id"] in lines or t["shape_id"] not in shape_pts:
            continue
        lines[t["route_id"]] = {
            "id": t["route_id"],
            "mode": mode,
            "name": label,
            "every": round(headway.get(t["trip_id"], 900) / 60),
            "d": path_d(simplify(shape_pts[t["shape_id"]], 1.2)),
        }

    # Main stops: those served by the most corridor lines, at least 30 px apart.
    ranked = sorted(served, key=lambda s: -len(served[s]))
    kept: list[str] = []
    for s in ranked:
        if len(kept) >= 28:
            break
        if all(math.dist(stop_xy[s], stop_xy[k]) > 30 for k in kept):
            kept.append(s)
    main_stops = []
    for s in kept:
        rs = [lines[r] for r in served[s] if r in lines]
        modes = Counter(r["mode"] for r in rs)
        main_stops.append(
            {
                "id": s,
                "name": stops[s]["stop_name"],
                "x": round(stop_xy[s][0], 1),
                "y": round(stop_xy[s][1], 1),
                "mode": modes.most_common(1)[0][0],
                "count": len(rs),
                "lines": [
                    {"name": r["name"], "mode": r["mode"], "every": r["every"]}
                    for r in sorted(rs, key=lambda r: r["every"])[:8]
                ],
            }
        )

    walk = WalkGraph(pack)

    def plan(a: tuple[float, float], b: tuple[float, float]) -> list[dict]:
        la, lo = frame.unproject(*a)[::-1], frame.unproject(*b)[::-1]
        out = subprocess.run(
            [
                binary,
                "plan",
                "--data",
                str(pack),
                "--at",
                WHEN,
                "--from",
                f"{la[0]:.6f},{la[1]:.6f}",
                "--to",
                f"{lo[0]:.6f},{lo[1]:.6f}",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        result = json.loads(out.stdout)
        options = []
        for o in result["options"]:
            legs = []
            for leg in o["legs"]:
                if leg["type"] == "walk":
                    if leg["metres"] < 30:
                        continue
                    p, q = (frame.project(leg[k]["lon"], leg[k]["lat"]) for k in ("from", "to"))
                    legs.append(
                        {
                            "type": "walk",
                            "metres": leg["metres"],
                            "minutes": leg["minutes"],
                            "d": path_d(simplify(walk.path(p, q), 0.8)),
                        }
                    )
                    continue
                trip = trip_by_id[leg["trip_id"]]
                pts = shape_pts.get(trip["shape_id"], [])
                p = frame.project(leg["board"]["lon"], leg["board"]["lat"])
                q = frame.project(leg["alight"]["lon"], leg["alight"]["lat"])
                seg = [p, *cut(pts, p, q), q] if pts else [p, q]
                mode, label = mode_and_label(routes[leg["route_id"]]["route_long_name"])
                legs.append(
                    {
                        "type": "ride",
                        "mode": mode,
                        "line": label,
                        "board": leg["board"]["name"],
                        "alight": leg["alight"]["name"],
                        "wait50": leg["wait"]["p50_min"],
                        "wait80": leg["wait"]["p80_min"],
                        "minutes": leg["ride_minutes"],
                        "d": path_d(simplify(seg, 0.8)),
                    }
                )
            options.append(
                {
                    "labels": o["labels"],
                    "p50": o["p50_min"],
                    "p80": o["p80_min"],
                    "depart": o["depart"],
                    "arrive50": o["arrive_p50"],
                    "arrive80": o["arrive_p80"],
                    "transfers": o["transfers"],
                    "walk": o["walk_m"],
                    "legs": legs,
                }
            )
        return options

    trips_out = {}
    for key, _name, _sub, x, y in PLACES:
        trips_out[key] = {"to": plan(HOME, (x, y)), "back": plan((x, y), HOME)}
        print(key, [(o["p50"], o["p80"], o["transfers"]) for o in trips_out[key]["to"]])
    result = {
        "when": WHEN,
        "home": list(HOME),
        "places": [
            {
                "key": k,
                "name": n,
                "sub": s,
                "x": x,
                "y": y,
                "km": f"{math.dist(HOME, (x, y)) * 9.5 / 1000:.1f}".replace(".", ",") + " km",
            }
            for k, n, s, x, y in PLACES
        ],
        "lines": sorted(lines.values(), key=lambda r: r["mode"]),
        "stops": main_stops,
        "trips": trips_out,
    }
    Path(target).write_text(json.dumps(result, ensure_ascii=False, separators=(",", ":")), "utf-8")
    print(len(lines), "lignes,", len(main_stops), "arrêts,", Path(target).stat().st_size, "octets")


if __name__ == "__main__":
    main()

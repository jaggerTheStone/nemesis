"""Tire de l'extrait OSM d'Abidjan les couches dessinées par la maquette.

Usage : python extraire.py <extrait.osm.pbf> <sortie.json>
Dépendances : osmium (pyosmium) et shapely, hors du projet (outil de maquette).

Sortie : géométries projetées dans le cadre de `frame.py` (pixels CSS au zoom 14),
simplifiées, et lieux nommés. Données © contributeurs OpenStreetMap, ODbL.
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict

import frame
import osmium
from shapely import wkb
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import linemerge, polygonize, transform, unary_union

ROAD_CLASS = {
    "motorway": "motorway",
    "motorway_link": "motorway",
    "trunk": "trunk",
    "trunk_link": "trunk",
    "primary": "primary",
    "primary_link": "primary",
    "secondary": "secondary",
    "secondary_link": "secondary",
    "tertiary": "tertiary",
    "tertiary_link": "tertiary",
    "residential": "minor",
    "unclassified": "minor",
    "living_street": "minor",
    "pedestrian": "minor",
}

GREEN = {
    ("natural", "wood"),
    ("natural", "scrub"),
    ("natural", "grassland"),
    ("natural", "wetland"),
    ("landuse", "forest"),
    ("landuse", "grass"),
    ("landuse", "meadow"),
    ("landuse", "recreation_ground"),
    ("landuse", "cemetery"),
    ("leisure", "park"),
    ("leisure", "golf_course"),
    ("leisure", "nature_reserve"),
    ("boundary", "national_park"),
    ("boundary", "protected_area"),
}
FOREST = {("natural", "wood"), ("landuse", "forest"), ("boundary", "national_park")}
SAND = {("natural", "beach"), ("natural", "sand")}
INDUSTRIAL = {
    ("landuse", "industrial"),
    ("landuse", "port"),
    ("landuse", "railway"),
    ("landuse", "military"),
}

POI_KIND = {
    ("amenity", "bus_station"): "gare",
    ("public_transport", "station"): "gare",
    ("amenity", "ferry_terminal"): "embarcadere",
    ("amenity", "marketplace"): "marche",
    ("amenity", "university"): "universite",
    ("amenity", "hospital"): "hopital",
    ("shop", "mall"): "centre_commercial",
}


def tag_pairs(tags) -> set[tuple[str, str]]:
    return {(t.k, t.v) for t in tags}


class Collector:
    def __init__(self) -> None:
        self.roads: dict[str, list] = defaultdict(list)
        self.road_names: list[tuple[str, str, LineString]] = []
        self.water: list = []
        self.coast: list[LineString] = []
        self.green: list = []
        self.forest: list = []
        self.sand: list = []
        self.industrial: list = []
        self.airport: list = []
        self.runways: list = []
        self.rail: list = []
        self.ferry: list = []
        self.rivers: list = []
        self.places: list[dict] = []
        self.pois: list[dict] = []


def collect(path: str) -> Collector:
    out = Collector()
    factory = osmium.geom.WKBFactory()
    processor = osmium.FileProcessor(path).with_locations().with_areas()
    for obj in processor:
        tags = obj.tags
        pairs = tag_pairs(tags)
        name = tags.get("name")
        if obj.is_node():
            loc = obj.location
            if "place" in tags and name:
                out.places.append(
                    {"name": name, "place": tags["place"], "lon": loc.lon, "lat": loc.lat}
                )
            for pair, kind in POI_KIND.items():
                if pair in pairs and name:
                    out.pois.append({"name": name, "kind": kind, "lon": loc.lon, "lat": loc.lat})
            continue
        if obj.is_way():
            try:
                line = wkb.loads(factory.create_linestring(obj), hex=True)
            except Exception:  # noqa: BLE001 — incomplete way at the extract edge
                continue
            highway = tags.get("highway")
            if highway in ROAD_CLASS:
                cls = ROAD_CLASS[highway]
                out.roads[cls].append(line)
                if name and cls != "minor":
                    out.road_names.append((cls, name, line))
            if ("natural", "coastline") in pairs:
                out.coast.append(line)
            if tags.get("railway") == "rail":
                out.rail.append(line)
            if tags.get("route") == "ferry":
                out.ferry.append(line)
            if tags.get("aeroway") == "runway":
                out.runways.append(line)
            if tags.get("waterway") in ("river", "canal", "stream"):
                out.rivers.append(line)
            continue
        if obj.is_area():
            try:
                geom = wkb.loads(factory.create_multipolygon(obj), hex=True)
            except Exception:  # noqa: BLE001 — broken multipolygon
                continue
            if (
                ("natural", "water") in pairs
                or "water" in tags
                or tags.get("waterway") == "riverbank"
            ):
                out.water.append(geom)
            if pairs & GREEN:
                (out.forest if pairs & FOREST else out.green).append(geom)
            if pairs & SAND:
                out.sand.append(geom)
            if pairs & INDUSTRIAL:
                out.industrial.append(geom)
            if tags.get("aeroway") == "aerodrome":
                out.airport.append(geom)
            if tags.get("aeroway") == "apron":
                out.industrial.append(geom)
            for pair, kind in POI_KIND.items():
                if pair in pairs and name:
                    c = geom.representative_point()
                    out.pois.append({"name": name, "kind": kind, "lon": c.x, "lat": c.y})
    return out


def land_from_coast(coast: list[LineString], bbox: Polygon):
    """Land polygons inside `bbox`: OSM coastlines keep land on their left."""
    if not coast:
        return bbox
    merged = linemerge(unary_union(coast))
    lines = [merged] if isinstance(merged, LineString) else list(merged.geoms)
    clipped = [line.intersection(bbox) for line in lines]
    parts = []
    for c in clipped:
        if c.is_empty:
            continue
        parts.extend([c] if isinstance(c, LineString) else list(getattr(c, "geoms", [])))
    faces = list(polygonize(unary_union([*parts, bbox.boundary])))
    land = []
    for face in faces:
        vote = 0
        for seg_line in parts:
            if not isinstance(seg_line, LineString) or not face.boundary.intersects(seg_line):
                continue
            coords = list(seg_line.coords)
            for a, b in zip(coords, coords[1:], strict=False):
                mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
                if face.boundary.distance(Point(mid)) > 1e-7:
                    continue
                dx, dy = b[0] - a[0], b[1] - a[1]
                norm = (dx * dx + dy * dy) ** 0.5 or 1
                eps = 2e-6
                left = Point(mid[0] - dy / norm * eps, mid[1] + dx / norm * eps)
                right = Point(mid[0] + dy / norm * eps, mid[1] - dx / norm * eps)
                if face.contains(left):
                    vote += 1
                elif face.contains(right):
                    vote -= 1
                break
        if vote > 0:
            land.append(face)
    return unary_union(land) if land else Polygon()


def to_px(geom):
    return transform(lambda x, y, z=None: frame.project(x, y), geom)


def rings(geom, tolerance: float) -> list[list[list[float]]]:
    """Polygon rings (outer then holes), in frame pixels, rounded."""
    if geom.is_empty:
        return []
    geom = to_px(geom).simplify(tolerance, preserve_topology=True)
    polys = [geom] if isinstance(geom, Polygon) else list(getattr(geom, "geoms", []))
    out = []
    for poly in polys:
        if not isinstance(poly, Polygon) or poly.area < 4:
            continue
        for ring in [poly.exterior, *poly.interiors]:
            out.append([[round(x, 1), round(y, 1)] for x, y in ring.coords])
    return out


def lines(geoms, tolerance: float, clip) -> list[list[list[float]]]:
    out = []
    for g in geoms:
        g = g.intersection(clip)
        if g.is_empty:
            continue
        g = to_px(g).simplify(tolerance)
        parts = [g] if isinstance(g, LineString) else list(getattr(g, "geoms", []))
        for p in parts:
            if isinstance(p, LineString) and len(p.coords) >= 2:
                out.append([[round(x, 1), round(y, 1)] for x, y in p.coords])
    return out


def main() -> None:
    source, target = sys.argv[1], sys.argv[2]
    data = collect(source)
    pad = 0.01
    clip = box(frame.WEST - pad, frame.SOUTH - pad, frame.EAST + pad, frame.NORTH + pad)
    land = land_from_coast(data.coast, clip)
    area = lambda gs: unary_union([g.buffer(0) for g in gs]).intersection(clip)  # noqa: E731
    result = {
        "frame": {"width": frame.WIDTH, "height": frame.HEIGHT, "zoom": frame.ZOOM},
        "land": rings(land, 0.3),
        "water": rings(area(data.water), 0.3),
        "forest": rings(area(data.forest), 0.4),
        "green": rings(area(data.green), 0.4),
        "sand": rings(area(data.sand), 0.4),
        "industrial": rings(area(data.industrial), 0.4),
        "airport": rings(area(data.airport), 0.4),
        "runways": lines(data.runways, 0.3, clip),
        "rail": lines(data.rail, 0.3, clip),
        "ferry": lines(data.ferry, 0.3, clip),
        "rivers": lines(data.rivers, 0.3, clip),
        "roads": {cls: lines(gs, 0.25, clip) for cls, gs in data.roads.items()},
        "places": [],
        "pois": [],
        "road_names": [],
    }
    for p in data.places:
        x, y = frame.project(p["lon"], p["lat"])
        if 0 <= x <= frame.WIDTH and 0 <= y <= frame.HEIGHT:
            result["places"].append(
                {"name": p["name"], "place": p["place"], "x": round(x, 1), "y": round(y, 1)}
            )
    seen = set()
    for p in data.pois:
        x, y = frame.project(p["lon"], p["lat"])
        key = (p["name"], round(x), round(y))
        if key in seen or not (0 <= x <= frame.WIDTH and 0 <= y <= frame.HEIGHT):
            continue
        seen.add(key)
        result["pois"].append(
            {
                "name": p["name"],
                "kind": p["kind"],
                "x": round(x, 1),
                "y": round(y, 1),
                "lon": round(p["lon"], 6),
                "lat": round(p["lat"], 6),
            }
        )
    lengths: dict[tuple[str, str], float] = defaultdict(float)
    for cls, name, line in data.road_names:
        lengths[(cls, name)] += to_px(line).length
    result["road_names"] = [
        {"class": cls, "name": name, "length": round(length)}
        for (cls, name), length in sorted(lengths.items(), key=lambda kv: -kv[1])
    ]
    with open(target, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, separators=(",", ":"))
    counts = {k: len(v) for k, v in result.items() if isinstance(v, list)}
    counts["roads"] = {k: len(v) for k, v in result["roads"].items()}
    print(json.dumps(counts, ensure_ascii=False))


if __name__ == "__main__":
    main()

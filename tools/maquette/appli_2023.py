"""Données d'Abidjan pour l'APK de test yafohi : lignes de 2023 et vrai moteur, hors ligne.

Usage :
  python appli_2023.py <gtfs.zip> <pack réel> <couches.json> <carte-yafohi.svg> <polices> <sortie>

Produit, au format de l'appli Flutter (assets/<sortie>) :
  city.json   arrêts et lignes du GTFS 2023, lieux d'OpenStreetMap, position de démo ;
  map.json    tracés des lignes (GeoJSON) et quarts du fond de carte avec leurs coins ;
  carte/      le fond yafohi en quatre JPEG (moins de 4 096 px de côté chacun), noms des
              quartiers inclus, la carte embarquée n'ayant pas de glyphes ;
  pack/       le pack du moteur : GTFS 2023 (noms de lignes nettoyés) et graphe piéton.

Évaluation interne seulement (H-030) : le GTFS 2023 est sous licence CC BY-NC 4.0 et
l'appli affiche « Lignes de 2023 · à confirmer ». Les prix et les attentes observées
manquent : le moteur l'indique.
"""

from __future__ import annotations

import csv
import io
import json
import math
import os
import shutil
import subprocess
import sys
import uuid
import zipfile
from pathlib import Path

import frame
from PIL import Image

NAMESPACE = uuid.UUID("6f1b3c1e-6a55-4a8e-9c1a-2f9d1e7c0a11")
HOME = (533.4, 1287.8)  # Toits-Rouges, Yopougon (frame pixels)
COMMUNES = {
    "yopougon": "Yopougon",
    "attecoube": "Attécoubé",
    "adjame": "Adjamé",
    "plateau": "Le Plateau",
    "cocody": "Cocody",
    "treichville": "Treichville",
    "marcory": "Marcory",
    "koumassi": "Koumassi",
    "port-bouet": "Port-Bouët",
    "abobo": "Abobo",
}
POI_CATEGORY = {
    "marche": "marche",
    "universite": "ecole",
    "hopital": "sante",
    "centre_commercial": "commerce",
    "gare": "gare",
    "embarcadere": "gare",
}
GTFS_FILES = (
    "agency.txt",
    "calendar.txt",
    "calendar_dates.txt",
    "feed_info.txt",
    "frequencies.txt",
    "routes.txt",
    "shapes.txt",
    "stop_times.txt",
    "stops.txt",
    "trips.txt",
)
MODE_COLOR = {"gbaka": "13855A", "woro_communal": "BF5A00", "woro_intercommunal": "8A4A00"}


def ident(kind: str, code: str) -> str:
    return str(uuid.uuid5(NAMESPACE, f"{kind}:{code}"))


def mode_of(agency: str) -> str:
    if agency.lower().startswith("gbaka"):
        return "gbaka"
    return "woro_intercommunal" if "banalis" in agency.lower() else "woro_communal"


def clean_name(long_name: str) -> str:
    """« woro woro banalisé : A ↔ B » → « A ↔ B »."""
    return long_name.partition(" : ")[2].strip() or long_name.strip()


def read(z: zipfile.ZipFile, name: str) -> list[dict]:
    return list(csv.DictReader(io.TextIOWrapper(z.open(name), encoding="utf-8-sig")))


def lonlat(x: float, y: float) -> tuple[float, float]:
    lon, lat = frame.unproject(x, y)
    return round(lon, 6), round(lat, 6)


def simplify(points: list[tuple[float, float]], tolerance: float) -> list[tuple[float, float]]:
    if len(points) < 3:
        return points
    keep = [False] * len(points)
    keep[0] = keep[-1] = True
    stack = [(0, len(points) - 1)]
    while stack:
        a, b = stack.pop()
        (ax, ay), (bx, by) = points[a], points[b]
        norm = math.hypot(bx - ax, by - ay) or 1e-12
        best, index = 0.0, -1
        for i in range(a + 1, b):
            px, py = points[i]
            d = abs((by - ay) * (px - ax) - (bx - ax) * (py - ay)) / norm
            if d > best:
                best, index = d, i
        if best > tolerance and index > 0:
            keep[index] = True
            stack += [(a, index), (index, b)]
    return [p for p, k in zip(points, keep, strict=True) if k]


def render_map(svg_path: Path, layers: dict, fonts: Path, out: Path) -> list[dict]:
    """Yafohi background with district names, cut in four JPEG quarters."""
    svg = svg_path.read_text(encoding="utf-8").rsplit("</svg>", 1)[0]
    labels = []
    big = {
        "Yopougon",
        "Attécoubé",
        "Adjamé",
        "Le Plateau",
        "Cocody",
        "Treichville",
        "Marcory",
        "Koumassi",
        "Port-Bouët",
        "Abobo",
    }
    taken: list[tuple[float, float, float]] = []

    def place(name: str, x: float, y: float, size: float, style: str) -> None:
        half = len(name) * size * 0.33
        if any(abs(x - tx) < half + tw and abs(y - ty) < size * 1.6 for tx, ty, tw in taken):
            return
        taken.append((x, y, half))
        labels.append(
            f'<text x="{x:.1f}" y="{y:.1f}" class="{style}" font-size="{size}">{name}</text>'
        )

    places = layers["places"]
    for p in places:
        if p["name"] in big and p["place"] in ("suburb", "city", "town"):
            place(p["name"].upper(), p["x"], p["y"], 15, "q")
    for name, x, y, style in (
        ("Lagune Ébrié", 470, 1560, "w"),
        ("Baie du Banco", 725, 1345, "w"),
        ("Parc national du Banco", 555, 640, "f"),
    ):
        place(name, x, y, 13, style)
    for p in sorted(places, key=lambda p: (p["place"] != "suburb", p["name"])):
        if p["place"] in ("suburb", "quarter") and p["name"] not in big:
            place(p["name"], p["x"], p["y"], 11.5, "s")
    style = (
        f'<style>@font-face{{font-family:N;src:url("file://{fonts}/Nunito-800.ttf")}}'
        "text{font-family:N;text-anchor:middle;dominant-baseline:middle;paint-order:stroke;"
        "stroke:#FBF6EC;stroke-width:3.2px;stroke-linejoin:round}"
        ".q{fill:#5A4E3C;letter-spacing:.08em}.s{fill:#7A6D58}"
        ".w{fill:#2F7F75;font-style:italic}.f{fill:#4E7B33;font-style:italic}</style>"
    )
    html = out / "carte.html"
    html.write_text(
        f'<html><head><meta charset="utf-8"></head><body style="margin:0">'
        f"{svg}{style}{''.join(labels)}</svg></body></html>",
        encoding="utf-8",
    )
    png = out / "carte.png"
    script = (
        "const { chromium } = require('playwright');(async () => {"
        "const b = await chromium.launch();"
        "const p = await b.newPage({ viewport: "
        f"{{ width: {frame.WIDTH}, height: {frame.HEIGHT} }}, deviceScaleFactor: 2 }});"
        f"await p.goto('file://{html}'); await p.waitForTimeout(500);"
        f"await p.screenshot({{ path: '{png}' }}); await b.close(); }})();"
    )
    env = {**os.environ, "NODE_PATH": subprocess.check_output(["npm", "root", "-g"], text=True)}
    env["NODE_PATH"] = env["NODE_PATH"].strip()
    subprocess.run(["node", "-e", script], check=True, env=env)
    image = Image.open(png).convert("RGB")
    html.unlink()
    png.unlink()
    w, h = image.size
    quarters = []
    for qy in range(2):
        for qx in range(2):
            x0, x1 = qx * w // 2, (qx + 1) * w // 2
            y0, y1 = qy * h // 2, (qy + 1) * h // 2
            name = f"q{qy}{qx}.jpg"
            image.crop((x0, y0, x1, y1)).save(out / name, "JPEG", quality=84, optimize=True)
            fx0, fx1, fy0, fy1 = x0 / 2, x1 / 2, y0 / 2, y1 / 2
            quarters.append(
                {
                    "file": name,
                    "coordinates": [
                        lonlat(fx0, fy0),
                        lonlat(fx1, fy0),
                        lonlat(fx1, fy1),
                        lonlat(fx0, fy1),
                    ],
                }
            )
    return quarters


def main() -> None:
    gtfs_zip, pack, layers_path, svg, fonts, out = map(Path, sys.argv[1:7])
    layers = json.loads(layers_path.read_text(encoding="utf-8"))
    for old in ("pack", "carte"):  # README.md stays
        shutil.rmtree(out / old, ignore_errors=True)
    (out / "pack" / "gtfs").mkdir(parents=True)
    (out / "carte").mkdir()

    z = zipfile.ZipFile(gtfs_zip)
    agencies = {a["agency_id"]: a["agency_name"] for a in read(z, "agency.txt")}
    routes = read(z, "routes.txt")
    mode = {r["route_id"]: mode_of(agencies.get(r["agency_id"], r["agency_id"])) for r in routes}

    # Pack: the 2023 GTFS with clean line names, and the walking graph.
    for name in GTFS_FILES:
        rows = read(z, name)
        if name == "routes.txt":
            for r in rows:
                r["route_long_name"] = clean_name(r["route_long_name"])
                r["route_color"] = MODE_COLOR[mode[r["route_id"]]]
        with open(out / "pack" / "gtfs" / name, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(
                f, fieldnames=list(rows[0].keys()) if rows else [], lineterminator="\n"
            )
            writer.writeheader()
            writer.writerows(rows)
    for name in ("walk_nodes.csv", "walk_edges.csv"):
        shutil.copy(pack / name, out / "pack" / name)
    meta = json.loads((pack / "pack.json").read_text(encoding="utf-8"))
    (out / "pack" / "pack.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # Stops and lines inside the map frame.
    stops = {s["stop_id"]: s for s in read(z, "stops.txt")}
    trips = read(z, "trips.txt")
    served: dict[str, set[str]] = {}
    first_last: dict[str, tuple[str, str]] = {}
    by_trip: dict[str, list[tuple[int, str]]] = {}
    for row in read(z, "stop_times.txt"):
        by_trip.setdefault(row["trip_id"], []).append((int(row["stop_sequence"]), row["stop_id"]))
    for t in trips:
        seq = [s for _, s in sorted(by_trip.get(t["trip_id"], []))]
        for s in seq:
            served.setdefault(s, set()).add(t["route_id"])
        if seq:
            first_last.setdefault(t["route_id"], (seq[0], seq[-1]))
    communes = {
        code: next((p["x"], p["y"]) for p in layers["places"] if p["name"] == name)
        for code, name in COMMUNES.items()
    }

    def area_of(x: float, y: float) -> str:
        return min(communes, key=lambda c: math.dist(communes[c], (x, y)))

    city_stops = []
    for sid, s in stops.items():
        x, y = frame.project(float(s["stop_lon"]), float(s["stop_lat"]))
        if not (0 <= x <= frame.WIDTH and 0 <= y <= frame.HEIGHT) or sid not in served:
            continue
        name = s["stop_name"].strip() or "Arrêt sans nom"
        city_stops.append(
            {
                "code": sid,
                "id": ident("stop", sid),
                "name": name,
                "kind": "gare_artisanale" if name.lower().startswith("gare") else "arret_informel",
                "lat": round(float(s["stop_lat"]), 6),
                "lon": round(float(s["stop_lon"]), 6),
                "area": area_of(x, y),
                "aliases": [],
                "lighting": "inconnu",
                "lines": sorted(served[sid]),
                "hours": ["05:00", "22:00"],
            }
        )
    kept_codes = {s["code"] for s in city_stops}
    city_lines = []
    for r in routes:
        rid = r["route_id"]
        if not any(rid in served.get(code, ()) for code in kept_codes):
            continue
        ends = first_last.get(rid, ("", ""))
        city_lines.append(
            {
                "code": rid,
                "id": ident("line", rid),
                "short_name": "",
                "long_name": clean_name(r["route_long_name"]),
                "mode": mode[rid],
                "network": mode[rid],
                "color": MODE_COLOR[mode[rid]],
                "text_color": "FFFFFF",
                "body_color": "",
                "color_pattern": None,
                "announced_as": None,
                "terminals": [e for e in ends if e in kept_codes],
            }
        )
    places = []
    seen = set()
    for p in layers["pois"]:
        cat = POI_CATEGORY.get(p["kind"])
        key = (p["name"], round(p["x"] / 30), round(p["y"] / 30))
        if not cat or key in seen:
            continue
        seen.add(key)
        lon, lat = lonlat(p["x"], p["y"])
        places.append(
            {
                "code": f"osm-{len(places)}",
                "name": p["name"],
                "category": cat,
                "lat": lat,
                "lon": lon,
                "aliases": [],
            }
        )
    for p in layers["places"]:
        if p["place"] in ("suburb", "quarter", "neighbourhood"):
            lon, lat = lonlat(p["x"], p["y"])
            places.append(
                {
                    "code": f"osm-{len(places)}",
                    "name": p["name"],
                    "category": "quartier",
                    "lat": lat,
                    "lon": lon,
                    "aliases": [],
                }
            )
    west, north = lonlat(0, 0)
    east, south = lonlat(frame.WIDTH, frame.HEIGHT)
    home_lon, home_lat = lonlat(*HOME)
    city = {
        "city": {
            "areas": COMMUNES,
            "bbox": [west, south, east, north],
            "code": "abidjan",
            "day_types": ["ouvrable", "samedi", "dimanche"],
            "id": ident("city", "abidjan"),
            "is_fictional": False,
            "name": "Abidjan",
            "network_version": meta["network_version"],
        },
        "fares": [],
        "lines": city_lines,
        "places": places,
        "position": {"lat": home_lat, "lon": home_lon},
        "stops": city_stops,
        "waits": [],
    }
    (out / "city.json").write_text(
        json.dumps(city, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
    )

    # Map: line shapes as GeoJSON, background quarters.
    shapes: dict[str, list[tuple[int, float, float]]] = {}
    for row in read(z, "shapes.txt"):
        shapes.setdefault(row["shape_id"], []).append(
            (int(row["shape_pt_sequence"]), float(row["shape_pt_lon"]), float(row["shape_pt_lat"]))
        )
    shape_of = {}
    for t in trips:
        shape_of.setdefault(t["route_id"], t["shape_id"])
    features = []
    for line in city_lines:
        pts = [(lon, lat) for _, lon, lat in sorted(shapes.get(shape_of.get(line["code"]), []))]
        pts = simplify(pts, 0.00008)
        if len(pts) < 2:
            continue
        features.append(
            {
                "type": "Feature",
                "properties": {
                    "line": line["code"],
                    "color": "#" + line["color"],
                    "short_name": "",
                },
                "geometry": {
                    "type": "LineString",
                    "coordinates": [[round(a, 5), round(b, 5)] for a, b in pts],
                },
            }
        )
    quarters = render_map(svg, layers, fonts, out / "carte")
    map_json = {
        "lines": {"type": "FeatureCollection", "features": features},
        "roads": {"type": "FeatureCollection", "features": []},
        "background": {"color": "#FBF6EC", "images": quarters},
    }
    (out / "map.json").write_text(
        json.dumps(map_json, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
    )
    print(
        len(city_stops),
        "arrêts,",
        len(city_lines),
        "lignes,",
        len(places),
        "lieux,",
        len(features),
        "tracés",
    )


if __name__ == "__main__":
    main()

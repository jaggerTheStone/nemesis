"""Selects the origin-destination pairs of the routing spike (I0.8) from a GTFS feed.

Nothing is invented: origins and destinations are real stops of the feed. The pilot
corridor is not chosen yet (porteur decision), so the pairs span the network:
- « pôles » are the stops where most trips start or end, merged within 300 m;
- pairs between pôles are spread over three distance bands;
- « bord de route » pairs start on the route itself, halfway between two stops that
  are more than 800 m apart, on the shape of the trip: they test boarding between
  stops (continuous pickup, partie 8.1).

Usage: python -I select_pairs.py <gtfs.zip> <out.csv>
The selection is deterministic: same feed, same pairs.
"""

from __future__ import annotations

import collections
import csv
import io
import math
import sys
import zipfile
from pathlib import Path

HUB_MERGE_M = 300.0
TOP_HUBS = 24
BANDS = (
    ("court", 2_000.0, 5_000.0, 5),
    ("moyen", 5_000.0, 10_000.0, 8),
    ("long", 10_000.0, 40_000.0, 7),
)
MAX_USES_PER_HUB = 2
ROADSIDE_PAIRS = 5
ROADSIDE_MIN_GAP_M = 800.0


def distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * 6_371_000 * math.asin(math.sqrt(a))


def read(archive: zipfile.ZipFile, name: str) -> list[dict[str, str]]:
    return list(csv.DictReader(io.StringIO(archive.read(name).decode("utf-8-sig"))))


def hubs(stops: dict[str, dict[str, str]], stop_times: list[dict[str, str]]) -> list[dict]:
    by_trip: dict[str, list[tuple[int, str]]] = collections.defaultdict(list)
    for row in stop_times:
        by_trip[row["trip_id"]].append((int(row["stop_sequence"]), row["stop_id"]))
    terminals: collections.Counter[str] = collections.Counter()
    for sequence in by_trip.values():
        sequence.sort()
        terminals[sequence[0][1]] += 1
        terminals[sequence[-1][1]] += 1
    merged: list[dict] = []
    for stop_id, count in sorted(terminals.items(), key=lambda item: (-item[1], item[0])):
        stop = stops[stop_id]
        lat, lon = float(stop["stop_lat"]), float(stop["stop_lon"])
        near = next(
            (h for h in merged if distance_m(h["lat"], h["lon"], lat, lon) <= HUB_MERGE_M), None
        )
        if near:
            near["trips"] += count
        else:
            merged.append(
                {
                    "stop_id": stop_id,
                    "name": stop["stop_name"],
                    "lat": lat,
                    "lon": lon,
                    "trips": count,
                }
            )
    merged.sort(key=lambda h: (-h["trips"], h["stop_id"]))
    return merged[:TOP_HUBS]


def hub_pairs(selected_hubs: list[dict]) -> list[dict]:
    uses: collections.Counter[str] = collections.Counter()
    pairs = []
    for band, low, high, quota in BANDS:
        candidates = []
        for i, a in enumerate(selected_hubs):
            for b in selected_hubs[i + 1 :]:
                d = distance_m(a["lat"], a["lon"], b["lat"], b["lon"])
                if low <= d < high:
                    candidates.append(
                        (-(a["trips"] + b["trips"]), a["stop_id"], b["stop_id"], a, b, d)
                    )
        candidates.sort(key=lambda c: c[:3])
        taken = 0
        for _, _, _, a, b, d in candidates:
            if taken == quota:
                break
            if uses[a["stop_id"]] >= MAX_USES_PER_HUB or uses[b["stop_id"]] >= MAX_USES_PER_HUB:
                continue
            uses[a["stop_id"]] += 1
            uses[b["stop_id"]] += 1
            taken += 1
            pairs.append({"band": band, "origin": a, "destination": b, "distance_m": d})
    return pairs


def roadside_pairs(
    archive: zipfile.ZipFile, stops: dict[str, dict[str, str]], selected_hubs: list[dict]
) -> list[dict]:
    """Origins halfway along a long inter-stop gap, on the trip's shape; destination: a hub."""
    shapes: dict[str, list[tuple[int, float, float]]] = collections.defaultdict(list)
    for row in read(archive, "shapes.txt"):
        shapes[row["shape_id"]].append(
            (int(row["shape_pt_sequence"]), float(row["shape_pt_lat"]), float(row["shape_pt_lon"]))
        )
    by_trip: dict[str, list[tuple[int, str]]] = collections.defaultdict(list)
    for row in read(archive, "stop_times.txt"):
        by_trip[row["trip_id"]].append((int(row["stop_sequence"]), row["stop_id"]))
    gaps = []
    for trip in sorted(read(archive, "trips.txt"), key=lambda t: t["trip_id"]):
        sequence = sorted(by_trip[trip["trip_id"]])
        points = sorted(shapes.get(trip["shape_id"], []))
        if not points:
            continue
        for (_, a), (_, b) in zip(sequence, sequence[1:], strict=False):
            sa, sb = stops[a], stops[b]
            gap = distance_m(
                float(sa["stop_lat"]),
                float(sa["stop_lon"]),
                float(sb["stop_lat"]),
                float(sb["stop_lon"]),
            )
            if gap > ROADSIDE_MIN_GAP_M:
                mid_lat = (float(sa["stop_lat"]) + float(sb["stop_lat"])) / 2
                mid_lon = (float(sa["stop_lon"]) + float(sb["stop_lon"])) / 2
                # The shape point nearest to the midpoint: a point on the road itself.
                _, lat, lon = min(points, key=lambda p: distance_m(p[1], p[2], mid_lat, mid_lon))
                gaps.append((-gap, trip["trip_id"], a, b, lat, lon))
    gaps.sort()
    pairs, used_trips = [], set()
    for _, trip_id, a, b, lat, lon in gaps:
        if len(pairs) == ROADSIDE_PAIRS:
            break
        if trip_id in used_trips:
            continue
        # Destination: the hub farthest from the origin among the top hubs, for a real trip.
        destination = max(
            selected_hubs, key=lambda h: (distance_m(lat, lon, h["lat"], h["lon"]), h["stop_id"])
        )
        distance = distance_m(lat, lon, destination["lat"], destination["lon"])
        if distance > 25_000:
            destination = min(
                (h for h in selected_hubs if distance_m(lat, lon, h["lat"], h["lon"]) >= 5_000),
                key=lambda h: (distance_m(lat, lon, h["lat"], h["lon"]), h["stop_id"]),
            )
        used_trips.add(trip_id)
        origin = {
            "stop_id": "",
            "name": f"Bord de route entre {stops[a]['stop_name']} et {stops[b]['stop_name']}",
            "lat": lat,
            "lon": lon,
        }
        pairs.append(
            {
                "band": "bord_de_route",
                "origin": origin,
                "destination": destination,
                "distance_m": distance_m(lat, lon, destination["lat"], destination["lon"]),
            }
        )
    return pairs


def main(argv: list[str]) -> int:
    source, target = Path(argv[1]), Path(argv[2])
    with zipfile.ZipFile(source) as archive:
        stops = {s["stop_id"]: s for s in read(archive, "stops.txt")}
        selected = hubs(stops, read(archive, "stop_times.txt"))
        pairs = hub_pairs(selected) + roadside_pairs(archive, stops, selected)
    with target.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(
            [
                "pair_id",
                "band",
                "origin_stop_id",
                "origin_name",
                "origin_lat",
                "origin_lon",
                "destination_stop_id",
                "destination_name",
                "destination_lat",
                "destination_lon",
                "distance_m",
            ]
        )
        for index, pair in enumerate(pairs, start=1):
            o, d = pair["origin"], pair["destination"]
            writer.writerow(
                [
                    f"OD{index:02d}",
                    pair["band"],
                    o["stop_id"],
                    o["name"],
                    f"{o['lat']:.6f}",
                    f"{o['lon']:.6f}",
                    d["stop_id"],
                    d["name"],
                    f"{d['lat']:.6f}",
                    f"{d['lon']:.6f}",
                    round(pair["distance_m"]),
                ]
            )
    print(f"{len(pairs)} couples écrits dans {target}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

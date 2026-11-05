"""Compares options A (OpenTripPlanner) and B (frequency RAPTOR) of the spike (I0.8).

Both engines' itineraries are re-scored with one cost function, so that only the
search differs:
- walking: straight line × 1,3 at 4,5 km/h between the ends of each walking leg;
- boarding: régime B median wait, ln 2 × headway of the band (ALGORITHMES.md 1.3),
  optionally multiplied per stop and line by the simulated live factor of `--seed`
  (the same hash as routing_core::wait::SimulatedLive);
- riding: GTFS offsets between the boarding and alighting stops of the trip.

The question asked is the one of ADR-003: when the live wait changes, does
re-scoring OpenTripPlanner's candidates find as good a journey as an engine that
puts the wait in the search itself?

Usage: python -I compare.py --gtfs <dir> --otp otp.json --b-base b.json --b-sim b-sim.json
       --seed 2026 [--b-virtual b-virtuels.json] --out-json c.json --out-md c.md
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

WALK_SPEED = 4.5 / 3.6
DETOUR = 1.3
GAIN_THRESHOLD_S = 5 * 60


def distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * 6_371_000 * math.asin(math.sqrt(a))


def walk_seconds(straight_m: float) -> int:
    return math.ceil(straight_m * DETOUR / WALK_SPEED)


def factor(seed: int, stop_id: str, route_id: str) -> float:
    """Simulated live factor, identical to SimulatedLive::factor in Rust."""
    value = 0xCBF29CE484222325
    for byte in f"{seed}|{stop_id}|{route_id}".encode():
        value ^= byte
        value = (value * 0x100000001B3) & 0xFFFFFFFFFFFFFFFF
    return 0.5 + 2.5 * ((value >> 11) / float(1 << 53))


def seconds(clock: str) -> int:
    h, m, *s = (int(x) for x in clock.split(":"))
    return h * 3600 + m * 60 + (s[0] if s else 0)


class Gtfs:
    """Trips of the feed: ordered stops, offsets and bands, as the Rust reader sees them."""

    def __init__(self, directory: Path) -> None:
        def read(name: str) -> list[dict[str, str]]:
            with (directory / name).open(encoding="utf-8-sig") as handle:
                return list(csv.DictReader(handle))

        rows: dict[str, list[tuple[int, str, int, int]]] = defaultdict(list)
        for r in read("stop_times.txt"):
            arrival = seconds(r["arrival_time"] or r["departure_time"])
            departure = seconds(r["departure_time"] or r["arrival_time"])
            rows[r["trip_id"]].append((int(r["stop_sequence"]), r["stop_id"], arrival, departure))
        self.trips: dict[str, dict[str, Any]] = {}
        for trip_id, sequence in rows.items():
            sequence.sort()
            first = sequence[0][3]
            self.trips[trip_id] = {
                "stops": [s[1] for s in sequence],
                "arr": [s[2] - first for s in sequence],
                "dep": [max(s[3], s[2]) - first for s in sequence],
                "bands": [],
            }
        for r in read("frequencies.txt"):
            if r["trip_id"] in self.trips:
                self.trips[r["trip_id"]]["bands"].append(
                    (seconds(r["start_time"]), seconds(r["end_time"]), int(r["headway_secs"]))
                )
        self.route_of = {t["trip_id"]: t["route_id"] for t in read("trips.txt")}

    def ride(self, trip_id: str, board: str, alight: str, at: int, seed: int | None) -> int | None:
        """Arrival at `alight` when reaching `board` at `at`, or None if impossible."""
        trip = self.trips.get(trip_id)
        if trip is None or board not in trip["stops"]:
            return None
        b = trip["stops"].index(board)
        try:
            a = trip["stops"].index(alight, b + 1)
        except ValueError:
            return None
        first = at - trip["dep"][b]
        headway = next((h for s, e, h in trip["bands"] if s <= first < e), None)
        if headway is None:
            return None
        wait = round(math.log(2) * headway)
        if seed is not None:
            wait = round(wait * factor(seed, board, self.route_of[trip_id]))
        return at + wait + trip["arr"][a] - trip["dep"][b]


def strip_feed(gtfs_id: str | None) -> str:
    return gtfs_id.split(":", 1)[1] if gtfs_id and ":" in gtfs_id else (gtfs_id or "")


def otp_legs(itinerary: dict[str, Any]) -> list[dict[str, Any]]:
    legs = []
    for leg in itinerary["legs"]:
        if leg["mode"] == "WALK":
            legs.append(
                {
                    "type": "walk",
                    "from": (leg["from"]["lat"], leg["from"]["lon"]),
                    "to": (leg["to"]["lat"], leg["to"]["lon"]),
                }
            )
        else:
            legs.append(
                {
                    "type": "ride",
                    "trip_id": strip_feed((leg.get("trip") or {}).get("gtfsId")),
                    "board": strip_feed((leg["from"].get("stop") or {}).get("gtfsId")),
                    "alight": strip_feed((leg["to"].get("stop") or {}).get("gtfsId")),
                    "route": (leg.get("route") or {}).get("longName")
                    or (leg.get("route") or {}).get("shortName"),
                }
            )
    return legs


def b_legs(journey: dict[str, Any]) -> list[dict[str, Any]]:
    legs = []
    for leg in journey["legs"]:
        if leg["type"] == "walk":
            legs.append(
                {
                    "type": "walk",
                    "from": (leg["from"]["lat"], leg["from"]["lon"]),
                    "to": (leg["to"]["lat"], leg["to"]["lon"]),
                }
            )
        else:
            legs.append(
                {
                    "type": "ride",
                    "trip_id": leg["trip_id"],
                    "board": leg["board"]["stop_id"],
                    "alight": leg["alight"]["stop_id"],
                    "route": leg["route_name"],
                }
            )
    return legs


def rescore(gtfs: Gtfs, legs: list[dict[str, Any]], depart: int, seed: int | None) -> int | None:
    clock = depart
    for leg in legs:
        if leg["type"] == "walk":
            clock += walk_seconds(distance_m(*leg["from"], *leg["to"]))
        else:
            arrival = gtfs.ride(leg["trip_id"], leg["board"], leg["alight"], clock, seed)
            if arrival is None:
                return None
            clock = arrival
    return clock


def best(
    gtfs: Gtfs, candidates: list[list[dict[str, Any]]], depart: int, seed: int | None
) -> int | None:
    scores = [
        s for s in (rescore(gtfs, legs, depart, seed) for legs in candidates) if s is not None
    ]
    return min(scores) if scores else None


def index_b(report: dict[str, Any]) -> dict[tuple[str, str], list[list[dict[str, Any]]]]:
    return {
        (q["pair_id"], q["time"]): [b_legs(j) for j in q["journeys"] if j["rides"] > 0]
        for q in report["queries"]
    }


def compare(gtfs: Gtfs, otp: dict, b_base: dict, b_sim: dict, seed: int) -> dict[str, Any]:
    base, sim = index_b(b_base), index_b(b_sim)
    rows = []
    for q in otp["queries"]:
        key = (q["pair_id"], q["time"])
        depart = seconds(q["time"])
        a_candidates = [
            otp_legs(it)
            for it in q["itineraries"]
            if any(leg["mode"] != "WALK" for leg in it["legs"])
        ]
        routes = {
            tuple(leg["route"] for leg in legs if leg["type"] == "ride") for legs in a_candidates
        }
        row = {
            "pair_id": q["pair_id"],
            "band": q["band"],
            "time": q["time"],
            "a_itineraries": len(q["itineraries"]),
            "a_distinct": len(routes),
            "b_journeys": len(base.get(key, [])),
            "a_own_min": min((it["duration"] for it in q["itineraries"]), default=None),
            "a_median": best(gtfs, a_candidates, depart, None),
            "b_median": best(gtfs, base.get(key, []), depart, None),
            "a_live": best(gtfs, a_candidates, depart, seed),
            "b_base_live": best(gtfs, base.get(key, []), depart, seed),
            "b_live": best(gtfs, sim.get(key, []), depart, seed),
        }
        for name in ("a_median", "b_median", "a_live", "b_base_live", "b_live"):
            if row[name] is not None:
                row[name] -= depart
        rows.append(row)

    def gains(a: str, b: str) -> dict[str, Any]:
        pairs = [(r[a], r[b]) for r in rows if r[a] is not None and r[b] is not None]
        diffs = [x - y for x, y in pairs]
        return {
            "compared": len(pairs),
            "only_a": sum(1 for r in rows if r[a] is not None and r[b] is None),
            "only_b": sum(1 for r in rows if r[b] is not None and r[a] is None),
            "b_better_5min": sum(1 for d in diffs if d > GAIN_THRESHOLD_S),
            "a_better_5min": sum(1 for d in diffs if d < -GAIN_THRESHOLD_S),
            "median_gain_min": round(statistics.median(diffs) / 60, 1) if diffs else None,
            "max_gain_min": round(max(diffs) / 60, 1) if diffs else None,
        }

    return {
        "seed": seed,
        "rows": rows,
        "median_waits": gains("a_median", "b_median"),
        "live_waits": gains("a_live", "b_live"),
        "b_without_live_knowledge": gains("b_base_live", "b_live"),
    }


def self_check(gtfs: Gtfs, report: dict[str, Any], seed: int | None) -> int:
    """B's own arrivals must match the shared cost function: returns the mismatches."""
    mismatches = 0
    for q in report["queries"]:
        depart = seconds(q["time"])
        for journey in q["journeys"]:
            if (
                journey["rides"]
                and rescore(gtfs, b_legs(journey), depart, seed) != journey["arrive"]
            ):
                mismatches += 1
    return mismatches


def fr(value: float, digits: int = 1) -> str:
    """Number with a decimal comma."""
    return f"{value:.{digits}f}".replace(".", ",")


def fr_or_dash(value: float | None) -> str:
    return "—" if value is None else fr(value)


def minutes(value: int | None) -> str:
    return "—" if value is None else f"{round(value / 60)}"


def markdown(result: dict[str, Any], otp: dict, b_reports: dict[str, dict]) -> str:
    base = b_reports["base"]
    lines = [
        "# Spike du moteur d'itinéraires : comparaison des options A et B",
        "",
        "Mesures produites par le workflow « Spike du moteur d'itinéraires » (I0.8). GTFS « Abidjan"
        " 2023 » (évaluation interne, H-030) et extrait OSM d'Abidjan.",
        "",
        "## Performances",
        "",
        "| Mesure | A : OpenTripPlanner | B : RAPTOR à fréquences |"
        " B avec points de montée virtuels |",
        "|---|---|---|---|",
    ]
    virtual = b_reports.get("virtual")
    build = otp["build"]
    build_memory = (
        f"{build['peak_memory_mib']} Mio au plus" if build["peak_memory_mib"] else "non mesurée"
    )

    def b_cells(render: Any) -> str:
        return f"{render(base)} | {render(virtual) if virtual else '—'} |"

    def prep(r: dict) -> str:
        return f"{fr(r['read_ms'] + r['build_ms'], 0)} ms"

    def memory(r: dict) -> str:
        return f"{fr((r['peak_rss_kib'] or 0) / 1024, 0)} Mio"

    def speed(r: dict) -> str:
        return f"p50 {fr(r['latency_all']['p50_ms'])} ms ; p95 {fr(r['latency_all']['p95_ms'])} ms"

    def size(r: dict) -> str:
        n = r["network"]
        return f"{n['stops']} points dont {n['virtual_stops']} virtuels, {n['footpaths']} liaisons"

    otp_speed = f"{fr(otp['latency_p50_of_p50_ms'])} ms ; pire {fr(otp['latency_max_p50_ms'])} ms"
    lines += [
        f"| Préparation | graphe en {fr(build['seconds'])} s, {build_memory} | {b_cells(prep)}",
        f"| Mémoire en service | {otp['serve_peak_memory_mib']} Mio (JVM) | {b_cells(memory)}",
        f"| Latence par requête (médiane) | {otp_speed}, HTTP compris | {b_cells(speed)}",
        f"| Requêtes sans véhicule | {otp['queries_without_itinerary']} |"
        f" {b_cells(lambda r: r['queries_without_journey'])}",
        f"| Taille du réseau | — | {b_cells(size)}",
    ]
    lines += ["", "## Même fonction de coût pour les deux moteurs", ""]
    for key, title in (
        ("median_waits", "Attentes médianes du régime B (sans état en direct)"),
        (
            "live_waits",
            f"Attentes en direct simulées (graine {result['seed']}) : A réévalue ses candidats,"
            " B calcule avec",
        ),
        (
            "b_without_live_knowledge",
            "Effet de l'attente dans le calcul, à moteur égal : B sans puis avec"
            " les attentes simulées",
        ),
    ):
        g = result[key]
        lines += [
            f"**{title}** : {g['compared']} requêtes comparées.",
            f"- B meilleur de plus de 5 min : {g['b_better_5min']} ; A meilleur de plus de 5 min :"
            f" {g['a_better_5min']}.",
            f"- Gain médian de B : {fr_or_dash(g['median_gain_min'])} min ;"
            f" gain maximal : {fr_or_dash(g['max_gain_min'])} min.",
            f"- Seulement A : {g['only_a']} ; seulement B : {g['only_b']}.",
            "",
        ]
    lines += [
        "## Détail par requête (minutes, fonction de coût commune)",
        "",
        "| Couple | Classe | Heure | A : itinéraires (distincts) | B : options | A médian |"
        " B médian | A en direct | B en direct |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in result["rows"]:
        lines.append(
            f"| {r['pair_id']} | {r['band']} | {r['time']} |"
            f" {r['a_itineraries']} ({r['a_distinct']}) | {r['b_journeys']} |"
            f" {minutes(r['a_median'])} | {minutes(r['b_median'])} |"
            f" {minutes(r['a_live'])} | {minutes(r['b_live'])} |"
        )
    lines += ["", "## Construction du graphe d'OpenTripPlanner", ""]
    lines += [f"- {note}" for note in otp["build"]["notes"]]
    lines += [
        f"- Avertissement d'import `{k}` : {v}" for k, v in sorted(otp["build"]["issues"].items())
    ]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--gtfs", required=True, type=Path)
    parser.add_argument("--otp", required=True, type=Path)
    parser.add_argument("--b-base", required=True, type=Path)
    parser.add_argument("--b-sim", required=True, type=Path)
    parser.add_argument("--b-virtual", type=Path)
    parser.add_argument("--seed", required=True, type=int)
    parser.add_argument("--out-json", required=True, type=Path)
    parser.add_argument("--out-md", required=True, type=Path)
    args = parser.parse_args(argv)

    gtfs = Gtfs(args.gtfs)
    load = lambda p: json.loads(p.read_text(encoding="utf-8"))  # noqa: E731
    otp, b_base, b_sim = load(args.otp), load(args.b_base), load(args.b_sim)
    for name, report, seed in (("B médian", b_base, None), ("B en direct", b_sim, args.seed)):
        mismatches = self_check(gtfs, report, seed)
        if mismatches:
            raise SystemExit(
                f"{name} : {mismatches} trajets ne suivent pas la fonction de coût commune"
            )
    result = compare(gtfs, otp, b_base, b_sim, args.seed)
    reports = {"base": b_base}
    if args.b_virtual:
        reports["virtual"] = load(args.b_virtual)
    args.out_json.write_text(
        json.dumps(result, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )
    args.out_md.write_text(markdown(result, otp, reports), encoding="utf-8")
    for key in ("median_waits", "live_waits", "b_without_live_knowledge"):
        print(key, json.dumps(result[key], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())

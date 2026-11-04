"""Tests of the fictional fixtures generator (I0.5)."""

from __future__ import annotations

import csv
import io
import json
import math
from collections import defaultdict
from pathlib import Path

import pytest

from nemesis_pipelines.fixtures.city import CITY_BBOX, MODES, ROUTES, build_city
from nemesis_pipelines.fixtures.cli import GTFS_DIR, generated_files, main
from nemesis_pipelines.fixtures.gtfs import PUBLICATION_MIN_CONTRIBUTORS, gtfs_files
from nemesis_pipelines.fixtures.waits import gamma_quantile, regime_a_seconds, regime_b_seconds

REPO_ROOT = Path(__file__).resolve().parents[3]
FILES = gtfs_files(build_city())


def table(name: str) -> list[dict[str, str]]:
    return list(csv.DictReader(io.StringIO(FILES[name])))


def seconds(value: str) -> int:
    hours, minutes, secs = (int(part) for part in value.split(":"))
    return hours * 3600 + minutes * 60 + secs


# --- Generated files ------------------------------------------------------------------------


def test_generated_files_are_up_to_date() -> None:
    expected = generated_files()
    for relative, content in expected.items():
        assert (REPO_ROOT / relative).read_bytes().decode("utf-8") == content, (
            f"régénérer {relative}"
        )
    on_disk = {p.relative_to(REPO_ROOT) for p in (REPO_ROOT / GTFS_DIR).glob("*.txt")}
    assert on_disk == {p for p in expected if p.parent == GTFS_DIR}


def test_generation_is_deterministic() -> None:
    assert gtfs_files(build_city()) == FILES


# --- Content matches the plan (docs/PHASE-0.md, I0.5) ----------------------------------------


def test_city_matches_the_plan() -> None:
    stops = table("stops.txt")
    kinds = {row["stop_id"]: row["stop_kind"] for row in table("ext_stop_attributes.txt")}
    stations = [s for s in stops if kinds[s["stop_id"]] in ("gare_artisanale", "embarcadere")]
    assert len(table("areas.txt")) == 3
    assert len(stations) == 8
    assert len(table("routes.txt")) == 12
    modes = {route.mode for route in ROUTES}
    assert {"gbaka", "woro_communal", "woro_intercommunal", "bus_sotra", "bateau_bus"} <= modes
    assert len(table("trips.txt")) == 72


def test_every_record_is_fictional_and_inside_the_city() -> None:
    for name, content in FILES.items():
        rows = list(csv.DictReader(io.StringIO(content)))
        assert rows, name
        assert all(row["is_fictional"] == "1" for row in rows), name
    lon_min, lat_min, lon_max, lat_max = CITY_BBOX
    for stop in table("stops.txt"):
        assert stop["stop_name"].endswith("(fictif)")
        assert lon_min <= float(stop["stop_lon"]) <= lon_max
        assert lat_min <= float(stop["stop_lat"]) <= lat_max


# --- GTFS integrity (complements the MobilityData validator, run in CI) ----------------------


def test_references_between_files() -> None:
    routes = {r["route_id"] for r in table("routes.txt")}
    services = {c["service_id"] for c in table("calendar.txt")}
    stops = {s["stop_id"] for s in table("stops.txt")}
    trips = table("trips.txt")
    trip_ids = {t["trip_id"] for t in trips}
    shapes = {s["shape_id"] for s in table("shapes.txt")}
    assert {t["route_id"] for t in trips} <= routes
    assert {t["service_id"] for t in trips} <= services
    assert {t["shape_id"] for t in trips} == shapes
    used_stops = {st["stop_id"] for st in table("stop_times.txt")}
    assert used_stops == stops, "chaque arrêt doit être desservi"
    assert {st["trip_id"] for st in table("stop_times.txt")} == trip_ids
    assert {f["trip_id"] for f in table("frequencies.txt")} == trip_ids
    assert {sa["stop_id"] for sa in table("stop_areas.txt")} == stops
    areas = {a["area_id"] for a in table("areas.txt")}
    products = {p["fare_product_id"] for p in table("fare_products.txt")}
    networks = {r["network_id"] for r in table("routes.txt")}
    for rule in table("fare_leg_rules.txt"):
        assert rule["fare_product_id"] in products
        assert rule["network_id"] in networks
        assert {rule["from_area_id"], rule["to_area_id"]} <= areas | {""}
    for name in ("ext_stop_attributes.txt", "ext_stop_aliases.txt", "ext_wait_profiles.txt"):
        assert {row["stop_id"] for row in table(name)} <= stops, name
    for name in ("ext_route_appearance.txt", "ext_service_profiles.txt", "ext_fare_estimates.txt"):
        assert {row["route_id"] for row in table(name)} <= routes, name


def test_stop_times_and_shapes_progress() -> None:
    by_trip: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in table("stop_times.txt"):
        by_trip[row["trip_id"]].append(row)
    for trip, rows in by_trip.items():
        assert len(rows) >= 2, trip
        times = [seconds(r["departure_time"]) for r in rows]
        distances = [float(r["shape_dist_traveled"]) for r in rows]
        assert times == sorted(times) and distances == sorted(distances), trip
        assert [int(r["stop_sequence"]) for r in rows] == list(range(len(rows)))
    by_shape: dict[str, list[float]] = defaultdict(list)
    for row in table("shapes.txt"):
        by_shape[row["shape_id"]].append(float(row["shape_dist_traveled"]))
    for shape, distances in by_shape.items():
        assert distances == sorted(distances) and len(set(distances)) == len(distances), shape


def test_frequencies_do_not_overlap() -> None:
    by_trip: dict[str, list[tuple[int, int]]] = defaultdict(list)
    for row in table("frequencies.txt"):
        assert int(row["headway_secs"]) > 0 and row["exact_times"] == "0"
        by_trip[row["trip_id"]].append((seconds(row["start_time"]), seconds(row["end_time"])))
    for trip, bands in by_trip.items():
        for (_, end), (start, _) in zip(bands, bands[1:], strict=False):
            assert end <= start, trip


# --- Estimates follow the documented models ---------------------------------------------------


def test_wait_formulas_match_algorithmes_examples() -> None:
    assert gamma_quantile(3, 0.5) == pytest.approx(2.6741, abs=1e-3)
    assert gamma_quantile(3, 0.8) == pytest.approx(4.2790, abs=1e-3)
    assert gamma_quantile(5, 0.8) == pytest.approx(6.7210, abs=1e-3)
    # Regime B example of docs/ALGORITHMES.md: 12 vehicles per hour, q = 0.25.
    assert regime_b_seconds(300, 0.25) == (832, 1931)
    # Regime A example: r = 6, λp = 1.5 per minute, d0 = 0.
    p50, p80 = regime_a_seconds(6, 1.5, departure_delay_min=0)
    assert (round(p50 / 60, 1), round(p80 / 60, 1)) == (3.1, 4.5)


def test_published_wait_profiles_are_consistent() -> None:
    departs_when_full = {mode: values[3] for mode, values in MODES.items()}
    mode_of = {route.code: route.mode for route in ROUTES}
    for row in table("ext_wait_profiles.txt"):
        p50, p80 = int(row["wait_p50_s"]), int(row["wait_p80_s"])
        assert 0 < p50 <= p80
        assert int(row["n_obs"]) >= PUBLICATION_MIN_CONTRIBUTORS
        if row["regime"] == "A":
            assert departs_when_full[mode_of[row["route_id"]]]
        else:
            assert p80 / p50 == pytest.approx(math.log(5) / math.log(2), rel=0.01)


def test_fare_estimates_are_ordered_and_rounded() -> None:
    regie = {route.code for route in ROUTES if route.operator == "regie"}
    for row in table("ext_fare_estimates.txt"):
        p10, p50, p90 = int(row["fare_p10"]), int(row["fare_p50"]), int(row["fare_p90"])
        assert 0 < p10 <= p50 <= p90
        assert p10 % 50 == p50 % 50 == p90 % 50 == 0
        assert int(row["n_obs"]) >= PUBLICATION_MIN_CONTRIBUTORS
        if row["route_id"] in regie:
            assert p10 == p50 == p90


# --- Validator report summary -------------------------------------------------------------------


def test_report_check_fails_only_on_errors(tmp_path: Path) -> None:
    report = tmp_path / "report.json"
    report.write_text(
        json.dumps(
            {
                "notices": [
                    {"code": "unknown_file", "severity": "INFO", "totalNotices": 8},
                    {"code": "unknown_column", "severity": "INFO", "totalNotices": 21},
                ]
            }
        )
    )
    assert main(["verifier-rapport", str(report)]) == 0
    report.write_text(
        json.dumps({"notices": [{"code": "invalid_url", "severity": "ERROR", "totalNotices": 1}]})
    )
    assert main(["verifier-rapport", str(report)]) == 1

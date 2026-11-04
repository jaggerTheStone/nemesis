"""GTFS writer for the fictional city: GTFS Schedule, Fares v2 and the ext_ files (ADR-007)."""

from __future__ import annotations

import csv
import io

from nemesis_pipelines.fixtures.city import AREAS, OPERATORS, City, typical_fare

FEED_START = "20260101"
FEED_END = "20301231"
FEED_VERSION = "fixtures-fictives-1"
PRODUCED_AT = "2026-11-04T00:00:00Z"
VERIFIED_AT = "2026-11-01"
LAST_OBSERVED_AT = "2026-11-01T00:00:00Z"
PUBLICATION_MIN_CONTRIBUTORS = 20  # k ≥ 20 (partie 12.2, ADR-007)
CALENDAR = {
    "ouvrable": (1, 1, 1, 1, 1, 0, 0),
    "samedi": (0, 0, 0, 0, 0, 1, 0),
    "dimanche": (0, 0, 0, 0, 0, 0, 1),
}
URL = "https://example.org/nemesis/lagune-fictive"

Table = tuple[list[str], list[list[object]]]


def clock(seconds: int) -> str:
    return f"{seconds // 3600:02d}:{seconds % 3600 // 60:02d}:{seconds % 60:02d}"


def _csv(header: list[str], rows: list[list[object]]) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow([*header, "is_fictional"])
    for row in rows:
        writer.writerow([*("" if value is None else value for value in row), 1])
    return buffer.getvalue()


def gtfs_files(city: City) -> dict[str, str]:
    """File name → content of every file of the fictional GTFS feed."""
    tables: dict[str, Table] = {}
    stops = city.stops
    patterns = city.patterns

    tables["agency.txt"] = (
        ["agency_id", "agency_name", "agency_url", "agency_timezone", "agency_lang"],
        [
            [code, f"{name} (fictif)", f"{URL}/{code}", "Africa/Abidjan", "fr"]
            for code, name, _ in OPERATORS
        ],
    )
    tables["stops.txt"] = (
        ["stop_id", "stop_name", "stop_lat", "stop_lon", "location_type"],
        [[s.code, s.name, f"{s.lat:.6f}", f"{s.lon:.6f}", 0] for s in stops.values()],
    )
    tables["routes.txt"] = (
        [
            "route_id",
            "agency_id",
            "route_short_name",
            "route_long_name",
            "route_type",
            "route_color",
            "route_text_color",
            "continuous_pickup",
            "continuous_drop_off",
            "network_id",
        ],
        [
            [
                r.code,
                r.operator,
                r.short_name,
                f"{r.long_name} (fictif)",
                4 if r.mode == "bateau_bus" else 3,
                r.route_color,
                r.text_color,
                0 if r.operator == "artisanal" else 1,
                0 if r.operator == "artisanal" else 1,
                r.network,
            ]
            for r in city.routes
        ],
    )
    tables["calendar.txt"] = (
        [
            "service_id",
            "monday",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
            "saturday",
            "sunday",
            "start_date",
            "end_date",
        ],
        [[service, *days, FEED_START, FEED_END] for service, days in CALENDAR.items()],
    )

    trips, stop_times, frequencies, shapes = [], [], [], []
    for pattern in patterns:
        headsign = stops[pattern.stops[-1]].name
        for index, code in enumerate(pattern.stops):
            stop = stops[code]
            shapes.append(
                [
                    pattern.code,
                    f"{stop.lat:.6f}",
                    f"{stop.lon:.6f}",
                    index,
                    f"{pattern.distances_m[index]:.1f}",
                ]
            )
        for day_type in CALENDAR:
            bands = [
                f for f in city.frequencies if f.pattern == pattern.code and f.day_type == day_type
            ]
            if not bands:
                continue
            trip_id = f"{pattern.code}-{day_type}"
            trips.append(
                [
                    pattern.route.code,
                    day_type,
                    trip_id,
                    headsign,
                    pattern.direction,
                    pattern.code,
                    2,
                ]
            )
            start = bands[0].start_s
            for index, code in enumerate(pattern.stops):
                time = clock(start + pattern.times_s[index])
                stop_times.append(
                    [trip_id, time, time, code, index, f"{pattern.distances_m[index]:.1f}", 0]
                )
            for band in bands:
                frequencies.append(
                    [trip_id, clock(band.start_s), clock(band.end_s), band.headway_s, 0]
                )

    tables["trips.txt"] = (
        [
            "route_id",
            "service_id",
            "trip_id",
            "trip_headsign",
            "direction_id",
            "shape_id",
            "bikes_allowed",
        ],
        trips,
    )
    tables["stop_times.txt"] = (
        [
            "trip_id",
            "arrival_time",
            "departure_time",
            "stop_id",
            "stop_sequence",
            "shape_dist_traveled",
            "timepoint",
        ],
        stop_times,
    )
    tables["frequencies.txt"] = (
        ["trip_id", "start_time", "end_time", "headway_secs", "exact_times"],
        frequencies,
    )
    tables["shapes.txt"] = (
        ["shape_id", "shape_pt_lat", "shape_pt_lon", "shape_pt_sequence", "shape_dist_traveled"],
        shapes,
    )
    tables["feed_info.txt"] = (
        [
            "feed_publisher_name",
            "feed_publisher_url",
            "feed_lang",
            "feed_start_date",
            "feed_end_date",
            "feed_version",
            "feed_contact_email",
        ],
        [
            [
                "Projet nemesis, données fictives",
                URL,
                "fr",
                FEED_START,
                FEED_END,
                FEED_VERSION,
                "fixtures@example.org",
            ]
        ],
    )

    # GTFS-Fares v2: areas are the three fictional communes; cash only.
    tables["areas.txt"] = (
        ["area_id", "area_name"],
        [[code, f"{name} (fictif)"] for code, name, _ in AREAS],
    )
    tables["stop_areas.txt"] = (["area_id", "stop_id"], [[s.area, s.code] for s in stops.values()])
    tables["fare_media.txt"] = (
        ["fare_media_id", "fare_media_name", "fare_media_type"],
        [["especes", "Espèces (fictif)", 0]],
    )
    leg_rules: dict[tuple[str, str, str], int] = {}
    for route in city.routes:
        forward = next(p for p in patterns if p.route is route and p.direction == 0)
        areas = sorted({stops[code].area for code in forward.stops})
        if route.operator == "regie":
            leg_rules[(route.network, "", "")] = typical_fare(route, areas[0], areas[0])
            continue
        for from_area in areas:
            for to_area in areas:
                leg_rules[(route.network, from_area, to_area)] = typical_fare(
                    route, from_area, to_area
                )
    amounts = sorted(set(leg_rules.values()))
    tables["fare_products.txt"] = (
        ["fare_product_id", "fare_product_name", "fare_media_id", "amount", "currency"],
        [[f"xof-{amount}", f"{amount} F (fictif)", "especes", amount, "XOF"] for amount in amounts],
    )
    tables["fare_leg_rules.txt"] = (
        ["leg_group_id", "network_id", "from_area_id", "to_area_id", "fare_product_id"],
        [
            ["-".join(part for part in key if part), key[0], key[1], key[2], f"xof-{amount}"]
            for key, amount in sorted(leg_rules.items())
        ],
    )

    # Project extension (ADR-007, docs/DATA.md).
    tables["ext_feed_info.txt"] = (
        ["extension_name", "extension_version", "network_version", "produced_at"],
        [["ext", "0.1.0", "1", PRODUCED_AT]],
    )
    tables["ext_stop_attributes.txt"] = (
        [
            "stop_id",
            "stop_kind",
            "boarding_radius_m",
            "lighting",
            "shelter",
            "accessibility",
            "active_start",
            "active_end",
        ],
        [
            [
                s.code,
                s.kind,
                s.boarding_radius_m,
                s.lighting,
                "inconnu",
                "inconnu",
                "05:00:00",
                "22:00:00",
            ]
            for s in stops.values()
        ],
    )
    tables["ext_stop_aliases.txt"] = (
        ["stop_id", "alias", "alias_kind", "language"],
        [[s.code, alias, kind, "fr"] for s in stops.values() for alias, kind in s.aliases],
    )
    tables["ext_route_appearance.txt"] = (
        [
            "route_id",
            "body_color",
            "color_pattern",
            "markings",
            "announced_as",
            "source",
            "verified_at",
        ],
        [
            [
                r.code,
                r.body_color,
                r.color_pattern,
                f"Inscription « {r.long_name.upper()} »",
                r.announced_as,
                "fixtures_fictives",
                VERIFIED_AT,
            ]
            for r in city.routes
        ],
    )
    by_code = {p.code: p for p in patterns}
    tables["ext_service_profiles.txt"] = (
        [
            "route_id",
            "direction_id",
            "stop_id",
            "day_type",
            "slot_start",
            "active",
            "headway_mean_s",
            "headway_cv",
            "departs_when_full",
            "seats",
            "n_obs",
        ],
        [
            [
                by_code[s.pattern].route.code,
                by_code[s.pattern].direction,
                s.stop,
                s.day_type,
                clock(s.slot_s),
                1,
                s.headway_s,
                f"{s.headway_cv:.2f}",
                int(s.departs_when_full),
                s.seats,
                s.n_obs,
            ]
            for s in city.service_profiles
        ],
    )
    tables["ext_wait_profiles.txt"] = (
        [
            "stop_id",
            "route_id",
            "direction_id",
            "day_type",
            "slot_start",
            "regime",
            "wait_p50_s",
            "wait_p80_s",
            "n_obs",
            "confidence",
        ],
        [
            [
                w.stop,
                by_code[w.pattern].route.code,
                by_code[w.pattern].direction,
                w.day_type,
                clock(w.slot_s),
                w.regime,
                w.p50_s,
                w.p80_s,
                w.n_contributors,
                w.confidence,
            ]
            for w in city.wait_profiles
            if w.n_contributors >= PUBLICATION_MIN_CONTRIBUTORS
        ],
    )
    tables["ext_fare_estimates.txt"] = (
        [
            "route_id",
            "from_area_id",
            "to_area_id",
            "condition",
            "fare_p10",
            "fare_p50",
            "fare_p90",
            "n_obs",
            "last_observed_at",
            "confidence",
        ],
        [
            [
                f.route,
                f.from_area,
                f.to_area,
                f.condition,
                f.p10,
                f.p50,
                f.p90,
                f.n_contributors,
                LAST_OBSERVED_AT,
                f.confidence,
            ]
            for f in city.fare_estimates
            if f.n_contributors >= PUBLICATION_MIN_CONTRIBUTORS
        ],
    )
    tables["ext_route_reliability.txt"] = (
        [
            "route_id",
            "direction_id",
            "day_type",
            "slot_start",
            "service_probability",
            "wait_calibration",
            "n_obs",
        ],
        [
            [
                by_code[r.pattern].route.code,
                by_code[r.pattern].direction,
                r.day_type,
                clock(r.slot_s),
                f"{r.service_probability:.2f}",
                None,
                r.n_obs,
            ]
            for r in city.reliability
        ],
    )

    return {name: _csv(header, rows) for name, (header, rows) in tables.items()}

"""SQL seed writer: loads the fictional city into the database (data/schema).

Deterministic UUIDs (uuid5) and « on conflict do nothing » make the seed idempotent:
it is replayed at every « docker compose up ».
"""

from __future__ import annotations

import uuid
from collections.abc import Iterable, Sequence

from nemesis_pipelines.fixtures.city import AREAS, CITY_BBOX, CITY_CODE, CITY_NAME, OPERATORS, City
from nemesis_pipelines.fixtures.geo import polygon_wkt
from nemesis_pipelines.fixtures.gtfs import LAST_OBSERVED_AT, clock

NAMESPACE = uuid.uuid5(uuid.NAMESPACE_URL, "https://example.org/nemesis/fixtures-fictives")
SOURCE = "fixtures_fictives"
BATCH = 500


def ident(kind: str, code: str) -> str:
    return str(uuid.uuid5(NAMESPACE, f"{kind}:{code}"))


class Raw(str):
    """An SQL expression inserted as is (geometry constructors)."""


def literal(value: object) -> str:
    if value is None:
        return "null"
    if isinstance(value, Raw):
        return str(value)
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int | float):
        return repr(value)
    return "'" + str(value).replace("'", "''") + "'"


def geometry(wkt: str) -> Raw:
    return Raw(f"ST_GeomFromText('{wkt}', 4326)")


def point(lon: float, lat: float) -> Raw:
    return geometry(f"POINT({lon} {lat})")


def insert(table: str, columns: Sequence[str], rows: Iterable[Sequence[object]]) -> list[str]:
    rows = list(rows)
    statements = []
    for start in range(0, len(rows), BATCH):
        values = ",\n    ".join(
            "(" + ", ".join(literal(value) for value in row) + ")"
            for row in rows[start : start + BATCH]
        )
        header = f"insert into {table} ({', '.join(columns)}) values"
        statements.append(f"{header}\n    {values}\non conflict do nothing;")
    return statements


def seed_sql(city: City) -> str:
    city_id = ident("city", CITY_CODE)
    common = (city_id, True)
    stop_id = {code: ident("stop", code) for code in city.stops}
    route_id = {route.code: ident("route", route.code) for route in city.routes}
    pattern_id = {pattern.code: ident("pattern", pattern.code) for pattern in city.patterns}
    area_id = {code: ident("area", code) for code, _, _ in AREAS}
    fare_area_id = {code: ident("fare-area", code) for code, _, _ in AREAS}
    patterns = {pattern.code: pattern for pattern in city.patterns}

    parts = [
        "-- Fichier généré par « uv run nemesis-fixtures generer » : ne pas le modifier à la main.",
        "-- Ville entièrement fictive « Lagune-Fictive » (I0.5), placée en pleine mer (H-027).",
        "-- Chaque ligne porte is_fictional = true (règle 1.3.1). Rejouable sans effet.",
        "",
        "begin;",
    ]
    parts += insert(
        "network.source",
        ["id", "name", "license", "is_fictional"],
        [[SOURCE, "Données fictives du projet", "Données de test, sans valeur réelle", True]],
    )
    parts += insert(
        "network.city",
        ["id", "code", "name", "timezone", "currency", "metric_srid", "bbox", "is_fictional"],
        [
            [
                city_id,
                CITY_CODE,
                CITY_NAME,
                "Africa/Abidjan",
                "XOF",
                32630,
                geometry(polygon_wkt(*CITY_BBOX)),
                True,
            ]
        ],
    )
    parts += insert(
        "network.admin_area",
        ["id", "city_id", "is_fictional", "kind", "code", "name", "geom", "source_id"],
        [
            [
                area_id[code],
                *common,
                "commune",
                code,
                f"{name} (fictif)",
                Raw(f"ST_Multi({geometry(polygon_wkt(*bbox))})"),
                SOURCE,
            ]
            for code, name, bbox in AREAS
        ],
    )
    parts += insert(
        "network.place",
        [
            "id",
            "city_id",
            "is_fictional",
            "category",
            "name",
            "geom",
            "admin_area_id",
            "source_id",
            "confidence",
            "verification_status",
        ],
        [
            [
                ident("place", p.code),
                *common,
                p.category,
                p.name,
                point(p.lon, p.lat),
                area_id[p.area],
                SOURCE,
                "moyenne",
                "verifie",
            ]
            for p in city.places
        ],
    )
    parts += insert(
        "network.place_alias",
        ["place_id", "city_id", "is_fictional", "alias", "alias_kind"],
        [
            [ident("place", p.code), *common, alias, kind]
            for p in city.places
            for alias, kind in p.aliases
        ],
    )
    parts += insert(
        "network.stop",
        [
            "id",
            "city_id",
            "is_fictional",
            "code",
            "kind",
            "name",
            "geom",
            "boarding_radius_m",
            "lighting",
            "active_start",
            "active_end",
            "source_id",
            "confidence",
            "verification_status",
        ],
        [
            [
                stop_id[s.code],
                *common,
                s.code,
                s.kind,
                s.name,
                point(s.lon, s.lat),
                s.boarding_radius_m,
                s.lighting,
                "05:00",
                "22:00",
                SOURCE,
                "moyenne",
                "verifie",
            ]
            for s in city.stops.values()
        ],
    )
    parts += insert(
        "network.stop_alias",
        ["stop_id", "city_id", "is_fictional", "alias", "alias_kind"],
        [
            [stop_id[s.code], *common, alias, kind]
            for s in city.stops.values()
            for alias, kind in s.aliases
        ],
    )
    parts += insert(
        "network.operator",
        ["id", "city_id", "is_fictional", "code", "name", "kind"],
        [
            [ident("operator", code), *common, code, f"{name} (fictif)", kind]
            for code, name, kind in OPERATORS
        ],
    )
    parts += insert(
        "network.route",
        [
            "id",
            "city_id",
            "is_fictional",
            "code",
            "operator_id",
            "mode",
            "spoken_name",
            "body_color",
            "color_pattern",
            "markings",
            "announced_as",
            "source_id",
            "confidence",
            "verification_status",
        ],
        [
            [
                route_id[r.code],
                *common,
                r.code,
                ident("operator", r.operator),
                r.mode,
                f"{r.long_name} (fictif)",
                r.body_color,
                r.color_pattern,
                f"Inscription « {r.long_name.upper()} »",
                r.announced_as,
                SOURCE,
                "moyenne",
                "verifie",
            ]
            for r in city.routes
        ],
    )
    parts += insert(
        "network.route_pattern",
        [
            "id",
            "city_id",
            "is_fictional",
            "route_id",
            "code",
            "direction_id",
            "headsign",
            "shape",
            "continuous_pickup",
            "continuous_drop_off",
            "is_main",
        ],
        [
            [
                pattern_id[p.code],
                *common,
                route_id[p.route.code],
                p.code,
                p.direction,
                city.stops[p.stops[-1]].name,
                geometry(
                    "LINESTRING("
                    + ",".join(f"{city.stops[c].lon} {city.stops[c].lat}" for c in p.stops)
                    + ")"
                ),
                p.route.operator == "artisanal",
                p.route.operator == "artisanal",
                True,
            ]
            for p in city.patterns
        ],
    )
    parts += insert(
        "network.route_pattern_stop",
        ["route_pattern_id", "sequence", "stop_id", "city_id", "is_fictional", "distance_along_m"],
        [
            [pattern_id[p.code], index, stop_id[code], *common, p.distances_m[index]]
            for p in city.patterns
            for index, code in enumerate(p.stops)
        ],
    )
    parts += insert(
        "network.service_profile",
        [
            "city_id",
            "is_fictional",
            "route_pattern_id",
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
                *common,
                pattern_id[s.pattern],
                stop_id[s.stop],
                s.day_type,
                clock(s.slot_s),
                True,
                s.headway_s,
                s.headway_cv,
                s.departs_when_full,
                s.seats,
                s.n_obs,
            ]
            for s in city.service_profiles
        ],
    )
    parts += insert(
        "network.fare_area",
        ["id", "city_id", "is_fictional", "code", "name", "geom"],
        [
            [
                fare_area_id[code],
                *common,
                code,
                f"{name} (fictif)",
                Raw(f"ST_Multi({geometry(polygon_wkt(*bbox))})"),
            ]
            for code, name, bbox in AREAS
        ],
    )
    parts += insert(
        "network.fare_area_stop",
        ["fare_area_id", "stop_id", "city_id", "is_fictional"],
        [[fare_area_id[s.area], stop_id[s.code], *common] for s in city.stops.values()],
    )
    parts += insert(
        "mobility.wait_profile",
        [
            "city_id",
            "is_fictional",
            "stop_id",
            "route_id",
            "direction_id",
            "day_type",
            "slot_start",
            "regime",
            "wait_p50_s",
            "wait_p80_s",
            "n_obs",
            "n_contributors",
            "confidence",
        ],
        [
            [
                *common,
                stop_id[w.stop],
                route_id[patterns[w.pattern].route.code],
                patterns[w.pattern].direction,
                w.day_type,
                clock(w.slot_s),
                w.regime,
                w.p50_s,
                w.p80_s,
                w.n_obs,
                w.n_contributors,
                w.confidence,
            ]
            for w in city.wait_profiles
        ],
    )
    parts += insert(
        "mobility.fare_estimate",
        [
            "city_id",
            "is_fictional",
            "route_id",
            "from_area_id",
            "to_area_id",
            "condition",
            "fare_p10",
            "fare_p50",
            "fare_p90",
            "n_obs",
            "n_contributors",
            "last_observed_at",
            "confidence",
        ],
        [
            [
                *common,
                route_id[f.route],
                fare_area_id[f.from_area],
                fare_area_id[f.to_area],
                f.condition,
                f.p10,
                f.p50,
                f.p90,
                f.n_obs,
                f.n_contributors,
                LAST_OBSERVED_AT,
                f.confidence,
            ]
            for f in city.fare_estimates
        ],
    )
    parts += insert(
        "network.incident",
        [
            "id",
            "city_id",
            "is_fictional",
            "kind",
            "geom",
            "severity",
            "starts_at",
            "status",
            "source_id",
        ],
        [
            [
                ident("incident", "inondation-pont"),
                *common,
                "inondation",
                geometry(polygon_wkt(-4.048, 1.975, -4.042, 1.981)),
                "forte",
                "2026-11-01T06:00:00Z",
                "confirme",
                SOURCE,
            ]
        ],
    )
    parts += insert(
        "ops.staff_account",
        ["id", "display_name", "email", "role", "mfa_enabled", "is_fictional"],
        [
            [
                ident("staff", "curatrice"),
                "Curatrice (fictif)",
                "curatrice@example.org",
                "curateur",
                True,
                True,
            ],
            [
                ident("staff", "moderateur"),
                "Modérateur (fictif)",
                "moderateur@example.org",
                "moderateur",
                True,
                True,
            ],
        ],
    )
    parts += insert(
        "network.network_version",
        ["city_id", "is_fictional", "number", "status", "notes"],
        [[*common, 1, "brouillon", "Réseau fictif de départ (I0.5)"]],
    )
    parts += ["commit;", ""]
    return "\n".join(parts)

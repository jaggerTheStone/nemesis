"""GTFS ↔ OSM gap report (I0.7): what the GTFS says and what OpenStreetMap says now.

Stops are matched first by identity, when the GTFS was produced from OSM (`node/123`
identifiers), then one to one by distance. Routes are matched by identity (route
relation = shape), then by reference and by geometry: the share of each line that
runs within a buffer of the other. Nothing is decided here: the report lists the
gaps, for review by the data team.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

from nemesis_pipelines.sources import City

STOP_MATCH_M = 50.0  # a GTFS stop and an OSM stop farther apart are distinct
STOP_MOVED_M = 20.0  # a matched stop farther than this has moved
ROUTE_BUFFER_M = 30.0  # tolerance of the geometric comparison of routes
ROUTE_SAME = 0.95  # both lines run within each other's buffer for 95 % of their length
ROUTE_MATCH = 0.80  # below this, without the same reference, routes are distinct
ENDPOINT_M = 150.0  # candidate OSM routes pass this close to both ends of the GTFS line
NAME_SIMILAR = 0.5  # trigram similarity under which names are reported as different
COVERAGE_M = 300.0  # OSM-only objects are counted within this distance of GTFS stops
MAX_LISTED = 50  # longest list in the Markdown report (the GeoJSON has everything)

OSM_REF = re.compile(r"^(node|way|relation)/([0-9]+)$")
OSM_TYPES = {"node": "N", "way": "W", "relation": "R"}
OSM_TYPE_NAMES = {value: key for key, value in OSM_TYPES.items()}

GAP_LABELS = {
    "arret_deplace": "Arrêts déplacés de plus de 20 m",
    "nom_different": "Arrêts dont le nom diffère",
    "arret_absent_osm": "Arrêts du GTFS absents d'OSM",
    "arret_absent_gtfs": "Arrêts d'OSM absents du GTFS",
    "trace_different": "Lignes au tracé différent",
    "nom_ligne_different": "Lignes dont le nom diffère",
    "ligne_absente_osm": "Tracés du GTFS absents d'OSM",
    "ligne_absente_gtfs": "Lignes d'OSM absentes du GTFS",
}

_ENVELOPE = "st_makeenvelope(%s::float8, %s::float8, %s::float8, %s::float8, 4326)"

SETUP_SQL = [
    # GTFS stops of the run (stops and stations; entrances and nodes are not compared).
    """
    create temp table gap_gtfs_stop on commit drop as
    select stop_id, stop_name, line_no, geom
    from staging_gtfs.stop
    where import_run_id = %s::uuid and location_type in (0, 1) and geom is not null
    """,
    "create index on gap_gtfs_stop using gist (geom)",
    # Area where the GTFS has stops: OSM-only objects are only counted there.
    f"""
    create temp table gap_area on commit drop as
    select st_intersection(
               st_buffer(st_convexhull(st_collect(geom))::geography, %s::float8)::geometry,
               {_ENVELOPE}) as geom
    from gap_gtfs_stop
    """,
    # OSM stops in the city (stop positions duplicate platforms and are left aside).
    f"""
    create temp table gap_osm_stop on commit drop as
    select osm_type, osm_id, kind, name, geom
    from staging_osm.transit_stop
    where kind <> 'stop_position' and st_intersects(geom, {_ENVELOPE})
    """,
    "create index on gap_osm_stop using gist (geom)",
    "create index on gap_osm_stop (osm_type, osm_id)",
    # One GTFS line per shape; trips without a shape follow their stops.
    """
    create temp table gap_gtfs_line on commit drop as
    with run as (select %s::uuid as id),
    shape_line as (
        select shape_id, st_makeline(geom order by sequence, line_no) as geom
        from staging_gtfs.shape_point, run
        where import_run_id = run.id and geom is not null
        group by shape_id
    ),
    shaped as (
        select distinct on (t.shape_id) t.shape_id as key, t.shape_id, t.route_id,
               t.direction_id, t.trip_headsign
        from staging_gtfs.trip t, run
        where t.import_run_id = run.id and t.shape_id is not null
        order by t.shape_id, t.line_no
    ),
    unshaped as (
        select t.trip_id, t.route_id, t.direction_id, t.trip_headsign,
               st_makeline(s.geom order by st.stop_sequence) as geom,
               string_agg(st.stop_id, '>' order by st.stop_sequence) as sequence
        from staging_gtfs.trip t
        join run on t.import_run_id = run.id
        join staging_gtfs.stop_time st on st.import_run_id = run.id and st.trip_id = t.trip_id
        join staging_gtfs.stop s on s.import_run_id = run.id and s.stop_id = st.stop_id
        where t.shape_id is null and s.geom is not null
        group by t.trip_id, t.route_id, t.direction_id, t.trip_headsign
    )
    select key, shape_id, route_id, direction_id, trip_headsign, geom, 'shape' as geometry_source
    from shaped join shape_line using (shape_id)
    union all
    (select distinct on (route_id, sequence) 'trip:' || trip_id, null, route_id, direction_id,
            trip_headsign, geom, 'arrets'
     from unshaped
     order by route_id, sequence, trip_id)
    """,
    """
    create temp table gap_gtfs_route on commit drop as
    select l.*, r.route_short_name, r.route_long_name, r.route_type,
           st_transform(l.geom, %s::integer) as geom_m
    from gap_gtfs_line l
    left join staging_gtfs.route r on r.import_run_id = %s::uuid and r.route_id = l.route_id
    where st_npoints(l.geom) >= 2
    """,
    "alter table gap_gtfs_route add column buffer_m geometry",
    "update gap_gtfs_route set buffer_m = st_buffer(geom_m, %s::float8)",
    # OSM routes crossing the GTFS area, with their first stop for the direction.
    """
    create temp table gap_osm_route on commit drop as
    select r.relation_id, r.route, r.ref, r.name, r.geom,
           st_transform(r.geom, %s::integer) as geom_m,
           (select s.geom from staging_osm.route_member m
              join staging_osm.transit_stop s
                on s.osm_type = upper(m.member_type) and s.osm_id = m.member_id
             where m.relation_id = r.relation_id
               and (m.role like 'platform%%' or m.role like 'stop%%')
             order by m.sequence limit 1) as first_stop
    from staging_osm.route r
    where r.geom is not null and st_intersects(r.geom, (select geom from gap_area))
    """,
    "alter table gap_osm_route add column buffer_m geometry",
    "update gap_osm_route set buffer_m = st_buffer(geom_m, %s::float8)",
    "create index on gap_osm_route using gist (geom_m)",
]

STOP_IDENTITY_SQL = """
select g.stop_id, g.stop_name, s.osm_type, s.osm_id, s.name,
       st_distance(g.geom::geography, s.geom::geography),
       similarity(network.normalize_text(g.stop_name), network.normalize_text(coalesce(s.name, '')))
from gap_gtfs_stop g
join staging_osm.transit_stop s
  on s.osm_type = %s and s.osm_id = %s::bigint
where g.stop_id = %s
order by s.kind = 'stop_position'
limit 1
"""

STOP_CANDIDATES_SQL = """
select g.stop_id, g.stop_name, o.osm_type, o.osm_id, o.name,
       st_distance(g.geom::geography, o.geom::geography) as distance,
       similarity(network.normalize_text(g.stop_name), network.normalize_text(coalesce(o.name, '')))
from gap_gtfs_stop g
join gap_osm_stop o
  on o.geom && st_expand(g.geom, 0.001)
 and st_dwithin(g.geom::geography, o.geom::geography, %s::float8)
"""

ROUTE_METRICS = """
       coalesce(st_length(st_intersection(g.geom_m, o.buffer_m))
                / nullif(st_length(g.geom_m), 0), 0),
       coalesce(st_length(st_intersection(o.geom_m, g.buffer_m))
                / nullif(st_length(o.geom_m), 0), 0),
       coalesce(upper(g.route_short_name) = upper(o.ref), false),
       similarity(network.normalize_text(coalesce(g.route_long_name, g.route_short_name, '')),
                  network.normalize_text(coalesce(o.name, o.ref, ''))),
       st_distance(st_transform(st_startpoint(g.geom), %s::integer),
                   st_transform(o.first_stop, %s::integer))
"""

ROUTE_IDENTITY_SQL = f"""
select g.key, o.relation_id, {ROUTE_METRICS}
from gap_gtfs_route g join gap_osm_route o on o.relation_id = g.shape_id::bigint
where g.shape_id ~ '^[0-9]{{1,18}}$'
"""

ROUTE_CANDIDATES_SQL = f"""
select g.key, o.relation_id, {ROUTE_METRICS}
from gap_gtfs_route g
join gap_osm_route o
  on (g.route_short_name is not null and upper(g.route_short_name) = upper(o.ref))
  or (st_dwithin(st_startpoint(g.geom_m), o.geom_m, %s::float8)
      and st_dwithin(st_endpoint(g.geom_m), o.geom_m, %s::float8))
-- A line already matched by identity needs no other candidate.
where not (g.shape_id ~ '^[0-9]{{1,18}}$'
           and exists (select from gap_osm_route i where i.relation_id = g.shape_id::bigint))
"""


@dataclass
class StopMatch:
    gtfs_id: str
    gtfs_name: str
    osm_type: str
    osm_id: int
    osm_name: str | None
    distance_m: float
    name_similarity: float
    by_identity: bool

    @property
    def osm_ref(self) -> str:
        return f"{OSM_TYPE_NAMES[self.osm_type]}/{self.osm_id}"


@dataclass
class RouteMatch:
    gtfs_key: str
    osm_relation: int
    coverage_gtfs: float  # share of the GTFS line within the OSM buffer
    coverage_osm: float  # share of the OSM line within the GTFS buffer
    same_ref: bool
    name_similarity: float
    start_gap_m: float | None
    by_identity: bool

    @property
    def similarity(self) -> float:
        return min(self.coverage_gtfs, self.coverage_osm)


@dataclass
class GapReport:
    city: str
    gtfs_run: str
    osm_run: str | None
    totals: dict[str, int] = field(default_factory=dict)
    stop_matches: list[StopMatch] = field(default_factory=list)
    route_matches: list[RouteMatch] = field(default_factory=list)
    features: list[dict[str, Any]] = field(default_factory=list)

    def gaps(self, kind: str) -> list[dict[str, Any]]:
        return [f["properties"] for f in self.features if f["properties"]["ecart"] == kind]


def assign_stops(identity: list[StopMatch], candidates: list[StopMatch]) -> list[StopMatch]:
    """One to one: identity first, then the closest pairs (similar names break ties)."""
    matches = list(identity)
    used_gtfs = {m.gtfs_id for m in matches}
    used_osm = {(m.osm_type, m.osm_id) for m in matches}
    for candidate in sorted(candidates, key=lambda c: (c.distance_m, -c.name_similarity)):
        key = (candidate.osm_type, candidate.osm_id)
        if candidate.gtfs_id in used_gtfs or key in used_osm:
            continue
        matches.append(candidate)
        used_gtfs.add(candidate.gtfs_id)
        used_osm.add(key)
    return matches


def assign_routes(identity: list[RouteMatch], candidates: list[RouteMatch]) -> list[RouteMatch]:
    """One to one: identity first, then same reference, geometric similarity, direction."""
    matches = list(identity)
    used_gtfs = {m.gtfs_key for m in matches}
    used_osm = {m.osm_relation for m in matches}
    eligible = [c for c in candidates if c.same_ref or c.similarity >= ROUTE_MATCH]
    order = sorted(
        eligible,
        key=lambda c: (
            not c.same_ref,
            -round(c.similarity, 2),
            c.start_gap_m if c.start_gap_m is not None else float("inf"),
        ),
    )
    for candidate in order:
        if candidate.gtfs_key in used_gtfs or candidate.osm_relation in used_osm:
            continue
        matches.append(candidate)
        used_gtfs.add(candidate.gtfs_key)
        used_osm.add(candidate.osm_relation)
    return matches


def _stop(row: tuple[Any, ...], by_identity: bool) -> StopMatch:
    return StopMatch(
        row[0], row[1], row[2], int(row[3]), row[4], float(row[5]), float(row[6]), by_identity
    )


def _route(row: tuple[Any, ...], by_identity: bool) -> RouteMatch:
    gap = row[6]
    return RouteMatch(
        row[0],
        int(row[1]),
        float(row[2]),
        float(row[3]),
        bool(row[4]),
        float(row[5]),
        None if gap is None else float(gap),
        by_identity,
    )


def _feature(geometry: str | None, **properties: Any) -> dict[str, Any]:
    return {
        "type": "Feature",
        "geometry": json.loads(geometry) if geometry else None,
        "properties": properties,
    }


def build_report(cursor: Any, city: City, gtfs_run: str, osm_run: str | None) -> GapReport:
    bbox = city.bbox
    srid = city.metric_srid
    parameters = [
        (gtfs_run,),
        (),
        (COVERAGE_M, *bbox),
        (*bbox,),
        (),
        (),
        (gtfs_run,),
        (srid, gtfs_run),
        (),
        (ROUTE_BUFFER_M,),
        (srid,),
        (),
        (ROUTE_BUFFER_M,),
        (),
    ]
    for sql, params in zip(SETUP_SQL, parameters, strict=True):
        if params:
            cursor.execute(sql, params)
        else:
            cursor.execute(sql)

    report = GapReport(city=city.code, gtfs_run=gtfs_run, osm_run=osm_run)

    # --- Stops ----------------------------------------------------------------------------
    cursor.execute("select stop_id from gap_gtfs_stop")
    gtfs_ids = [row[0] for row in cursor.fetchall()]
    identity = []
    for stop_id in gtfs_ids:
        found = OSM_REF.match(stop_id)
        if not found:
            continue
        cursor.execute(STOP_IDENTITY_SQL, (OSM_TYPES[found.group(1)], int(found.group(2)), stop_id))
        row = cursor.fetchone()
        if row:
            identity.append(_stop(row, True))
    cursor.execute(STOP_CANDIDATES_SQL, (STOP_MATCH_M,))
    candidates = [_stop(row, False) for row in cursor.fetchall()]
    report.stop_matches = assign_stops(identity, candidates)

    cursor.execute(
        "select count(*) from staging_gtfs.stop where import_run_id = %s::uuid and geom is null",
        (gtfs_run,),
    )
    unreadable = cursor.fetchone()[0]
    cursor.execute(
        "select count(*) from gap_osm_stop where st_intersects(geom, (select geom from gap_area))"
    )
    osm_stops_in_area = cursor.fetchone()[0]

    matched_gtfs = {m.gtfs_id for m in report.stop_matches}
    matched_osm = {(m.osm_type, m.osm_id) for m in report.stop_matches}
    for match in report.stop_matches:
        cursor.execute(
            """
            select st_asgeojson(st_makeline(g.geom, s.geom), 6)
            from gap_gtfs_stop g, staging_osm.transit_stop s
            where g.stop_id = %s and s.osm_type = %s and s.osm_id = %s
            limit 1
            """,
            (match.gtfs_id, match.osm_type, match.osm_id),
        )
        line = cursor.fetchone()[0]
        common = {
            "gtfs_stop_id": match.gtfs_id,
            "gtfs_nom": match.gtfs_name,
            "osm": match.osm_ref,
            "osm_nom": match.osm_name,
            "distance_m": round(match.distance_m, 1),
            "par_identifiant": match.by_identity,
        }
        if match.distance_m > STOP_MOVED_M:
            report.features.append(_feature(line, ecart="arret_deplace", **common))
        if match.name_similarity < NAME_SIMILAR:
            report.features.append(
                _feature(
                    line,
                    ecart="nom_different",
                    similarite=round(match.name_similarity, 2),
                    **common,
                )
            )
    cursor.execute("select stop_id, stop_name, line_no, st_asgeojson(geom, 6) from gap_gtfs_stop")
    for stop_id, name, line_no, geometry in cursor.fetchall():
        if stop_id not in matched_gtfs:
            report.features.append(
                _feature(
                    geometry,
                    ecart="arret_absent_osm",
                    gtfs_stop_id=stop_id,
                    gtfs_nom=name,
                    ligne_stops_txt=line_no,
                )
            )
    cursor.execute(
        """
        select osm_type, osm_id, kind, name, st_asgeojson(geom, 6) from gap_osm_stop
        where st_intersects(geom, (select geom from gap_area))
        order by osm_type, osm_id
        """
    )
    for osm_type, osm_id, kind, name, geometry in cursor.fetchall():
        if (osm_type, osm_id) not in matched_osm:
            report.features.append(
                _feature(
                    geometry,
                    ecart="arret_absent_gtfs",
                    osm=f"{OSM_TYPE_NAMES[osm_type]}/{osm_id}",
                    osm_nom=name,
                    nature=kind,
                )
            )

    # --- Routes ---------------------------------------------------------------------------
    cursor.execute(ROUTE_IDENTITY_SQL, (srid, srid))
    route_identity = [_route(row, True) for row in cursor.fetchall()]
    cursor.execute(ROUTE_CANDIDATES_SQL, (srid, srid, ENDPOINT_M, ENDPOINT_M))
    route_candidates = [_route(row, False) for row in cursor.fetchall()]
    report.route_matches = assign_routes(route_identity, route_candidates)

    cursor.execute(
        """
        select key, route_id, route_short_name, route_long_name, direction_id, geometry_source,
               round(st_length(geom::geography)), st_asgeojson(geom, 6)
        from gap_gtfs_route order by key
        """
    )
    gtfs_lines = {row[0]: row for row in cursor.fetchall()}
    cursor.execute(
        """
        select relation_id, route, ref, name, round(st_length(geom::geography)),
               st_asgeojson(geom, 6)
        from gap_osm_route order by relation_id
        """
    )
    osm_lines = {row[0]: row for row in cursor.fetchall()}

    def gtfs_props(key: str) -> dict[str, Any]:
        _, route_id, short, long_name, direction, source, length, _ = gtfs_lines[key]
        return {
            "gtfs_trace": key,
            "gtfs_route_id": route_id,
            "gtfs_ligne": short or long_name,
            "gtfs_nom": long_name,
            "sens": direction,
            "trace_issu_de": source,
            "longueur_m": int(length),
        }

    def osm_props(relation: int) -> dict[str, Any]:
        _, mode, ref, name, length, _ = osm_lines[relation]
        return {
            "osm": f"relation/{relation}",
            "osm_mode": mode,
            "osm_ref": ref,
            "osm_nom": name,
            "osm_longueur_m": int(length),
        }

    for match in report.route_matches:
        common = {
            **gtfs_props(match.gtfs_key),
            **osm_props(match.osm_relation),
            "part_gtfs_sur_osm": round(match.coverage_gtfs, 3),
            "part_osm_sur_gtfs": round(match.coverage_osm, 3),
            "meme_reference": match.same_ref,
            "par_identifiant": match.by_identity,
        }
        if match.similarity < ROUTE_SAME:
            report.features.append(
                _feature(
                    gtfs_lines[match.gtfs_key][7], ecart="trace_different", cote="gtfs", **common
                )
            )
            report.features.append(
                _feature(
                    osm_lines[match.osm_relation][5], ecart="trace_different", cote="osm", **common
                )
            )
        if match.name_similarity < NAME_SIMILAR and not match.same_ref:
            report.features.append(
                _feature(
                    gtfs_lines[match.gtfs_key][7],
                    ecart="nom_ligne_different",
                    similarite=round(match.name_similarity, 2),
                    **common,
                )
            )
    matched_lines = {m.gtfs_key for m in report.route_matches}
    matched_relations = {m.osm_relation for m in report.route_matches}
    for key, row in gtfs_lines.items():
        if key not in matched_lines:
            report.features.append(_feature(row[7], ecart="ligne_absente_osm", **gtfs_props(key)))
    for relation, row in osm_lines.items():
        if relation not in matched_relations:
            report.features.append(
                _feature(row[5], ecart="ligne_absente_gtfs", **osm_props(relation))
            )

    report.totals = {
        "arrets_gtfs": len(gtfs_ids),
        "arrets_gtfs_coordonnees_illisibles": unreadable,
        "arrets_osm_dans_la_zone": osm_stops_in_area,
        "arrets_apparies": len(report.stop_matches),
        "arrets_apparies_par_identifiant": sum(m.by_identity for m in report.stop_matches),
        "traces_gtfs": len(gtfs_lines),
        "lignes_osm_dans_la_zone": len(osm_lines),
        "traces_apparies": len(report.route_matches),
        "traces_apparies_par_identifiant": sum(m.by_identity for m in report.route_matches),
    }
    for kind in GAP_LABELS:
        rows = report.gaps(kind)
        # A different route shows twice (GTFS and OSM sides): count it once.
        report.totals[kind] = len([r for r in rows if r.get("cote") != "osm"])
    return report


def geojson(report: GapReport) -> str:
    collection = {
        "type": "FeatureCollection",
        "properties": {
            "ville": report.city,
            "import_gtfs": report.gtfs_run,
            "import_osm": report.osm_run,
        },
        "features": report.features,
    }
    return json.dumps(collection, ensure_ascii=False, indent=1) + "\n"


def _cell(value: Any) -> str:
    text = "" if value is None else str(value)
    return text.replace("|", "\\|").replace("\n", " ")


def markdown(report: GapReport, gtfs_label: str, osm_label: str) -> str:
    t = report.totals
    lines = [
        f"# Écarts GTFS ↔ OSM : {report.city}",
        "",
        f"- GTFS : {gtfs_label} (import `{report.gtfs_run}`)",
        f"- OSM : {osm_label} (import `{report.osm_run}`)",
        f"- Seuils : arrêts appariés à moins de {STOP_MATCH_M:.0f} m, déplacés au-delà de"
        f" {STOP_MOVED_M:.0f} m ; tracés comparés dans une bande de {ROUTE_BUFFER_M:.0f} m,"
        f" identiques au-delà de {ROUTE_SAME * 100:.0f} % de longueur commune dans les deux sens.",
        "- Toutes les entités sont dans le fichier GeoJSON qui accompagne ce rapport.",
        "",
        "## Synthèse",
        "",
        "| Mesure | Valeur |",
        "|--------|--------|",
        f"| Arrêts du GTFS | {t['arrets_gtfs']} |",
        f"| Arrêts d'OSM dans la zone du GTFS | {t['arrets_osm_dans_la_zone']} |",
        f"| Arrêts appariés (dont par identifiant OSM) | {t['arrets_apparies']}"
        f" ({t['arrets_apparies_par_identifiant']}) |",
        f"| Tracés du GTFS | {t['traces_gtfs']} |",
        f"| Lignes d'OSM dans la zone du GTFS | {t['lignes_osm_dans_la_zone']} |",
        f"| Tracés appariés (dont par identifiant OSM) | {t['traces_apparies']}"
        f" ({t['traces_apparies_par_identifiant']}) |",
    ]
    if t["arrets_gtfs_coordonnees_illisibles"]:
        unreadable = t["arrets_gtfs_coordonnees_illisibles"]
        lines.append(f"| Arrêts du GTFS aux coordonnées illisibles | {unreadable} |")
    lines += [f"| {label} | {t[kind]} |" for kind, label in GAP_LABELS.items()]

    columns = {
        "arret_deplace": ("gtfs_stop_id", "gtfs_nom", "osm", "osm_nom", "distance_m"),
        "nom_different": ("gtfs_stop_id", "gtfs_nom", "osm", "osm_nom", "similarite"),
        "arret_absent_osm": ("gtfs_stop_id", "gtfs_nom", "ligne_stops_txt"),
        "arret_absent_gtfs": ("osm", "osm_nom", "nature"),
        "trace_different": (
            "gtfs_trace",
            "gtfs_ligne",
            "osm",
            "osm_nom",
            "part_gtfs_sur_osm",
            "part_osm_sur_gtfs",
        ),
        "nom_ligne_different": ("gtfs_trace", "gtfs_nom", "osm", "osm_nom", "similarite"),
        "ligne_absente_osm": ("gtfs_trace", "gtfs_ligne", "gtfs_nom", "sens", "longueur_m"),
        "ligne_absente_gtfs": ("osm", "osm_mode", "osm_ref", "osm_nom", "osm_longueur_m"),
    }
    for kind, label in GAP_LABELS.items():
        rows = [r for r in report.gaps(kind) if r.get("cote") != "osm"]
        if not rows:
            continue
        keys = columns[kind]
        lines += ["", f"## {label} ({len(rows)})", ""]
        lines.append("| " + " | ".join(keys) + " |")
        lines.append("|" + "---|" * len(keys))
        for row in rows[:MAX_LISTED]:
            lines.append("| " + " | ".join(_cell(row.get(k)) for k in keys) + " |")
        if len(rows) > MAX_LISTED:
            lines.append(f"\n… {len(rows) - MAX_LISTED} autre(s) dans le GeoJSON.")
    return "\n".join(lines) + "\n"

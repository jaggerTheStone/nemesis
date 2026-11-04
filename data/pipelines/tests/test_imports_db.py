"""Imports against a migrated database: staging, licence guard, gap report, places (I0.7)."""

from __future__ import annotations

import zipfile
from pathlib import Path
from typing import Any

import pg8000.dbapi
import pytest

from nemesis_pipelines.download import Fetched, Provenance, fetch
from nemesis_pipelines.fixtures.osm import DIVERGENCES
from nemesis_pipelines.gtfs.staging import load_gtfs
from nemesis_pipelines.osm.importer import import_osm
from nemesis_pipelines.osm.places import ensure_city, promote_places
from nemesis_pipelines.reports import gaps
from nemesis_pipelines.runs import current_osm_run, ensure_source
from nemesis_pipelines.sources import Manifest, Source, load_manifest
from nemesis_schema.connection import connect


@pytest.fixture
def manifest(repository: Path) -> Manifest:
    return load_manifest(repository / "data/pipelines/sources.toml")


def _error(cursor: Any, sql: str, *params: Any) -> tuple[str, str]:
    cursor.execute("savepoint expected")
    try:
        cursor.execute(sql, params) if params else cursor.execute(sql)
    except pg8000.dbapi.DatabaseError as error:
        cursor.execute("rollback to savepoint expected")
        return error.args[0]["C"], error.args[0]["M"]
    raise AssertionError(f"statement succeeded: {sql}")


def _fictional_gtfs(tmp_path: Path, files: dict[str, str], name: str = "gtfs_test") -> Fetched:
    path = tmp_path / f"{name}.zip"
    with zipfile.ZipFile(path, "w") as archive:
        for file_name, content in files.items():
            archive.writestr(file_name, content)
    source = _gtfs_source(name)
    provenance = Provenance(
        source_id=source.id,
        kind="gtfs",
        url=f"depot:{name}",
        file_name=path.name,
        sha256="0" * 64,
        size_bytes=path.stat().st_size,
        verified_by="fichier_du_depot",
        retrieved_at="2026-11-04T06:00:00Z",
        license=source.license,
        usage=source.usage,
        is_fictional=True,
    )
    return Fetched(path, provenance)


def _gtfs_source(name: str = "gtfs_test") -> Source:
    return Source(
        id=name,
        kind="gtfs",
        name="GTFS de test (fictif)",
        license="test",
        usage="produit",
        is_fictional=True,
        path=f"{name}.zip",
    )


def test_an_evaluation_source_never_enters_the_network(pg_url: str, manifest: Manifest) -> None:
    connection = connect(pg_url)
    cursor = connection.cursor()
    ensure_source(cursor, manifest.source("gtfs_abidjan_2023"))
    city_id = ensure_city(cursor, manifest.city("abidjan"))
    insert = """
        insert into network.place (city_id, category, name, geom, source_id)
        values (%s::uuid, 'gare', 'Gare de test', st_setsrid(st_makepoint(-4.0, 5.3), 4326), %s)
    """
    code, message = _error(cursor, insert, city_id, "gtfs_abidjan_2023")
    assert code == "NM004" and "réservée à l'évaluation" in message

    # A source already used by the network cannot be switched to evaluation afterwards.
    ensure_source(cursor, manifest.source("osm_cote_divoire"))
    cursor.execute(insert, (city_id, "osm_cote_divoire"))
    code, _ = _error(
        cursor, "update network.source set usage = 'evaluation' where id = 'osm_cote_divoire'"
    )
    assert code == "NM004"
    connection.rollback()
    connection.close()


def test_gtfs_values_are_staged_intact_and_typed_when_readable(pg_url: str, tmp_path: Path) -> None:
    files = {
        "stops.txt": "stop_id,stop_name,stop_lat,stop_lon\na,Arrêt A (fictif),2.0,-4.0\n"
        "b,Arrêt B (fictif),abc,-4.0\nc,Arrêt C (fictif),95,-4.0\n",
        "routes.txt": "route_id,route_short_name,route_type\nr,R,3\n",
    }
    connection = connect(pg_url)
    run_ids = []
    for _ in range(3):
        run_id, counts = load_gtfs(connection, _gtfs_source(), _fictional_gtfs(tmp_path, files))
        run_ids.append(run_id)
    cursor = connection.cursor()
    cursor.execute(
        "select stop_id, geom is null from staging_gtfs.stop where import_run_id = %s::uuid"
        " order by stop_id",
        (run_ids[-1],),
    )
    assert [list(row) for row in cursor.fetchall()] == [["a", False], ["b", True], ["c", True]]
    cursor.execute(
        "select data ->> 'stop_lat' from staging_gtfs.record where import_run_id = %s::uuid"
        " and line_no = 3",
        (run_ids[-1],),
    )
    assert cursor.fetchone()[0] == "abc"
    cursor.execute(
        "select status, counts -> 'files' ->> 'stops.txt' from ops.import_run where id = %s::uuid",
        (run_ids[-1],),
    )
    assert cursor.fetchone() == ["termine", "3"]
    # Only the two latest runs keep their rows; all three stay listed.
    cursor.execute("select count(distinct import_run_id) from staging_gtfs.record")
    assert cursor.fetchone()[0] == 2
    cursor.execute("select count(*) from ops.import_run where source_id = 'gtfs_test'")
    assert cursor.fetchone()[0] == 3
    assert counts["files"] == {"routes.txt": 1, "stops.txt": 3}
    connection.close()


def test_the_api_role_cannot_read_staging(pg_url: str, tmp_path: Path) -> None:
    connection = connect(pg_url)
    load_gtfs(connection, _gtfs_source(), _fictional_gtfs(tmp_path, {"stops.txt": "stop_id\na\n"}))
    cursor = connection.cursor()
    cursor.execute("set role nemesis_api")
    code, _ = _error(cursor, "select count(*) from staging_gtfs.record")
    assert code == "42501"
    cursor.execute("reset role")
    cursor.execute("set role nemesis_analyst")
    cursor.execute("select count(*) from staging_gtfs.record")
    assert cursor.fetchone()[0] == 1
    connection.rollback()
    connection.close()


@pytest.fixture
def fictional_osm(
    pg_url: str, osm2pgsql: None, manifest: Manifest, repository: Path, tmp_path: Path
) -> str:
    """Imports the fictional OSM extract; returns the run id."""
    source = manifest.source("osm_lagune_fictive")
    fetched = fetch(source, tmp_path / "travail", root=repository)
    connection = connect(pg_url)
    run_id, counts = import_osm(connection, pg_url, source, fetched)
    connection.close()
    assert counts["route"] == 23 and counts["transit_stop"] == 35
    return run_id


def test_the_fictional_chain_finds_exactly_the_deliberate_gaps(
    pg_url: str, fictional_osm: str, manifest: Manifest, repository: Path, tmp_path: Path
) -> None:
    source = manifest.source("gtfs_lagune_fictive")
    connection = connect(pg_url)
    gtfs_run, _ = load_gtfs(connection, source, fetch(source, tmp_path / "t", root=repository))
    cursor = connection.cursor()
    report = gaps.build_report(cursor, manifest.city("lagune-fictive"), gtfs_run, fictional_osm)
    connection.rollback()
    connection.close()

    found = {
        kind: sorted(
            str(row.get("gtfs_stop_id") or row.get("gtfs_trace") or row.get("osm_nom"))
            for row in report.gaps(kind)
            if row.get("cote") != "osm"
        )
        for kind in gaps.GAP_LABELS
    }
    assert found["arret_deplace"] == DIVERGENCES["arret_deplace"]
    assert found["nom_different"] == DIVERGENCES["nom_different"]
    assert found["arret_absent_osm"] == sorted(DIVERGENCES["arret_absent_osm"])
    assert len(found["arret_absent_gtfs"]) == len(DIVERGENCES["arret_absent_gtfs"])
    assert found["trace_different"] == DIVERGENCES["trace_different"]
    assert found["ligne_absente_osm"] == DIVERGENCES["ligne_absente_osm"]
    assert [r["osm_ref"] for r in report.gaps("ligne_absente_gtfs")] == ["W9"]
    assert found["nom_ligne_different"] == []
    assert report.totals["traces_apparies"] == 22
    # Each direction is matched with its own OSM relation, not with the reverse one.
    for match in report.route_matches:
        assert match.start_gap_m is not None and match.start_gap_m < 1

    geojson = gaps.geojson(report)
    assert '"ecart": "arret_deplace"' in geojson
    text = gaps.markdown(report, "GTFS fictif", "OSM fictif")
    assert "| Lignes d'OSM absentes du GTFS | 1 |" in text


def test_stops_and_routes_are_matched_by_osm_identity_first(
    pg_url: str, fictional_osm: str, manifest: Manifest, tmp_path: Path
) -> None:
    connection = connect(pg_url)
    cursor = connection.cursor()
    cursor.execute(
        "select osm_id, st_x(geom), st_y(geom) from staging_osm.transit_stop"
        " where kind = 'platform' order by osm_id limit 2"
    )
    (first, lon1, lat1), (second, lon2, lat2) = cursor.fetchall()
    cursor.execute(
        "select relation_id from staging_osm.route where ref = 'G1' order by relation_id limit 1"
    )
    relation = cursor.fetchone()[0]
    cursor.execute(
        "select st_x(geom), st_y(geom) from (select (st_dumppoints(st_linemerge(geom))).geom"
        " from staging_osm.route where relation_id = %s) p",
        (relation,),
    )
    points = cursor.fetchall()
    # The GTFS was « produced from OSM »: node/… stop ids, the route relation as shape id.
    # The second stop sits 30 m away in the GTFS: matched by identity, reported as moved.
    stops = (
        "stop_id,stop_name,stop_lat,stop_lon\n"
        f"node/{first},Arrêt un (fictif),{lat1},{lon1}\n"
        f"node/{second},Arrêt deux (fictif),{lat2 + 30 / 111_320},{lon2}\n"
        "node/999999,Arrêt disparu (fictif),2.05,-4.05\n"
    )
    shapes = "shape_id,shape_pt_lat,shape_pt_lon,shape_pt_sequence\n" + "".join(
        f"{relation},{lat},{lon},{index}\n" for index, (lon, lat) in enumerate(points)
    )
    files = {
        "stops.txt": stops,
        "routes.txt": "route_id,route_long_name,route_type\n1,Ligne (fictif),3\n",
        "trips.txt": f"route_id,service_id,trip_id,shape_id,direction_id\n1,s,t,{relation},0\n",
        "shapes.txt": shapes,
    }
    gtfs_run, _ = load_gtfs(
        connection, _gtfs_source("gtfs_osm"), _fictional_gtfs(tmp_path, files, "gtfs_osm")
    )
    report = gaps.build_report(cursor, manifest.city("lagune-fictive"), gtfs_run, fictional_osm)
    connection.rollback()
    connection.close()
    assert report.totals["arrets_apparies_par_identifiant"] == 2
    assert [r["gtfs_stop_id"] for r in report.gaps("arret_deplace")] == [f"node/{second}"]
    assert [r["gtfs_stop_id"] for r in report.gaps("arret_absent_osm")] == ["node/999999"]
    assert report.totals["traces_apparies_par_identifiant"] == 1
    assert report.gaps("trace_different") == []


def test_osm_places_are_promoted_once_with_their_aliases(
    pg_url: str, fictional_osm: str, manifest: Manifest
) -> None:
    source, city = manifest.source("osm_lagune_fictive"), manifest.city("lagune-fictive")
    connection = connect(pg_url)
    first = promote_places(connection, source, city, fictional_osm)
    assert first["lieux_crees"] == 25 and first["lieux_mis_a_jour"] == 0
    second = promote_places(connection, source, city, fictional_osm)
    assert (second["lieux_crees"], second["lieux_mis_a_jour"]) == (0, 25)
    assert second["alias_ajoutes"] == 0 and second["lieux_absents_du_dernier_import"] == 0
    cursor = connection.cursor()
    cursor.execute(
        """
        select a.alias_kind from network.place p join network.place_alias a on a.place_id = p.id
        where p.name = 'Pharmacie de la Lagune (fictif)' order by a.alias_kind, a.alias
        """
    )
    assert [row[0] for row in cursor.fetchall()] == ["abreviation", "autre", "nom"]
    cursor.execute(
        "select count(*) from network.place where external_ref like 'node/%%' and is_fictional"
    )
    assert cursor.fetchone()[0] == 25
    with pytest.raises(LookupError, match="staging_osm contient"):
        current_osm_run(cursor, "osm_cote_divoire")
    with pytest.raises(ValueError, match="fictives"):
        promote_places(connection, manifest.source("osm_cote_divoire"), city, fictional_osm)
    connection.close()

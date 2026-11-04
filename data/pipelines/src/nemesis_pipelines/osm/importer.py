"""Runs osm2pgsql with the nemesis flex style and records the import run."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any

from nemesis_pipelines.download import Fetched
from nemesis_pipelines.runs import finish_run, start_run
from nemesis_pipelines.sources import Source

STYLE = Path(__file__).with_name("nemesis.lua")
SCHEMA = "staging_osm"
TABLES = ("road", "poi", "transit_stop", "route", "route_master", "route_member", "boundary")


class Osm2pgsqlMissingError(RuntimeError):
    pass


def osm2pgsql_version(binary: str = "osm2pgsql") -> str:
    path = shutil.which(binary)
    if path is None:
        raise Osm2pgsqlMissingError(
            "osm2pgsql introuvable : « apt-get install osm2pgsql » (version 1.11 attendue)"
        )
    output = subprocess.run([path, "--version"], check=True, capture_output=True, text=True).stderr
    for token in output.split():
        if token[:1].isdigit() and token.count(".") == 2:
            return token
    return "inconnue"


def run_osm2pgsql(database_url: str, path: Path, cache_mb: int = 2000) -> None:
    """Full import (tables recreated); the RAM middle keeps a country extract fast."""
    subprocess.run(
        [
            "osm2pgsql",
            "--create",
            "--output=flex",
            f"--style={STYLE}",
            f"--schema={SCHEMA}",
            f"--cache={cache_mb}",
            "--log-level=warn",
            "-d",
            database_url,
            str(path),
        ],
        check=True,
    )


def table_counts(cursor: Any) -> dict[str, int]:
    counts = {}
    for table in TABLES:
        cursor.execute(f"select count(*) from {SCHEMA}.{table}")
        counts[table] = cursor.fetchone()[0]
    cursor.execute(f"select kind, count(*) from {SCHEMA}.transit_stop group by kind order by kind")
    counts_by_kind = {kind: total for kind, total in cursor.fetchall()}
    cursor.execute(f"select route, count(*) from {SCHEMA}.route group by route order by route")
    routes_by_mode = {mode: total for mode, total in cursor.fetchall()}
    return {**counts, "transit_stop_par_nature": counts_by_kind, "route_par_mode": routes_by_mode}


def data_timestamp(cursor: Any) -> str | None:
    """Replication timestamp of the extract, as stored by osm2pgsql (if the file has one)."""
    cursor.execute(
        f"select value from {SCHEMA}.osm2pgsql_properties where property = 'current_timestamp'"
    )
    row = cursor.fetchone()
    return row[0] if row else None


def import_osm(
    connection: Any,
    database_url: str,
    source: Source,
    fetched: Fetched,
    expected_version: str | None = None,
) -> tuple[str, dict[str, Any]]:
    version = osm2pgsql_version()
    if expected_version and version != expected_version:
        print(f"Attention : osm2pgsql {version}, style écrit et testé pour {expected_version}.")
    cursor = connection.cursor()
    run_id = start_run(cursor, source, fetched.provenance)
    connection.commit()
    try:
        run_osm2pgsql(database_url, fetched.path)
        counts = {**table_counts(cursor), "osm2pgsql": version}
        finish_run(cursor, run_id, counts, data_timestamp(cursor))
        connection.commit()
    except BaseException:
        connection.rollback()
        finish_run(cursor, run_id, {"osm2pgsql": version}, status="echec")
        connection.commit()
        raise
    return run_id, counts

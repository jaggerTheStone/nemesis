"""Import runs (ops.import_run): the provenance of everything a pipeline loads."""

from __future__ import annotations

import json
from typing import Any

from nemesis_pipelines.download import Provenance
from nemesis_pipelines.sources import Source


def ensure_source(cursor: Any, source: Source) -> None:
    """Declares the source and its licence in network.source (idempotent).

    A change of usage towards « evaluation » is refused by the database when network
    rows already depend on the source (migration 20261104000800).
    """
    cursor.execute(
        """
        insert into network.source (id, name, license, attribution, url, license_url, usage,
                                    is_fictional)
        values (%s, %s, %s, %s, %s, %s, %s, %s)
        on conflict (id) do update
            set name = excluded.name, license = excluded.license,
                attribution = excluded.attribution, url = excluded.url,
                license_url = excluded.license_url, usage = excluded.usage
        """,
        (
            source.id,
            source.name,
            source.license,
            source.attribution,
            source.page_url or source.url,
            source.license_url,
            source.usage,
            source.is_fictional,
        ),
    )


def start_run(cursor: Any, source: Source, provenance: Provenance) -> str:
    ensure_source(cursor, source)
    cursor.execute(
        """
        insert into ops.import_run (source_id, is_fictional, kind, url, file_name, sha256,
                                    size_bytes, verified_by, retrieved_at)
        values (%s, %s, %s, %s, %s, %s, %s, %s, %s::timestamptz)
        returning id::text
        """,
        (
            source.id,
            source.is_fictional,
            source.kind,
            provenance.url,
            provenance.file_name,
            provenance.sha256,
            provenance.size_bytes,
            provenance.verified_by,
            provenance.retrieved_at,
        ),
    )
    return cursor.fetchone()[0]


def finish_run(
    cursor: Any,
    run_id: str,
    counts: dict[str, Any],
    data_timestamp: str | None = None,
    status: str = "termine",
) -> None:
    cursor.execute(
        """
        update ops.import_run
           set status = %s, finished_at = now(), counts = %s::jsonb,
               data_timestamp = %s::timestamptz
         where id = %s::uuid
        """,
        (status, json.dumps(counts, ensure_ascii=False), data_timestamp, run_id),
    )


def latest_run(cursor: Any, source_id: str) -> str | None:
    """Most recent finished run of a source."""
    cursor.execute(
        """
        select id::text from ops.import_run
         where source_id = %s and status = 'termine'
         order by finished_at desc limit 1
        """,
        (source_id,),
    )
    row = cursor.fetchone()
    return row[0] if row else None


def current_osm_run(cursor: Any, source_id: str) -> str:
    """The run whose data is in staging_osm, which osm2pgsql recreates at each import.

    Refuses to go on when the last OSM import came from another source: a report or a
    promotion would otherwise mix two extracts.
    """
    cursor.execute(
        """
        select id::text, source_id, status from ops.import_run
         where kind = 'osm'
         order by started_at desc limit 1
        """
    )
    row = cursor.fetchone()
    if row is None:
        raise LookupError("aucun import OSM")
    run_id, current_source, status = row
    if status != "termine":
        raise LookupError(f"le dernier import OSM ({run_id}) est {status.replace('_', ' ')}")
    if current_source != source_id:
        raise LookupError(f"staging_osm contient l'import {run_id} de {current_source}")
    return run_id


def prune_gtfs_staging(cursor: Any, source_id: str, keep: int = 2) -> int:
    """Keeps the staged rows of the `keep` latest runs of a source; the runs stay listed."""
    cursor.execute(
        """
        delete from staging_gtfs.file
         where import_run_id in (
             select id from ops.import_run
              where source_id = %s and kind = 'gtfs'
              order by started_at desc offset %s)
        """,
        (source_id, keep),
    )
    return cursor.rowcount

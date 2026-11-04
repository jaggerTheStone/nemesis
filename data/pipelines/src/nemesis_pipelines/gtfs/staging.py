"""Loads a GTFS archive into staging_gtfs, exactly as published.

Nothing is corrected here: every row of every file is stored with its line number
and its values as text, so that the validator report and the gap report can point
at the original line. The typed views of staging_gtfs leave unreadable values null.
"""

from __future__ import annotations

import csv
import io
import json
import zipfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from nemesis_pipelines.download import Fetched
from nemesis_pipelines.runs import finish_run, prune_gtfs_staging, start_run
from nemesis_pipelines.sources import Source

EXTRA_KEY = "__extra__"


@dataclass
class GtfsFile:
    name: str
    columns: list[str]
    records: list[tuple[int, dict[str, Any]]] = field(default_factory=list)
    blank_lines: int = 0
    short_rows: int = 0
    long_rows: int = 0


@dataclass
class GtfsArchive:
    files: dict[str, GtfsFile]
    ignored: list[str]
    newest_member: datetime | None

    @property
    def feed_info(self) -> dict[str, Any] | None:
        info = self.files.get("feed_info.txt")
        return info.records[0][1] if info and info.records else None


def read_gtfs(path: Path) -> GtfsArchive:
    """Reads every root-level .txt file of the archive (UTF-8, BOM tolerated)."""
    files: dict[str, GtfsFile] = {}
    ignored: list[str] = []
    newest: datetime | None = None
    with zipfile.ZipFile(path) as archive:
        for info in archive.infolist():
            if info.is_dir():
                continue
            if "/" in info.filename or not info.filename.endswith(".txt"):
                ignored.append(info.filename)
                continue
            stamp = datetime(*info.date_time)
            newest = stamp if newest is None or stamp > newest else newest
            text = archive.read(info).decode("utf-8-sig")
            reader = csv.reader(io.StringIO(text, newline=""))
            header = next(reader, None)
            gtfs_file = GtfsFile(info.filename, list(header or []))
            for values in reader:
                if not values or values == [""]:
                    gtfs_file.blank_lines += 1
                    continue
                record: dict[str, Any] = dict(zip(gtfs_file.columns, values, strict=False))
                if len(values) > len(gtfs_file.columns):
                    record[EXTRA_KEY] = values[len(gtfs_file.columns) :]
                    gtfs_file.long_rows += 1
                elif len(values) < len(gtfs_file.columns):
                    gtfs_file.short_rows += 1
                gtfs_file.records.append((reader.line_num, record))
            files[info.filename] = gtfs_file
    return GtfsArchive(files=files, ignored=sorted(ignored), newest_member=newest)


def _copy_rows(cursor: Any, run_id: str, gtfs_file: GtfsFile) -> None:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    for line_no, record in gtfs_file.records:
        writer.writerow([run_id, gtfs_file.name, line_no, json.dumps(record, ensure_ascii=False)])
    buffer.seek(0)
    cursor.execute(
        "copy staging_gtfs.record (import_run_id, file_name, line_no, data)"
        " from stdin with (format csv)",
        stream=buffer,
    )


def summarise(archive: GtfsArchive) -> dict[str, Any]:
    """Volumes and reading anomalies, as recorded in ops.import_run.counts."""
    counts: dict[str, Any] = {
        "files": {name: len(f.records) for name, f in sorted(archive.files.items())},
    }
    anomalies = {
        name: {
            key: value
            for key, value in (
                ("lignes_vides", f.blank_lines),
                ("lignes_courtes", f.short_rows),
                ("lignes_longues", f.long_rows),
            )
            if value
        }
        for name, f in sorted(archive.files.items())
    }
    anomalies = {name: values for name, values in anomalies.items() if values}
    if anomalies:
        counts["anomalies_de_lecture"] = anomalies
    if archive.ignored:
        counts["fichiers_ignores"] = archive.ignored
    if archive.feed_info:
        counts["feed_info"] = {k: v for k, v in archive.feed_info.items() if k != EXTRA_KEY}
    return counts


def load_gtfs(connection: Any, source: Source, fetched: Fetched) -> tuple[str, dict[str, Any]]:
    """Loads the archive in one transaction; returns the run id and the recorded counts."""
    archive = read_gtfs(fetched.path)
    cursor = connection.cursor()
    try:
        run_id = start_run(cursor, source, fetched.provenance)
        for gtfs_file in archive.files.values():
            cursor.execute(
                "insert into staging_gtfs.file (import_run_id, file_name, columns, row_count)"
                " values (%s::uuid, %s, %s, %s)",
                (run_id, gtfs_file.name, gtfs_file.columns, len(gtfs_file.records)),
            )
            if gtfs_file.records:
                _copy_rows(cursor, run_id, gtfs_file)
        counts = summarise(archive)
        newest = archive.newest_member
        # Archive dates carry no time zone; Abidjan is on UTC all year.
        stamp = None if source.is_fictional or newest is None else f"{newest.isoformat()}Z"
        finish_run(cursor, run_id, counts, stamp)
        prune_gtfs_staging(cursor, source.id)
        connection.commit()
    except BaseException:
        connection.rollback()
        raise
    return run_id, counts

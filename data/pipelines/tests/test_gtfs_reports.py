"""GTFS reading (as published), validator summary and PMTiles measures (I0.7)."""

from __future__ import annotations

import gzip
import json
import zipfile
from pathlib import Path

import pytest

from nemesis_pipelines.gtfs.staging import EXTRA_KEY, read_gtfs, summarise
from nemesis_pipelines.gtfs.validator import markdown, read_report
from nemesis_pipelines.tiles import planetiler
from nemesis_pipelines.tiles.pmtiles import (
    Header,
    PmtilesError,
    header_bytes,
    parse_header,
    read_archive,
)


def _zip(path: Path, files: dict[str, bytes]) -> Path:
    with zipfile.ZipFile(path, "w") as archive:
        for name, content in files.items():
            archive.writestr(name, content)
    return path


def test_values_are_read_exactly_as_published(tmp_path: Path) -> None:
    archive = _zip(
        tmp_path / "gtfs.zip",
        {
            # BOM, CRLF, a quoted comma, a blank line, a short row and a long row.
            "stops.txt": "﻿stop_id,stop_name,stop_lat,stop_lon\r\n"
            'a,"Gare, Nord", 2.0 ,-4.0\r\n'
            "\r\n"
            "b,Arrêt B,abc,-4.1\r\n"
            "c,Arrêt C\r\n"
            "d,Arrêt D,2.1,-4.2,en trop\r\n".encode(),
            "dossier/routes.txt": b"route_id\n",
            "LISEZMOI.md": b"notes",
        },
    )
    gtfs = read_gtfs(archive)
    stops = gtfs.files["stops.txt"]
    assert stops.columns == ["stop_id", "stop_name", "stop_lat", "stop_lon"]
    records = dict(stops.records)
    assert records[2] == {
        "stop_id": "a",
        "stop_name": "Gare, Nord",
        "stop_lat": " 2.0 ",
        "stop_lon": "-4.0",
    }
    assert records[4]["stop_lat"] == "abc"  # kept as is: the validator reports it
    assert records[5] == {"stop_id": "c", "stop_name": "Arrêt C"}
    assert records[6][EXTRA_KEY] == ["en trop"]
    assert (stops.blank_lines, stops.short_rows, stops.long_rows) == (1, 1, 1)
    assert gtfs.ignored == ["LISEZMOI.md", "dossier/routes.txt"]
    counts = summarise(gtfs)
    assert counts["files"] == {"stops.txt": 4}
    assert counts["anomalies_de_lecture"]["stops.txt"] == {
        "lignes_vides": 1,
        "lignes_courtes": 1,
        "lignes_longues": 1,
    }


def test_the_fictional_gtfs_reads_completely(repository: Path, tmp_path: Path) -> None:
    from nemesis_pipelines.download import gtfs_zip

    archive = tmp_path / "fictif.zip"
    gtfs_zip(repository / "data/fixtures_fictives/gtfs", archive)
    gtfs = read_gtfs(archive)
    assert len(gtfs.files["stops.txt"].records) == 35
    assert all(f.blank_lines == f.short_rows == f.long_rows == 0 for f in gtfs.files.values())
    assert gtfs.feed_info and gtfs.feed_info["feed_lang"] == "fr"


def _report(directory: Path) -> Path:
    directory.mkdir()
    report = {
        "summary": {
            "validatorVersion": "8.0.1",
            "validatedAt": "2026-11-04T10:00:00Z",
            "counts": {"Stops": 4834, "Routes": 490},
        },
        "notices": [
            {
                "code": "feed_expiration_date30_days",
                "severity": "WARNING",
                "totalNotices": 1,
                "sampleNotices": [{"feedEndDate": "20231231"}],
            },
            {"code": "unusable_trip", "severity": "INFO", "totalNotices": 3},
            {
                "code": "block_trips_with_overlapping_stop_times",
                "severity": "ERROR",
                "totalNotices": 12,
                "sampleNotices": [{"csvRowNumber": index} for index in range(15)],
            },
            {
                "code": "missing_required_field",
                "severity": "ERROR",
                "totalNotices": 2,
                "sampleNotices": [{"filename": "stops.txt", "csvRowNumber": 7}],
            },
        ],
    }
    (directory / "report.json").write_text(json.dumps(report), encoding="utf-8")
    return directory


def test_every_validator_notice_is_listed_errors_first(tmp_path: Path) -> None:
    summary = read_report(_report(tmp_path / "rapport"))
    assert [n.code for n in summary.notices] == [
        "block_trips_with_overlapping_stop_times",
        "missing_required_field",
        "feed_expiration_date30_days",
        "unusable_trip",
    ]
    assert summary.total("ERROR") == 14
    text = markdown(summary, "GTFS de test")
    assert "Aucune correction automatique" in text
    for notice in summary.notices:
        assert f"`{notice.code}`" in text
    assert '{"csvRowNumber": 7, "filename": "stops.txt"}' in text
    # Ten samples at most, then a pointer to the full HTML report.
    assert "… 2 autre(s) : voir report.html" in text
    assert "| Erreur | 2 | 14 |" in text


def test_validator_errors_of_its_own_are_shown(tmp_path: Path) -> None:
    directory = _report(tmp_path / "rapport")
    (directory / "system_errors.json").write_text(
        json.dumps({"notices": [{"code": "i_o_error", "severity": "ERROR", "totalNotices": 1}]}),
        encoding="utf-8",
    )
    text = markdown(read_report(directory), "GTFS de test")
    assert "Erreurs du validateur lui-même" in text and "`i_o_error`" in text


# --- PMTiles -----------------------------------------------------------------------------


def _header(**values: object) -> Header:
    base = dict(
        root_directory=(127, 50),
        metadata=(177, 0),
        leaf_directories=(0, 0),
        tile_data=(1000, 2_000_000),
        addressed_tiles=4000,
        tile_entries=3500,
        tile_contents=3000,
        clustered=True,
        internal_compression="gzip",
        tile_compression="gzip",
        tile_type="mvt",
        min_zoom=0,
        max_zoom=14,
        bounds=(-4.25, 5.18, -3.7, 5.53),
        center_zoom=12,
        center=(-3.975, 5.355),
    )
    base.update(values)
    return Header(**base)  # type: ignore[arg-type]


def test_a_pmtiles_header_round_trips() -> None:
    header = _header()
    data = header_bytes(header)
    assert len(data) == 127
    assert parse_header(data) == header


@pytest.mark.parametrize(
    ("data", "message"),
    [
        (b"PMTiles", "trop court"),
        (b"MBTiles" + bytes(120), "pas une archive"),
        (b"PMTiles\x02" + bytes(119), "version 2"),
    ],
)
def test_a_bad_archive_is_refused(data: bytes, message: str) -> None:
    with pytest.raises(PmtilesError, match=message):
        parse_header(data)


def _archive(path: Path, size: int, metadata: dict[str, object]) -> Path:
    raw = gzip.compress(json.dumps(metadata).encode())
    header = _header(metadata=(127, len(raw)))
    path.write_bytes(header_bytes(header) + raw + bytes(max(0, size - 127 - len(raw))))
    return path


def test_archives_are_measured_against_the_f12_budget(tmp_path: Path) -> None:
    metadata = {
        "attribution": "© les contributeurs d'OpenStreetMap",
        "vector_layers": [{"id": "roads"}, {"id": "water"}],
    }
    header, read = read_archive(_archive(tmp_path / "a.pmtiles", 1000, metadata))
    assert header.max_zoom == 14 and read == metadata

    city = planetiler.measure(_archive(tmp_path / "ville.pmtiles", 30_000_000, metadata), "ville")
    country = planetiler.measure(_archive(tmp_path / "pays.pmtiles", 90_000_000, metadata), "pays")
    assert city.layers == ("roads", "water")
    text = planetiler.markdown([country, city], "ville")
    assert planetiler.BASEMAP_BUDGET_MB == 45
    assert "| ville.pmtiles | 30.0 Mo | 0–14 | 3000 | roads, water | dans le budget |" in text
    assert "sans objet (pays entier)" in text
    big = planetiler.measure(_archive(tmp_path / "gros.pmtiles", 46_000_000, metadata), "gros")
    assert "**hors budget**" in planetiler.markdown([big], "gros")
    assert json.loads(planetiler.to_json([city]))[0]["size_mb"] == 30.0


def test_the_basemap_schema_has_no_heavy_layer(repository: Path) -> None:
    schema = planetiler.SCHEMA.read_text(encoding="utf-8")
    layers = [
        line.split(":", 1)[1].strip()
        for line in schema.splitlines()
        if line.lstrip().startswith("- id:")
    ]
    assert layers == [
        "water",
        "waterways",
        "green",
        "boundaries",
        "places",
        "roads",
        "railways",
        "ferries",
        "transit",
    ]
    assert "les contributeurs d'OpenStreetMap" in schema
    assert "url:" not in schema  # OSM only, from the verified local extract

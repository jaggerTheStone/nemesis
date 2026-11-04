"""Reads the header and metadata of a PMTiles v3 archive (specification v3.0).

Enough to measure a basemap against the F-12 budget and to check what it contains
(zooms, bounds, layers, attribution) without any external tool.
"""

from __future__ import annotations

import gzip
import json
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Any

HEADER_SIZE = 127
_LAYOUT = struct.Struct("<7sB11Q4B2B4iB2i")
COMPRESSIONS = {0: "inconnue", 1: "aucune", 2: "gzip", 3: "brotli", 4: "zstd"}
TILE_TYPES = {0: "inconnu", 1: "mvt", 2: "png", 3: "jpeg", 4: "webp", 5: "avif"}


class PmtilesError(ValueError):
    pass


@dataclass(frozen=True)
class Header:
    root_directory: tuple[int, int]
    metadata: tuple[int, int]
    leaf_directories: tuple[int, int]
    tile_data: tuple[int, int]
    addressed_tiles: int
    tile_entries: int
    tile_contents: int
    clustered: bool
    internal_compression: str
    tile_compression: str
    tile_type: str
    min_zoom: int
    max_zoom: int
    bounds: tuple[float, float, float, float]
    center_zoom: int
    center: tuple[float, float]


def parse_header(data: bytes) -> Header:
    if len(data) < HEADER_SIZE:
        raise PmtilesError("fichier trop court pour un en-tête PMTiles")
    fields = _LAYOUT.unpack(data[:HEADER_SIZE])
    magic, version = fields[0], fields[1]
    if magic != b"PMTiles":
        raise PmtilesError("ce n'est pas une archive PMTiles")
    if version != 3:
        raise PmtilesError(f"PMTiles version {version} non prise en charge (version 3 attendue)")
    offsets = fields[2:13]
    clustered, internal, tile_compression, tile_type = fields[13:17]
    min_zoom, max_zoom = fields[17], fields[18]
    min_lon, min_lat, max_lon, max_lat = (value / 1e7 for value in fields[19:23])
    center_zoom = fields[23]
    center_lon, center_lat = fields[24] / 1e7, fields[25] / 1e7
    return Header(
        root_directory=(offsets[0], offsets[1]),
        metadata=(offsets[2], offsets[3]),
        leaf_directories=(offsets[4], offsets[5]),
        tile_data=(offsets[6], offsets[7]),
        addressed_tiles=offsets[8],
        tile_entries=offsets[9],
        tile_contents=offsets[10],
        clustered=bool(clustered),
        internal_compression=COMPRESSIONS.get(internal, str(internal)),
        tile_compression=COMPRESSIONS.get(tile_compression, str(tile_compression)),
        tile_type=TILE_TYPES.get(tile_type, str(tile_type)),
        min_zoom=min_zoom,
        max_zoom=max_zoom,
        bounds=(min_lon, min_lat, max_lon, max_lat),
        center_zoom=center_zoom,
        center=(center_lon, center_lat),
    )


def header_bytes(header: Header) -> bytes:
    """Inverse of parse_header (used by the tests to build archives)."""
    codes = {v: k for k, v in COMPRESSIONS.items()}
    types = {v: k for k, v in TILE_TYPES.items()}
    return _LAYOUT.pack(
        b"PMTiles",
        3,
        *header.root_directory,
        *header.metadata,
        *header.leaf_directories,
        *header.tile_data,
        header.addressed_tiles,
        header.tile_entries,
        header.tile_contents,
        int(header.clustered),
        codes[header.internal_compression],
        codes[header.tile_compression],
        types[header.tile_type],
        header.min_zoom,
        header.max_zoom,
        *(round(value * 1e7) for value in header.bounds),
        header.center_zoom,
        *(round(value * 1e7) for value in header.center),
    )


def read_archive(path: Path) -> tuple[Header, dict[str, Any]]:
    """Header and JSON metadata (vector layers, attribution…) of an archive."""
    with path.open("rb") as handle:
        header = parse_header(handle.read(HEADER_SIZE))
        offset, length = header.metadata
        handle.seek(offset)
        raw = handle.read(length)
    if header.internal_compression == "gzip":
        raw = gzip.decompress(raw)
    elif header.internal_compression not in ("aucune", "inconnue"):
        raise PmtilesError(f"compression interne {header.internal_compression} non lue")
    metadata = json.loads(raw.decode("utf-8")) if raw else {}
    return header, metadata

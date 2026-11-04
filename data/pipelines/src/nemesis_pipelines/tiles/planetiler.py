"""Builds the light basemap with Planetiler (pinned image) and measures it against F-12.

F-12: the Abidjan city pack must stay under 15 Mo without basemap and under 60 Mo
with the light basemap, so the basemap itself gets at most 45 Mo. Sizes are in
megabytes of 10⁶ bytes, the stricter reading of « Mo ».
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from nemesis_pipelines.tiles.pmtiles import read_archive

SCHEMA = Path(__file__).with_name("basemap.yml")
PACK_WITH_BASEMAP_MB = 60.0
PACK_WITHOUT_BASEMAP_MB = 15.0
BASEMAP_BUDGET_MB = PACK_WITH_BASEMAP_MB - PACK_WITHOUT_BASEMAP_MB
MAX_ZOOM = 14


@dataclass(frozen=True)
class TileMeasure:
    name: str
    path: str
    size_bytes: int
    min_zoom: int
    max_zoom: int
    bounds: tuple[float, float, float, float]
    tile_contents: int
    addressed_tiles: int
    layers: tuple[str, ...]
    attribution: str | None

    @property
    def size_mb(self) -> float:
        return self.size_bytes / 1e6


def _docker_user() -> list[str]:
    return ["--user", f"{os.getuid()}:{os.getgid()}"]


def verify_schema(image: str, schema: Path = SCHEMA) -> None:
    """Runs the examples of the schema (`planetiler verify`)."""
    schema = schema.resolve()
    subprocess.run(
        [
            "docker",
            "run",
            "--rm",
            *_docker_user(),
            "-v",
            f"{schema.parent}:/schema:ro",
            image,
            "verify",
            f"/schema/{schema.name}",
        ],
        check=True,
    )


def to_pbf(path: Path, work_dir: Path) -> Path:
    """Planetiler reads PBF only: converts an OSM XML file with osmium."""
    if path.suffix != ".osm":
        return path
    if shutil.which("osmium") is None:
        raise RuntimeError("osmium introuvable : « apt-get install osmium-tool »")
    target = work_dir / "sources" / f"{path.stem}.osm.pbf"
    target.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["osmium", "cat", str(path), "-o", str(target), "--overwrite"], check=True)
    return target


def generate(
    image: str,
    osm_pbf: Path,
    work_dir: Path,
    name: str,
    bounds: tuple[float, float, float, float] | None = None,
    heap: str = "3g",
    schema: Path = SCHEMA,
) -> Path:
    """Runs Planetiler; the archive lands in `work_dir/tiles/<name>.pmtiles`."""
    work_dir = work_dir.resolve()
    osm_pbf = osm_pbf.resolve()
    schema = schema.resolve()
    if not osm_pbf.is_relative_to(work_dir):
        raise ValueError(f"{osm_pbf} doit être sous {work_dir}")
    (work_dir / "tiles").mkdir(parents=True, exist_ok=True)
    (work_dir / "tmp").mkdir(parents=True, exist_ok=True)
    output = work_dir / "tiles" / f"{name}.pmtiles"
    command = [
        "docker",
        "run",
        "--rm",
        *_docker_user(),
        "-e",
        f"JAVA_TOOL_OPTIONS=-Xmx{heap}",
        "-v",
        f"{work_dir}:/data",
        "-v",
        f"{schema.parent}:/schema:ro",
        image,
        "generate-custom",
        f"--schema=/schema/{schema.name}",
        f"--osm_path=/data/{osm_pbf.relative_to(work_dir)}",
        f"--output=/data/tiles/{name}.pmtiles",
        f"--maxzoom={MAX_ZOOM}",
        "--tmpdir=/data/tmp",
        "--force",
    ]
    if bounds:
        command.append("--bounds=" + ",".join(f"{value:g}" for value in bounds))
    subprocess.run(command, check=True)
    return output


def measure(path: Path, name: str) -> TileMeasure:
    header, metadata = read_archive(path)
    layers = tuple(sorted(layer.get("id", "?") for layer in metadata.get("vector_layers", [])))
    return TileMeasure(
        name=name,
        path=str(path),
        size_bytes=path.stat().st_size,
        min_zoom=header.min_zoom,
        max_zoom=header.max_zoom,
        bounds=header.bounds,
        tile_contents=header.tile_contents,
        addressed_tiles=header.addressed_tiles,
        layers=layers,
        attribution=metadata.get("attribution"),
    )


def markdown(measures: list[TileMeasure], city_extract: str) -> str:
    lines = [
        "# Tuiles du fond léger",
        "",
        f"Budget de F-12 : pack ville sous {PACK_WITHOUT_BASEMAP_MB:.0f} Mo sans fond et sous"
        f" {PACK_WITH_BASEMAP_MB:.0f} Mo avec le fond léger, donc au plus"
        f" {BASEMAP_BUDGET_MB:.0f} Mo pour le fond lui-même (1 Mo = 10⁶ octets).",
        "",
        "| Archive | Taille | Zooms | Tuiles distinctes | Couches | Budget |",
        "|---------|--------|-------|-------------------|---------|--------|",
    ]
    for item in measures:
        if item.name == city_extract:
            verdict = "dans le budget" if item.size_mb <= BASEMAP_BUDGET_MB else "**hors budget**"
        else:
            verdict = "sans objet (pays entier)"
        lines.append(
            f"| {item.name}.pmtiles | {item.size_mb:.1f} Mo | {item.min_zoom}–{item.max_zoom}"
            f" | {item.tile_contents} | {', '.join(item.layers)} | {verdict} |"
        )
    attributions = sorted({m.attribution for m in measures if m.attribution})
    if attributions:
        lines += ["", "Attribution inscrite dans les archives : " + " ; ".join(attributions)]
    return "\n".join(lines) + "\n"


def to_json(measures: list[TileMeasure]) -> str:
    def entry(item: TileMeasure) -> dict[str, Any]:
        return {**asdict(item), "size_mb": round(item.size_mb, 2)}

    return json.dumps([entry(m) for m in measures], ensure_ascii=False, indent=2) + "\n"

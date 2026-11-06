"""Builds a city pack: what `routing plan --data <pack>` reads (I0.9).

    pack/
      pack.json        city, network version, fictional or not, usage, sources
      gtfs/            the GTFS feed, extension files included (ADR-007)
      walk_nodes.csv   OSM walking graph: nodes
      walk_edges.csv   OSM walking graph: edges, in metres

The real pack keeps the usage of its most restricted source: built from the GTFS
« Abidjan 2023 », it is for internal evaluation only (H-030).
"""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path
from typing import Any

from nemesis_pipelines.pack.walkgraph import WalkGraph, build_graph, ways_from_geojsonseq

PACK_FORMAT = 1


def pack_json(
    city: str,
    network_version: str,
    is_fictional: bool,
    usage: str,
    gtfs: str,
    sources: list[dict[str, Any]],
) -> str:
    content = {
        "format": PACK_FORMAT,
        "city": city,
        "network_version": network_version,
        "is_fictional": is_fictional,
        "usage": usage,
        "gtfs": gtfs,
        "walk_nodes": "walk_nodes.csv",
        "walk_edges": "walk_edges.csv",
        "sources": sources,
    }
    return json.dumps(content, ensure_ascii=False, indent=2) + "\n"


def write_graph(graph: WalkGraph, directory: Path) -> None:
    (directory / "walk_nodes.csv").write_text(graph.nodes_csv(), encoding="utf-8")
    (directory / "walk_edges.csv").write_text(graph.edges_csv(), encoding="utf-8")


def walk_graph_from_pbf(pbf: Path, bbox: tuple[float, float, float, float]) -> WalkGraph:
    """Clips the extract to the city, keeps the highways, reads them with osmium."""
    if shutil.which("osmium") is None:
        raise RuntimeError("osmium introuvable : « apt-get install osmium-tool »")
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        box = ",".join(f"{v:g}" for v in bbox)
        subprocess.run(
            ["osmium", "extract", "--bbox", box, "-o", str(work / "ville.osm.pbf"), str(pbf)],
            check=True,
        )
        subprocess.run(
            [
                "osmium",
                "tags-filter",
                "-o",
                str(work / "voies.osm.pbf"),
                str(work / "ville.osm.pbf"),
                "w/highway",
            ],
            check=True,
        )
        subprocess.run(
            [
                "osmium",
                "export",
                "-f",
                "geojsonseq",
                "--geometry-types=linestring",
                "-o",
                str(work / "voies.geojsonseq"),
                str(work / "voies.osm.pbf"),
            ],
            check=True,
        )
        return build_graph(ways_from_geojsonseq(work / "voies.geojsonseq"))


def build_real_pack(
    out: Path,
    city: str,
    bbox: tuple[float, float, float, float],
    gtfs_zip: Path,
    osm_pbf: Path,
    provenances: list[dict[str, Any]],
) -> dict:
    if out.exists():
        shutil.rmtree(out)
    (out / "gtfs").mkdir(parents=True)
    with zipfile.ZipFile(gtfs_zip) as archive:
        for member in archive.infolist():
            if (
                not member.is_dir()
                and "/" not in member.filename
                and member.filename.endswith(".txt")
            ):
                (out / "gtfs" / member.filename).write_bytes(archive.read(member))
    graph = walk_graph_from_pbf(osm_pbf, bbox)
    write_graph(graph, out)
    usage = "evaluation" if any(p["usage"] == "evaluation" for p in provenances) else "produit"
    version = "+".join(f"{p['source_id']}@{p['sha256'][:12]}" for p in provenances)
    sources = [
        {
            k: p.get(k)
            for k in (
                "source_id",
                "url",
                "sha256",
                "retrieved_at",
                "license",
                "attribution",
                "usage",
            )
        }
        for p in provenances
    ]
    (out / "pack.json").write_text(
        pack_json(city, version, False, usage, "gtfs", sources), encoding="utf-8"
    )
    return {"noeuds": len(graph.nodes), "troncons": len(graph.edges), "usage": usage}

"""Command line `nemesis-data` (I0.7): downloads, imports, reports and tiles.

    nemesis-data chaine reel            the whole chain on the real sources (network)
    nemesis-data chaine fictif          the same on the fictional data of the repository

Each step also has its own command (telecharger, valider-gtfs, importer-gtfs,
importer-osm, promouvoir-lieux, rapport-ecarts, tuiles, verifier-schema-tuiles).
Reports land in <travail>/rapports/<profil>/ ; tiles in <travail>/tiles/.
The database URL comes from --base or DATABASE_URL.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from nemesis_pipelines.download import Fetched, fetch
from nemesis_pipelines.gtfs import validator
from nemesis_pipelines.gtfs.staging import load_gtfs
from nemesis_pipelines.osm.importer import import_osm
from nemesis_pipelines.osm.places import promote_places
from nemesis_pipelines.pack.build import build_real_pack
from nemesis_pipelines.reports import gaps
from nemesis_pipelines.runs import current_osm_run, latest_run
from nemesis_pipelines.sources import MANIFEST_PATH, Manifest, Source, load_manifest
from nemesis_pipelines.tiles import planetiler


class Context:
    def __init__(self, args: argparse.Namespace) -> None:
        self.manifest: Manifest = load_manifest(args.manifeste)
        self.work: Path = args.travail
        self.root: Path = args.racine
        self.database_url: str | None = args.base or os.environ.get("DATABASE_URL")

    def connect(self) -> Any:
        if not self.database_url:
            raise SystemExit("Base absente : passer --base ou définir DATABASE_URL.")
        from nemesis_schema.connection import connect

        return connect(self.database_url)

    def fetch(self, source: Source) -> Fetched:
        fetched = fetch(source, self.work, root=self.root)
        p = fetched.provenance
        print(
            f"{source.id} : {p.file_name}, {p.size_bytes} octets, sha256 {p.sha256[:12]}…,"
            f" vérifié ({p.verified_by})"
        )
        return fetched

    def reports(self, name: str) -> Path:
        directory = self.work / "rapports" / name
        directory.mkdir(parents=True, exist_ok=True)
        return directory


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"Écrit : {path}")


def validate_gtfs(ctx: Context, source: Source, fetched: Fetched, out: Path) -> dict[str, int]:
    directory = out / "validation-gtfs"
    validator.run_validator(
        ctx.manifest.tool("gtfs_validator"),
        fetched.path,
        directory,
        None if source.is_fictional else "ci",
    )
    summary = validator.read_report(directory)
    _write(directory / "resume.md", validator.markdown(summary, source.name))
    totals = {severity: summary.total(severity) for severity in validator.SEVERITIES}
    print("Avis du validateur : " + ", ".join(f"{k} {v}" for k, v in totals.items()))
    return totals


def gap_report(ctx: Context, gtfs: Source, osm: Source, city_code: str, out: Path) -> dict:
    connection = ctx.connect()
    try:
        cursor = connection.cursor()
        gtfs_run = latest_run(cursor, gtfs.id)
        if gtfs_run is None:
            raise SystemExit(f"Importer d'abord le GTFS {gtfs.id}.")
        try:
            osm_run = current_osm_run(cursor, osm.id)
        except LookupError as error:
            raise SystemExit(f"Importer d'abord l'extrait {osm.id} : {error}.") from None
        report = gaps.build_report(cursor, ctx.manifest.city(city_code), gtfs_run, osm_run)
        connection.rollback()
    finally:
        connection.close()
    _write(out / "ecarts.md", gaps.markdown(report, gtfs.name, osm.name))
    _write(out / "ecarts.geojson", gaps.geojson(report))
    return report.totals


def build_tiles(
    ctx: Context, osm: Source, fetched: Fetched, city_code: str, out: Path, country: bool
) -> list[planetiler.TileMeasure]:
    image = ctx.manifest.tool("planetiler")
    planetiler.verify_schema(image)
    city = ctx.manifest.city(city_code)
    pbf = planetiler.to_pbf(fetched.path, ctx.work)
    targets: list[tuple[str, tuple[float, float, float, float] | None]] = [(city.code, city.bbox)]
    if country:
        targets.insert(0, (osm.id, None))
    measures = []
    for name, bounds in targets:
        path = planetiler.generate(image, pbf, ctx.work, name, bounds)
        measures.append(planetiler.measure(path, name))
    _write(out / "tuiles.md", planetiler.markdown(measures, city.code))
    _write(out / "tuiles.json", planetiler.to_json(measures))
    return measures


def run_chain(ctx: Context, profile_name: str, validate: bool, tiles: bool) -> int:
    profile = ctx.manifest.profile(profile_name)
    gtfs = ctx.manifest.source(profile.gtfs)
    osm = ctx.manifest.source(profile.osm)
    out = ctx.reports(profile_name)
    volumes: dict[str, Any] = {"profil": profile_name, "ville": profile.city}

    gtfs_file, osm_file = ctx.fetch(gtfs), ctx.fetch(osm)
    volumes["sources"] = {
        s.id: json.loads(f.provenance.to_json()) for s, f in ((gtfs, gtfs_file), (osm, osm_file))
    }
    if validate:
        volumes["validation_gtfs"] = validate_gtfs(ctx, gtfs, gtfs_file, out)

    connection = ctx.connect()
    try:
        gtfs_run, gtfs_counts = load_gtfs(connection, gtfs, gtfs_file)
        print(f"GTFS en staging : import {gtfs_run}")
        assert ctx.database_url is not None
        osm_run, osm_counts = import_osm(
            connection, ctx.database_url, osm, osm_file, ctx.manifest.tool("osm2pgsql")
        )
        print(f"OSM en staging : import {osm_run}")
        volumes["gtfs"] = {"import": gtfs_run, **gtfs_counts}
        volumes["osm"] = {"import": osm_run, **osm_counts}
        if profile.promote_places:
            city = ctx.manifest.city(profile.city)
            volumes["lieux"] = promote_places(connection, osm, city, osm_run)
            print(f"Lieux : {volumes['lieux']}")
    finally:
        connection.close()

    volumes["ecarts"] = gap_report(ctx, gtfs, osm, profile.city, out)
    if tiles:
        measures = build_tiles(ctx, osm, osm_file, profile.city, out, country=not osm.is_fictional)
        volumes["tuiles"] = {m.name: round(m.size_mb, 2) for m in measures}
    _write(out / "volumes.json", json.dumps(volumes, ensure_ascii=False, indent=2) + "\n")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="nemesis-data", description=__doc__.splitlines()[0])
    parser.add_argument("--manifeste", type=Path, default=MANIFEST_PATH)
    parser.add_argument("--travail", type=Path, default=Path("data/work"))
    parser.add_argument("--racine", type=Path, default=Path("."), help="racine du dépôt")
    parser.add_argument("--base", help="URL PostgreSQL (sinon DATABASE_URL)")
    commands = parser.add_subparsers(dest="command", required=True)

    chain = commands.add_parser("chaine", help="toute la chaîne d'un profil (reel, fictif)")
    chain.add_argument("profil")
    chain.add_argument(
        "--sans-validation",
        action="store_true",
        help="sans le validateur GTFS (image Docker requise)",
    )
    chain.add_argument(
        "--sans-tuiles", action="store_true", help="sans Planetiler (image Docker requise)"
    )

    download = commands.add_parser("telecharger", help="télécharger et vérifier des sources")
    download.add_argument("sources", nargs="+")

    for name, text in (
        ("valider-gtfs", "valider un GTFS"),
        ("importer-gtfs", "GTFS en staging"),
        ("importer-osm", "extrait OSM en staging"),
    ):
        command = commands.add_parser(name, help=text)
        command.add_argument("source")

    promote = commands.add_parser("promouvoir-lieux", help="points d'intérêt OSM → network.place")
    promote.add_argument("--source", required=True)
    promote.add_argument("--ville", required=True)

    report = commands.add_parser("rapport-ecarts", help="rapport d'écarts GTFS ↔ OSM")
    report.add_argument("--gtfs", required=True)
    report.add_argument("--osm", required=True)
    report.add_argument("--ville", required=True)

    tiles = commands.add_parser("tuiles", help="fond léger en PMTiles et mesure de taille")
    tiles.add_argument("--source", required=True)
    tiles.add_argument("--ville", required=True)
    tiles.add_argument("--pays", action="store_true", help="aussi l'archive de tout l'extrait")

    commands.add_parser("verifier-schema-tuiles", help="exemples du schéma Planetiler")

    pack = commands.add_parser("pack", help="pack ville du moteur d'itinéraires (profil reel)")
    pack.add_argument("profil")
    pack.add_argument(
        "--sortie", type=Path, help="dossier du pack (défaut : <travail>/packs/<profil>)"
    )

    args = parser.parse_args(argv)
    ctx = Context(args)
    manifest = ctx.manifest

    if args.command == "chaine":
        return run_chain(ctx, args.profil, not args.sans_validation, not args.sans_tuiles)
    if args.command == "telecharger":
        for source_id in args.sources:
            ctx.fetch(manifest.source(source_id))
        return 0
    if args.command == "pack":
        profile = manifest.profile(args.profil)
        gtfs, osm = manifest.source(profile.gtfs), manifest.source(profile.osm)
        if gtfs.is_fictional:
            raise SystemExit("Le pack fictif est versionné : data/fixtures_fictives/pack.")
        gtfs_file, osm_file = ctx.fetch(gtfs), ctx.fetch(osm)
        out = args.sortie or ctx.work / "packs" / args.profil
        city = manifest.city(profile.city)
        provenances = [json.loads(f.provenance.to_json()) for f in (gtfs_file, osm_file)]
        summary = build_real_pack(
            out, city.code, city.bbox, gtfs_file.path, osm_file.path, provenances
        )
        print(f"Pack écrit dans {out} : {summary}")
        return 0
    if args.command == "verifier-schema-tuiles":
        planetiler.verify_schema(manifest.tool("planetiler"))
        return 0
    if args.command == "valider-gtfs":
        source = manifest.source(args.source)
        validate_gtfs(ctx, source, ctx.fetch(source), ctx.reports(source.id))
        return 0
    if args.command in ("importer-gtfs", "importer-osm"):
        source = manifest.source(args.source)
        fetched = ctx.fetch(source)
        connection = ctx.connect()
        try:
            if args.command == "importer-gtfs":
                run_id, counts = load_gtfs(connection, source, fetched)
            else:
                assert ctx.database_url is not None
                run_id, counts = import_osm(
                    connection, ctx.database_url, source, fetched, manifest.tool("osm2pgsql")
                )
        finally:
            connection.close()
        print(json.dumps({"import": run_id, **counts}, ensure_ascii=False, indent=2))
        return 0
    if args.command == "promouvoir-lieux":
        source = manifest.source(args.source)
        connection = ctx.connect()
        try:
            try:
                run_id = current_osm_run(connection.cursor(), source.id)
            except LookupError as error:
                raise SystemExit(f"Importer d'abord l'extrait {source.id} : {error}.") from None
            print(promote_places(connection, source, manifest.city(args.ville), run_id))
        finally:
            connection.close()
        return 0
    if args.command == "rapport-ecarts":
        gtfs, osm = manifest.source(args.gtfs), manifest.source(args.osm)
        totals = gap_report(ctx, gtfs, osm, args.ville, ctx.reports(args.ville))
        print(json.dumps(totals, ensure_ascii=False, indent=2))
        return 0
    if args.command == "tuiles":
        source = manifest.source(args.source)
        build_tiles(ctx, source, ctx.fetch(source), args.ville, ctx.reports(args.ville), args.pays)
        return 0
    raise AssertionError(args.command)


if __name__ == "__main__":
    sys.exit(main())

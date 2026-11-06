"""Command line: `nemesis-fixtures generer [--verifier]` and `verifier-rapport`.

`generer` writes the fictional GTFS, the SQL seed, the fictional OSM extract, the city
pack of the routing engine and the data embedded in the mobile prototype.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from nemesis_pipelines.fixtures.city import build_city
from nemesis_pipelines.fixtures.gtfs import FEED_VERSION, gtfs_files
from nemesis_pipelines.fixtures.mobile import ASSETS, mobile_files
from nemesis_pipelines.fixtures.osm import osm_xml
from nemesis_pipelines.fixtures.sql import seed_sql
from nemesis_pipelines.pack.build import pack_json
from nemesis_pipelines.pack.walkgraph import build_graph, ways_from_osm_xml

GTFS_DIR = Path("data/fixtures_fictives/gtfs")
SEED_PATH = Path("data/fixtures_fictives/db/seed.sql")
OSM_PATH = Path("data/fixtures_fictives/osm/lagune-fictive.osm")
PACK_DIR = Path("data/fixtures_fictives/pack")


def generated_files() -> dict[Path, str]:
    city = build_city()
    gtfs = gtfs_files(city)
    files = {GTFS_DIR / name: content for name, content in gtfs.items()}
    files[SEED_PATH] = seed_sql(city)
    files[OSM_PATH] = osm_xml(city)
    # City pack of the routing engine (I0.9): the GTFS above and the walking graph.
    graph = build_graph(ways_from_osm_xml(files[OSM_PATH]))
    files[PACK_DIR / "walk_nodes.csv"] = graph.nodes_csv()
    files[PACK_DIR / "walk_edges.csv"] = graph.edges_csv()
    files[PACK_DIR / "pack.json"] = pack_json(
        "lagune-fictive",
        FEED_VERSION,
        True,
        "produit",
        "../gtfs",
        [{"source_id": "fixtures_fictives", "license": "Données de test, sans valeur réelle"}],
    )
    # Data of the mobile prototype (I0.11): the same pack, with its GTFS beside it.
    pack = {
        "walk_nodes.csv": files[PACK_DIR / "walk_nodes.csv"],
        "walk_edges.csv": files[PACK_DIR / "walk_edges.csv"],
        "pack.json": pack_json(
            "lagune-fictive",
            FEED_VERSION,
            True,
            "produit",
            "gtfs",
            [{"source_id": "fixtures_fictives", "license": "Données de test, sans valeur réelle"}],
        ),
    }
    files.update(mobile_files(city, gtfs, files[OSM_PATH], pack, FEED_VERSION))
    return files


def _generate(root: Path, check: bool) -> int:
    expected = generated_files()
    outdated = []
    for relative, content in expected.items():
        path = root / relative
        current = path.read_bytes().decode("utf-8") if path.exists() else None
        if current != content:
            outdated.append(relative)
            if not check:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8", newline="")
    stale = sorted(
        p
        for folder in (GTFS_DIR, ASSETS / "pack" / "gtfs")
        for p in (root / folder).glob("*.txt")
        if p.relative_to(root) not in expected
    )
    if check and (outdated or stale):
        print("Jeu fictif à régénérer avec « uv run nemesis-fixtures generer » :", file=sys.stderr)
        for relative in [*outdated, *(p.relative_to(root) for p in stale)]:
            print(f"  {relative}", file=sys.stderr)
        return 1
    for path in stale:
        path.unlink()
    if not check:
        print(f"{len(outdated)} fichier(s) mis à jour, {len(stale)} supprimé(s).")
    return 0


def _check_report(path: Path) -> int:
    """Summarises a MobilityData validator report; fails on any ERROR notice."""
    report = json.loads(path.read_text(encoding="utf-8"))
    notices = report.get("notices", [])
    errors = 0
    for notice in sorted(notices, key=lambda n: (n.get("severity", ""), n.get("code", ""))):
        severity, code, total = (
            notice.get("severity"),
            notice.get("code"),
            notice.get("totalNotices"),
        )
        print(f"{severity:8} {code} : {total}")
        if severity == "ERROR":
            errors += int(total or 1)
    print(f"{len(notices)} type(s) d'avis, {errors} erreur(s).")
    return 1 if errors else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="nemesis-fixtures", description="Jeu fictif Lagune-Fictive (I0.5)."
    )
    commands = parser.add_subparsers(dest="command", required=True)
    generate = commands.add_parser(
        "generer", help="régénérer le GTFS fictif, le jeu SQL et l'extrait OSM fictif"
    )
    generate.add_argument("--racine", type=Path, default=Path("."))
    generate.add_argument(
        "--verifier", action="store_true", help="échouer si un fichier est périmé"
    )
    report = commands.add_parser("verifier-rapport", help="résumer un rapport du validateur GTFS")
    report.add_argument("rapport", type=Path)
    args = parser.parse_args(argv)
    if args.command == "generer":
        return _generate(args.racine, args.verifier)
    return _check_report(args.rapport)


if __name__ == "__main__":
    sys.exit(main())

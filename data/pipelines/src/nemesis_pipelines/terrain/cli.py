"""Command line: `nemesis-terrain valider | generer | icones | accord`."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from nemesis_pipelines.terrain.generation import generated_files
from nemesis_pipelines.terrain.quality import assess, markdown
from nemesis_pipelines.terrain.reports import icon_results, icon_table
from nemesis_pipelines.terrain.schema import load_schemas, load_vocabularies
from nemesis_pipelines.terrain.validation import DirectoryReport, validate_tree


def _validate(paths: list[Path], fictional: bool) -> tuple[list[DirectoryReport], int]:
    schemas = load_schemas()
    reports: list[DirectoryReport] = []
    for path in paths:
        if not path.is_dir():
            print(f"{path} : dossier introuvable", file=sys.stderr)
            return reports, 1
        reports.extend(validate_tree(path, schemas, fictional))
    errors = 0
    for report in reports:
        counts = ", ".join(
            f"{name} : {len(dataset.rows)} ligne(s)" for name, dataset in report.datasets.items()
        )
        status = "OK" if not report.issues else f"{len(report.issues)} erreur(s)"
        print(f"{report.directory} — {counts or 'aucun jeu reconnu'} — {status}")
        for issue in report.issues:
            print(f"  {issue}")
        errors += len(report.issues)
    if not reports:
        print("Aucun fichier CSV trouvé.")
    return reports, 1 if errors else 0


def _generate(root: Path, check: bool) -> int:
    outdated = []
    for relative, content in generated_files(load_schemas(), load_vocabularies()).items():
        path = root / relative
        current = path.read_bytes().decode("utf-8") if path.exists() else None
        if current == content:
            continue
        outdated.append(relative)
        if not check:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8", newline="")
    if check and outdated:
        print("Fichiers à régénérer avec « uv run nemesis-terrain generer » :", file=sys.stderr)
        for relative in outdated:
            print(f"  {relative}", file=sys.stderr)
        return 1
    if not check:
        print(f"{len(outdated)} fichier(s) mis à jour.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="nemesis-terrain", description="Données de terrain (I0.2, I0.12)."
    )
    commands = parser.add_subparsers(dest="command", required=True)

    validate = commands.add_parser("valider", help="valider des dossiers de fichiers CSV")
    validate.add_argument("dossiers", nargs="+", type=Path)
    validate.add_argument(
        "--fictif",
        action="store_true",
        help="jeu fictif : chaque ligne doit porter is_fictional = true",
    )

    generate = commands.add_parser("generer", help="régénérer modèles CSV et dictionnaire")
    generate.add_argument("--racine", type=Path, default=Path("."))
    generate.add_argument(
        "--verifier", action="store_true", help="échouer si un fichier est périmé"
    )

    icons = commands.add_parser("icones", help="taux de reconnaissance des icônes")
    icons.add_argument("dossiers", nargs="+", type=Path)
    icons.add_argument("--fictif", action="store_true", help="calculer sur un jeu fictif")

    agreement = commands.add_parser(
        "accord", help="accord entre doubles relevés et doubles comptages (Éclaireurs)"
    )
    agreement.add_argument("dossiers", nargs="+", type=Path)
    agreement.add_argument("--fictif", action="store_true", help="calculer sur un jeu fictif")
    agreement.add_argument(
        "--strict", action="store_true", help="échouer si une mesure est sous son seuil"
    )

    args = parser.parse_args(argv)
    if args.command == "valider":
        return _validate(args.dossiers, args.fictif)[1]
    if args.command == "generer":
        return _generate(args.racine, args.verifier)
    reports, status = _validate(args.dossiers, args.fictif)
    if status:
        print("Corriger les erreurs avant de calculer les taux.", file=sys.stderr)
        return status
    if args.command == "accord":
        report = assess(reports)
        print(markdown(report))
        return 1 if args.strict and not report.accepted else 0
    print(icon_table(icon_results(reports)))
    return 0


if __name__ == "__main__":
    sys.exit(main())

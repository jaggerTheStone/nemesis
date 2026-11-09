"""Tests of the field-data schemas, validator and derived files (I0.2)."""

from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path

import pytest

from nemesis_pipelines.terrain.cli import main
from nemesis_pipelines.terrain.generation import generated_files
from nemesis_pipelines.terrain.reports import icon_results
from nemesis_pipelines.terrain.schema import FICTIONAL_COLUMN, load_schemas, load_vocabularies
from nemesis_pipelines.terrain.validation import (
    dataset_for,
    normalise,
    suggest_code,
    validate_directory,
    validate_tree,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
SCHEMAS = load_schemas()

TRIP = {
    "id": "TR-001",
    "origine": "Gare A",
    "origine_commune": "yopougon",
    "destination": "Marché B",
    "destination_commune": "adjame",
    "heure_depart": "06:30",
    "type_jour": "ouvrable",
    "profil": "standard",
    "validateurs": "V01+V02",
    "date_validation": "2026-11-20",
}
ANSWER = {
    "trajet_id": "TR-001",
    "reponse_no": "1",
    "statut": "acceptable",
    "etape1_mode": "gbaka",
    "etape1_montee": "Gare A",
    "etape1_descente": "Marché B",
    "duree_min_minutes": "20",
    "duree_max_minutes": "40",
    "prix_min_fcfa": "200",
    "prix_max_fcfa": "300",
    "justification": "Ligne directe",
}
QUERY = {
    "id": "RQ-0001",
    "date": "2026-11-20",
    "enqueteur": "E01",
    "lieu_enquete": "Gare A",
    "commune_enquete": "yopougon",
    "formulation": "Adj Liberté",
    "mode_saisie": "oral",
    "langue": "francais",
    "type_lieu": "marche",
    "expression_relative": "aucune",
    "lieu_compris": "Marché B",
    "commune_visee": "adjame",
}
PARTICIPANT = {
    "session": "S20261120-01",
    "participant": "P01",
    "consentement_oral": "oui",
    "tranche_age": "plus_60",
    "lecture": "difficile",
    "telephone": "basique",
    "langue_preferee": "dioula",
    "lieu_session": "Gare A",
    "enqueteur": "E01",
}


def write_csv(directory: Path, name: str, rows: list[dict[str, str]], delimiter: str = ";") -> Path:
    """Writes rows with the full schema header, as a field agent would."""
    schema = dataset_for(name, SCHEMAS)
    assert schema is not None
    header = list(schema.columns)
    extra = [column for row in rows for column in row if column not in header]
    header += list(dict.fromkeys(extra))
    lines = [delimiter.join(header)]
    for row in rows:
        lines.append(delimiter.join(row.get(column, "") for column in header))
    path = directory / name
    path.write_text("﻿" + "\r\n".join(lines) + "\r\n", encoding="utf-8")
    return path


def messages(directory: Path, fictional: bool = False) -> list[str]:
    return [issue.message for issue in validate_directory(directory, SCHEMAS, fictional).issues]


# --- Schemas and derived files -------------------------------------------------------


def test_every_schema_points_to_existing_documents() -> None:
    assert list(SCHEMAS) == [
        "requetes",
        "trajets",
        "reponses",
        "participants",
        "observations",
        "icones",
        "gares",
        "releves_ligne",
        "arrets_releves",
        "prix",
        "comptages",
        "photos",
        "traces",
    ]
    for schema in SCHEMAS.values():
        assert (REPO_ROOT / schema.protocol).is_file(), schema.protocol
        for form in schema.forms:
            assert (REPO_ROOT / form).is_file(), form


def test_generated_files_are_up_to_date() -> None:
    for relative, content in generated_files(SCHEMAS, load_vocabularies()).items():
        path = REPO_ROOT / relative
        assert path.read_bytes().decode("utf-8") == content, f"régénérer {relative}"


def test_fictional_fixtures_are_valid() -> None:
    reports = validate_tree(REPO_ROOT / "data/fixtures_fictives/terrain", SCHEMAS, fictional=True)
    assert reports
    assert [str(issue) for report in reports for issue in report.issues] == []


class _FieldCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.fields: set[str] = set()
        self.datasets: set[str] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if values.get("data-champ"):
            self.fields.add(values["data-champ"] or "")
        if values.get("data-jeux"):
            self.datasets.update((values["data-jeux"] or "").split())


def test_paper_forms_cover_every_field_entered_on_site() -> None:
    forms: dict[str, set[str]] = {}
    for schema in SCHEMAS.values():
        for form in schema.forms:
            forms.setdefault(form, set()).add(schema.name)
    for form, names in forms.items():
        collector = _FieldCollector()
        collector.feed((REPO_ROOT / form).read_text(encoding="utf-8"))
        expected = {
            spec.name for name in names for spec in SCHEMAS[name].fields if spec.entry == "field"
        }
        assert collector.datasets == names, form
        assert collector.fields == expected, f"{form} : écart {collector.fields ^ expected}"


# --- Values ----------------------------------------------------------------------------


def test_valid_trip_and_answer_pass(tmp_path: Path) -> None:
    write_csv(tmp_path, "trajets.csv", [TRIP])
    write_csv(tmp_path, "reponses.csv", [ANSWER])
    assert messages(tmp_path) == []


@pytest.mark.parametrize(
    ("column", "value", "expected"),
    [
        ("date_validation", "20/11/2026", "écrire 2026-11-20"),
        ("date_validation", "2026-02-30", "n'est pas une date valide"),
        ("heure_depart", "6h30", "écrire 06:30"),
        ("heure_depart", "25:00", "n'est pas une heure valide"),
        ("origine_commune", "Port-Bouët", "vouliez-vous « port_bouet »"),
        ("origine_commune", "yopogon", "vouliez-vous « yopougon »"),
        ("validateurs", "V01", "au moins 2 éléments"),
        ("validateurs", "V01+V01", "chaque élément de la liste doit être différent"),
        ("validateurs", "V01+", "élément vide"),
        ("conditions", "pluie+orage", "valeur « orage » inconnue"),
        ("id", "TR-1", "ne respecte pas le format"),
        ("origine_latitude", "48.85", "supérieure au maximum"),
    ],
)
def test_invalid_trip_values_are_reported(
    tmp_path: Path, column: str, value: str, expected: str
) -> None:
    row = {**TRIP, column: value}
    if column == "origine_latitude":
        row["origine_longitude"] = "-4.0"
    write_csv(tmp_path, "trajets.csv", [row])
    write_csv(tmp_path, "reponses.csv", [ANSWER])
    assert any(expected in message for message in messages(tmp_path)), messages(tmp_path)


def test_decimal_comma_from_french_spreadsheets_is_accepted(tmp_path: Path) -> None:
    write_csv(
        tmp_path,
        "trajets.csv",
        [{**TRIP, "origine_latitude": "5,35", "origine_longitude": "-4,02"}],
    )
    write_csv(tmp_path, "reponses.csv", [ANSWER])
    assert messages(tmp_path) == []


def test_missing_required_value(tmp_path: Path) -> None:
    write_csv(tmp_path, "requetes.csv", [{**QUERY, "formulation": ""}])
    assert messages(tmp_path) == ["valeur obligatoire manquante"]


def test_too_long_text(tmp_path: Path) -> None:
    write_csv(tmp_path, "requetes.csv", [{**QUERY, "formulation": "x" * 201}])
    assert messages(tmp_path) == ["texte trop long (201 caractères, maximum 200)"]


def test_extra_value_of_a_field(tmp_path: Path) -> None:
    write_csv(tmp_path, "requetes.csv", [{**QUERY, "commune_visee": "inconnue"}])
    assert messages(tmp_path) == []


def test_suggestions() -> None:
    values = {"port_bouet": "Port-Bouët", "yopougon": "Yopougon"}
    assert normalise("  Port-Bouët ") == "port_bouet"
    assert suggest_code("PORT BOUET", values) == "port_bouet"
    assert suggest_code("Yop", values) is None


# --- Files and headers -----------------------------------------------------------------


def test_comma_delimiter_and_no_bom(tmp_path: Path) -> None:
    path = write_csv(tmp_path, "requetes.csv", [QUERY], delimiter=",")
    path.write_bytes(path.read_bytes().removeprefix("﻿".encode()))
    assert messages(tmp_path) == []


def test_non_utf8_file(tmp_path: Path) -> None:
    (tmp_path / "requetes.csv").write_bytes("id;formulation\nRQ-0001;Adjamé\n".encode("cp1252"))
    assert messages(tmp_path) == [
        "le fichier n'est pas en UTF-8 : l'enregistrer en « CSV UTF-8 » dans le tableur"
    ]


def test_unknown_and_missing_columns(tmp_path: Path) -> None:
    (tmp_path / "requetes.csv").write_text("id;formulaton\nRQ-0001;Adj\n", encoding="utf-8")
    found = messages(tmp_path)
    assert "colonne inconnue ; vouliez-vous « formulation » ?" in found
    assert "colonne obligatoire absente" in found


def test_unknown_file_name(tmp_path: Path) -> None:
    (tmp_path / "notes.csv").write_text("a\n1\n", encoding="utf-8")
    assert messages(tmp_path)[0].startswith("nom de fichier inconnu")


def test_dataset_prefix_matching() -> None:
    assert dataset_for("requetes-2026-11-20-E01.csv", SCHEMAS).name == "requetes"  # type: ignore[union-attr]
    assert dataset_for("requetes.csv", SCHEMAS).name == "requetes"  # type: ignore[union-attr]
    assert dataset_for("requetesX.csv", SCHEMAS) is None


def test_empty_rows_are_ignored(tmp_path: Path) -> None:
    path = write_csv(tmp_path, "requetes.csv", [QUERY])
    path.write_text(path.read_text(encoding="utf-8") + ";;;;\r\n\r\n", encoding="utf-8")
    assert messages(tmp_path) == []


def test_duplicate_key_across_files_of_one_dataset(tmp_path: Path) -> None:
    write_csv(tmp_path, "requetes-E01.csv", [QUERY])
    write_csv(tmp_path, "requetes-E02.csv", [{**QUERY, "enqueteur": "E02"}])
    found = messages(tmp_path)
    assert len(found) == 1 and found[0].startswith("identifiant RQ-0001 déjà utilisé")


# --- Rules -----------------------------------------------------------------------------


def test_coordinates_go_together(tmp_path: Path) -> None:
    write_csv(tmp_path, "requetes.csv", [{**QUERY, "latitude": "5.3"}])
    assert messages(tmp_path) == ["renseigner ensemble ou laisser vides : latitude, longitude"]


def test_ordered_ranges(tmp_path: Path) -> None:
    write_csv(tmp_path, "trajets.csv", [TRIP])
    write_csv(tmp_path, "reponses.csv", [{**ANSWER, "prix_min_fcfa": "400"}])
    assert messages(tmp_path) == ["prix_max_fcfa doit être supérieur ou égal à prix_min_fcfa"]


def test_acceptable_answers_need_ranges_but_traps_do_not(tmp_path: Path) -> None:
    trap = {key: value for key, value in ANSWER.items() if "duree" not in key and "prix" not in key}
    write_csv(tmp_path, "trajets.csv", [TRIP])
    write_csv(tmp_path, "reponses.csv", [ANSWER, {**trap, "reponse_no": "2", "statut": "piege"}])
    assert messages(tmp_path) == []
    write_csv(tmp_path, "reponses.csv", [{**trap, "statut": "acceptable"}])
    assert sorted(messages(tmp_path)).count("obligatoire quand statut = acceptable") == 4


def test_steps_must_be_complete_and_contiguous(tmp_path: Path) -> None:
    write_csv(tmp_path, "trajets.csv", [TRIP])
    gap = {**ANSWER, "etape3_mode": "gbaka", "etape3_montee": "C", "etape3_descente": "D"}
    incomplete = {**ANSWER, "reponse_no": "2", "etape2_mode": "woro_communal"}
    no_step = {key: value for key, value in ANSWER.items() if not key.startswith("etape")} | {
        "reponse_no": "3"
    }
    write_csv(tmp_path, "reponses.csv", [gap, incomplete, no_step])
    found = messages(tmp_path)
    assert "étape 3 remplie sans l'étape 2" in found
    assert found.count("étape 2 incomplète") == 2
    assert "au moins une étape en véhicule attendue" in found


def test_consent_is_mandatory(tmp_path: Path) -> None:
    write_csv(tmp_path, "participants.csv", [{**PARTICIPANT, "consentement_oral": "non"}])
    assert messages(tmp_path) == [
        "sans consentement, aucune donnée ne doit être saisie : supprimer la ligne"
    ]


def test_references_between_files(tmp_path: Path) -> None:
    write_csv(tmp_path, "trajets.csv", [TRIP])
    write_csv(tmp_path, "reponses.csv", [ANSWER, {**ANSWER, "trajet_id": "TR-009"}])
    assert messages(tmp_path) == ["TR-009 absent de trajets"]


def test_reference_target_file_must_exist(tmp_path: Path) -> None:
    write_csv(tmp_path, "reponses.csv", [ANSWER])
    assert messages(tmp_path) == ["fichier trajets.csv attendu dans le même dossier"]


def test_every_trip_needs_an_acceptable_answer(tmp_path: Path) -> None:
    write_csv(tmp_path, "trajets.csv", [TRIP])
    write_csv(tmp_path, "reponses.csv", [{**ANSWER, "statut": "piege"}])
    assert messages(tmp_path) == [
        "chaque trajet doit avoir au moins une réponse acceptable dans reponses.csv"
    ]


# --- Fictional flag (rule 1.3.1) --------------------------------------------------------


def test_fictional_rows_are_refused_in_real_data(tmp_path: Path) -> None:
    write_csv(tmp_path, "requetes.csv", [{**QUERY, FICTIONAL_COLUMN: "true"}])
    assert messages(tmp_path) == [
        "ligne fictive dans un jeu réel : la déplacer dans data/fixtures_fictives"
    ]


def test_fictional_mode_requires_the_flag_on_every_row(tmp_path: Path) -> None:
    write_csv(tmp_path, "requetes.csv", [QUERY])
    assert messages(tmp_path, fictional=True) == [
        "jeu fictif : chaque ligne doit porter is_fictional = true"
    ]


# --- Icon report -----------------------------------------------------------------------


def _icon_session(directory: Path, recognised: int, total: int) -> None:
    participants, answers = [], []
    for index in range(1, total + 1):
        code = f"P{index:02d}"
        participants.append({**PARTICIPANT, "participant": code})
        answers.append(
            {
                "session": PARTICIPANT["session"],
                "participant": code,
                "icone": "mode_gbaka",
                "version_icone": "v1",
                "reponse": "gbaka",
                "reconnue": "oui" if index <= recognised else "non",
                "codeur": "E02",
            }
        )
    write_csv(directory, "participants.csv", participants)
    write_csv(directory, "icones.csv", answers)


@pytest.mark.parametrize(
    ("recognised", "total", "status"),
    [
        (17, 20, "seuil atteint"),
        (16, 20, "à retravailler"),
        (19, 19, "échantillon insuffisant (moins de 20)"),
    ],
)
def test_icon_threshold(tmp_path: Path, recognised: int, total: int, status: str) -> None:
    _icon_session(tmp_path, recognised, total)
    report = validate_directory(tmp_path, SCHEMAS, fictional=False)
    assert report.issues == []
    [result] = icon_results([report])
    assert result.status == status
    assert result.low_literacy_participants == total


# --- Command line ----------------------------------------------------------------------


def test_cli_exit_codes(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write_csv(tmp_path, "requetes.csv", [QUERY])
    assert main(["valider", str(tmp_path)]) == 0
    write_csv(tmp_path, "requetes.csv", [{**QUERY, "mode_saisie": "Écrit"}])
    assert main(["valider", str(tmp_path)]) == 1
    assert "vouliez-vous « ecrit »" in capsys.readouterr().out
    assert main(["valider", str(tmp_path / "absent")]) == 1


def test_pdf_forms_match_their_html_sources() -> None:
    import hashlib

    manifest = REPO_ROOT / "docs/TERRAIN/pdf/SOURCES.sha256"
    recorded = dict(line.split("  ")[::-1] for line in manifest.read_text().splitlines())
    sources = sorted((REPO_ROOT / "docs/TERRAIN/fiches").glob("*.html")) + [
        REPO_ROOT / "docs/TERRAIN/fiches/fiches.css"
    ]
    current = {
        str(path.relative_to(REPO_ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sources
    }
    assert recorded == current, "fiches modifiées : régénérer les PDF avec « make fiches-pdf »"
    for path in sources:
        if path.suffix == ".html":
            assert (REPO_ROOT / "docs/TERRAIN/pdf" / f"{path.stem}.pdf").is_file()

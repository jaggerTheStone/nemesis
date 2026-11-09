"""« Éclaireurs » campaign (I0.12): exchange formats and the quality protocol."""

from __future__ import annotations

from pathlib import Path

import pytest

from nemesis_pipelines.terrain.cli import main
from nemesis_pipelines.terrain.quality import (
    MIN_STOPS_JACCARD,
    assess,
    cohen_kappa,
    order_agreement,
)
from nemesis_pipelines.terrain.schema import load_schemas
from nemesis_pipelines.terrain.validation import dataset_for, validate_directory, validate_tree

REPO_ROOT = Path(__file__).resolve().parents[3]
SCHEMAS = load_schemas()
FIXTURES = REPO_ROOT / "data/fixtures_fictives/terrain/eclaireurs"


def write_csv(directory: Path, name: str, rows: list[dict[str, str]]) -> Path:
    schema = dataset_for(name, SCHEMAS)
    assert schema is not None
    header = list(schema.columns)
    lines = [";".join(header)]
    lines += [";".join(row.get(column, "") for column in header) for row in rows]
    path = directory / name
    path.write_text("﻿" + "\n".join(lines) + "\n", encoding="utf-8")
    return path


def messages(directory: Path) -> list[str]:
    report = validate_directory(directory, SCHEMAS, fictional=False)
    return [str(issue) for issue in report.issues]


SURVEY = {
    "id": "RL-0001",
    "date": "2026-11-20",
    "eclaireur": "E01",
    "mode": "gbaka",
    "ligne": "Adjamé – Bingerville",
    "type_jour": "ouvrable",
    "heure_depart": "06:40",
    "heure_arrivee": "07:30",
    "prix_paye": "300",
    "trace_gps": "non",
}


def stop(survey: str, rank: int, name: str, time: str = "06:45") -> dict[str, str]:
    return {
        "releve_id": survey,
        "rang": str(rank),
        "nom": name,
        "heure": time,
        "type_arret": "arret_informel",
    }


def slot(scout: str, tranche: str, departs: int, queue: int, level: str) -> dict[str, str]:
    return {
        "gare_id": "GA-0001",
        "date": "2026-11-20",
        "eclaireur": scout,
        "ligne": "Bingerville",
        "mode": "gbaka",
        "tranche": tranche,
        "arrivees": str(departs),
        "departs": str(departs),
        "vehicules_debut": "1",
        "file_debut": str(queue),
        "file_methode": "comptee",
        "file_niveau": level,
        "pluie": "non",
    }


# --- Exchange formats ------------------------------------------------------------------


def test_the_fictional_campaign_is_valid_and_accepted() -> None:
    reports = validate_tree(FIXTURES, SCHEMAS, fictional=True)
    assert [str(i) for r in reports for i in r.issues] == []
    names = set(reports[0].datasets)
    assert names == {
        "gares",
        "releves_ligne",
        "arrets_releves",
        "prix",
        "comptages",
        "photos",
        "traces",
    }
    quality = assess(reports)
    assert quality.accepted
    assert (quality.lines, quality.doubled) == (2, 1)
    assert len(quality.surveys) == 1 and len(quality.counts) == 1


def test_a_survey_needs_its_stops_and_times_in_order(tmp_path: Path) -> None:
    write_csv(tmp_path, "releves_ligne.csv", [{**SURVEY, "heure_arrivee": "06:10"}])
    write_csv(tmp_path, "arrets_releves.csv", [])
    found = messages(tmp_path)
    assert any("heure_arrivee doit être supérieur ou égal à heure_depart" in m for m in found)
    assert any("arrets_releves.csv" in m for m in found)


def test_counts_use_quarter_hours_and_full_departures_never_exceed_departures(
    tmp_path: Path,
) -> None:
    bad = {**slot("E01", "06:10", 3, 4, "peu"), "partis_pleins": "5"}
    write_csv(tmp_path, "comptages.csv", [bad])
    found = messages(tmp_path)
    assert any("[tranche]" in m for m in found)
    assert any("departs doit être supérieur ou égal à partis_pleins" in m for m in found)


def test_an_unchecked_photo_never_leaves_the_phone(tmp_path: Path) -> None:
    photo = {
        "id": "PH-00001",
        "fichier": "PH-00001.jpg",
        "date": "2026-11-20",
        "heure": "06:20",
        "eclaireur": "E01",
        "objet": "GA-0001",
        "sujet": "gare",
        "latitude": "5.35",
        "longitude": "-4.01",
        "controle": "non",
        "floutage": "non",
    }
    write_csv(tmp_path, "photos.csv", [photo])
    assert any("ne quitte pas le téléphone" in m for m in messages(tmp_path))


def test_traces_belong_to_a_survey(tmp_path: Path) -> None:
    write_csv(
        tmp_path,
        "traces.csv",
        [
            {
                "releve_id": "RL-0009",
                "heure": "06:40:05",
                "latitude": "5.35",
                "longitude": "-4.01",
                "precision_m": "8",
            }
        ],
    )
    assert any("releves_ligne" in m for m in messages(tmp_path))


# --- Agreement measures ----------------------------------------------------------------


def test_cohen_kappa() -> None:
    assert cohen_kappa(["a", "b", "a", "b"], ["a", "b", "a", "b"]) == 1.0
    assert cohen_kappa(["a", "a", "b", "b"], ["a", "b", "a", "b"]) == pytest.approx(0.0)
    # Classic example: 20 + 15 agreements out of 50, kappa 0.4.
    first = ["oui"] * 25 + ["non"] * 25
    second = ["oui"] * 20 + ["non"] * 5 + ["oui"] * 10 + ["non"] * 15
    assert cohen_kappa(first, second) == pytest.approx(0.4)


def test_order_agreement_counts_inverted_pairs() -> None:
    assert order_agreement([(0, 0), (1, 1), (2, 2)]) == 1.0
    assert order_agreement([(0, 0), (1, 2), (2, 1)]) == pytest.approx(2 / 3)
    assert order_agreement([(0, 0)]) is None


def test_two_surveys_that_disagree_are_sent_back(tmp_path: Path) -> None:
    second = {
        **SURVEY,
        "id": "RL-0002",
        "eclaireur": "E02",
        "double_de": "RL-0001",
        "prix_paye": "400",
    }
    write_csv(tmp_path, "releves_ligne.csv", [SURVEY, second])
    names = ["Liberté", "Mosquée", "Pharmacie", "Carrefour", "Terminus"]
    other = ["Liberté", "Église", "École", "Carrefour", "Terminus"]
    write_csv(
        tmp_path,
        "arrets_releves.csv",
        [stop("RL-0001", i, n) for i, n in enumerate(names, 1)]
        + [stop("RL-0002", i, n) for i, n in enumerate(other, 1)],
    )
    report = validate_directory(tmp_path, SCHEMAS, fictional=False)
    assert report.issues == []
    quality = assess([report])
    (check,) = quality.surveys
    jaccard = next(m for m in check.measures if m.name.startswith("arrêts"))
    assert jaccard.value == pytest.approx(3 / 7)
    assert jaccard.value < MIN_STOPS_JACCARD and jaccard.ok is False
    fare = next(m for m in check.measures if m.name.startswith("écart"))
    assert fare.value == 100 and fare.ok is False
    assert not quality.accepted


def test_a_double_survey_by_the_same_scout_is_refused(tmp_path: Path) -> None:
    second = {**SURVEY, "id": "RL-0002", "double_de": "RL-0001"}
    write_csv(tmp_path, "releves_ligne.csv", [SURVEY, second])
    write_csv(
        tmp_path,
        "arrets_releves.csv",
        [stop("RL-0001", 1, "Liberté"), stop("RL-0002", 1, "Liberté")],
    )
    quality = assess([validate_directory(tmp_path, SCHEMAS, fictional=False)])
    assert any("même Éclaireur" in note for note in quality.surveys[0].notes)
    assert not quality.accepted


def test_double_counts_compare_vehicles_queues_and_categories(tmp_path: Path) -> None:
    times = [f"{6 + k // 4:02d}:{(k % 4) * 15:02d}" for k in range(10)]
    first = [slot("E01", t, 4, 30, "beaucoup") for t in times]
    # The second Éclaireur misses vehicles half the time and calls every queue « moyen ».
    second = [slot("E02", t, 4 if k % 2 else 1, 31, "moyen") for k, t in enumerate(times)]
    write_csv(tmp_path, "comptages.csv", first + second)
    report = validate_directory(tmp_path, SCHEMAS, fictional=False)
    assert report.issues == []
    (check,) = assess([report]).counts
    values = {m.name: m for m in check.measures}
    assert values["départs à 1 près"].value == pytest.approx(0.5)
    assert values["départs à 1 près"].ok is False
    assert values["files à 20 % près"].ok is True
    # Every queue was counted at 30 or 31: inside « beaucoup », never inside « moyen ».
    calibration = assess([report]).calibration
    assert calibration["beaucoup"] == (10, 10)
    assert calibration["moyen"] == (0, 10)


def test_the_accord_command(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["accord", "--fictif", str(FIXTURES)]) == 0
    assert "Verdict : accepté." in capsys.readouterr().out
    second = {**SURVEY, "id": "RL-0002", "double_de": "RL-0001"}
    write_csv(tmp_path, "releves_ligne.csv", [SURVEY, second])
    write_csv(
        tmp_path,
        "arrets_releves.csv",
        [stop("RL-0001", 1, "Liberté"), stop("RL-0002", 1, "Liberté")],
    )
    assert main(["accord", str(tmp_path)]) == 0
    assert main(["accord", "--strict", str(tmp_path)]) == 1

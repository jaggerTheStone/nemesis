"""Summaries computed from validated field data."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from nemesis_pipelines.terrain.validation import DirectoryReport

# Partie 10.1: each icon must be recognised by at least 85 % of 20 people.
ICON_THRESHOLD = 0.85
ICON_MIN_PARTICIPANTS = 20
_LOW_LITERACY = {"difficile", "ne_lit_pas"}


@dataclass(frozen=True)
class IconResult:
    version: str
    icon: str
    participants: int
    recognised: int
    partial: int
    low_literacy_participants: int
    low_literacy_recognised: int

    @property
    def rate(self) -> float:
        return self.recognised / self.participants if self.participants else 0.0

    @property
    def status(self) -> str:
        if self.participants < ICON_MIN_PARTICIPANTS:
            return f"échantillon insuffisant (moins de {ICON_MIN_PARTICIPANTS})"
        return "seuil atteint" if self.rate >= ICON_THRESHOLD else "à retravailler"


def icon_results(reports: list[DirectoryReport]) -> list[IconResult]:
    """Recognition rate per icon version; a person counts once per icon."""
    literacy: dict[tuple[str, str, str], str] = {}
    answers: dict[tuple[str, str], dict[tuple[str, str, str], str]] = defaultdict(dict)
    for report in reports:
        directory = str(report.directory)
        participants = report.datasets.get("participants")
        if participants is not None:
            for row in participants.rows:
                person = (directory, row.values["session"], row.values["participant"])
                literacy[person] = row.values.get("lecture", "")
        icons = report.datasets.get("icones")
        if icons is None:
            continue
        for row in icons.rows:
            person = (directory, row.values["session"], row.values["participant"])
            answers[(row.values["version_icone"], row.values["icone"])][person] = row.values[
                "reconnue"
            ]

    results = []
    for (version, icon), by_person in sorted(answers.items()):
        low = [person for person in by_person if literacy.get(person) in _LOW_LITERACY]
        results.append(
            IconResult(
                version=version,
                icon=icon,
                participants=len(by_person),
                recognised=sum(1 for value in by_person.values() if value == "oui"),
                partial=sum(1 for value in by_person.values() if value == "partiel"),
                low_literacy_participants=len(low),
                low_literacy_recognised=sum(1 for person in low if by_person[person] == "oui"),
            )
        )
    return results


def icon_table(results: list[IconResult]) -> str:
    columns = ("Version", "Icône", "Personnes", "Reconnue", "Partielle", "Taux")
    columns += ("Lecture difficile", "Statut")
    lines = ["| " + " | ".join(columns) + " |", "|" + "---|" * len(columns)]
    for result in results:
        low = f"{result.low_literacy_recognised}/{result.low_literacy_participants}"
        lines.append(
            f"| {result.version} | {result.icon} | {result.participants} | {result.recognised} | "
            f"{result.partial} | {result.rate:.0%} | {low} | {result.status} |"
        )
    return "\n".join(lines)

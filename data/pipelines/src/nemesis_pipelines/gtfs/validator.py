"""MobilityData GTFS validator: run it, then list every notice it raised.

The canonical validator (partie 7.1) runs from its pinned image. Its notices are
listed in full in a Markdown summary, errors first; the GTFS itself is never
modified to make them disappear (I0.7: « jamais corrigées en silence »).
"""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

SEVERITIES = ("ERROR", "WARNING", "INFO")
SEVERITY_LABELS = {"ERROR": "Erreur", "WARNING": "Avertissement", "INFO": "Information"}
MAX_SAMPLES = 10


@dataclass(frozen=True)
class Notice:
    code: str
    severity: str
    total: int
    samples: tuple[dict[str, Any], ...]


@dataclass
class ValidationSummary:
    notices: list[Notice]
    validator_version: str | None = None
    validated_at: str | None = None
    counts: dict[str, Any] = field(default_factory=dict)
    system_errors: list[Notice] = field(default_factory=list)

    def total(self, severity: str) -> int:
        return sum(n.total for n in self.notices if n.severity == severity)


def run_validator(image: str, archive: Path, output: Path, country_code: str | None) -> None:
    """Runs the validator image on `archive`; reports land in `output`."""
    output.mkdir(parents=True, exist_ok=True)
    archive = archive.resolve()
    output = output.resolve()
    command = [
        "docker",
        "run",
        "--rm",
        "--user",
        f"{os.getuid()}:{os.getgid()}",
        "-v",
        f"{archive.parent}:/input:ro",
        "-v",
        f"{output}:/output",
        image,
        "-i",
        f"/input/{archive.name}",
        "-o",
        "/output",
    ]
    if country_code:
        command += ["-c", country_code]
    subprocess.run(command, check=True)


def _notices(raw: list[dict[str, Any]]) -> list[Notice]:
    notices = [
        Notice(
            code=str(item.get("code", "?")),
            severity=str(item.get("severity", "?")),
            total=int(item.get("totalNotices") or len(item.get("sampleNotices", [])) or 1),
            samples=tuple(item.get("sampleNotices", [])[:MAX_SAMPLES]),
        )
        for item in raw
    ]
    order = {severity: index for index, severity in enumerate(SEVERITIES)}
    return sorted(notices, key=lambda n: (order.get(n.severity, 99), -n.total, n.code))


def read_report(directory: Path) -> ValidationSummary:
    """Reads report.json (and system_errors.json) written by the validator."""
    report = json.loads((directory / "report.json").read_text(encoding="utf-8"))
    summary = report.get("summary", {})
    system_path = directory / "system_errors.json"
    system = (
        json.loads(system_path.read_text(encoding="utf-8")).get("notices", [])
        if system_path.exists()
        else []
    )
    return ValidationSummary(
        notices=_notices(report.get("notices", [])),
        validator_version=summary.get("validatorVersion"),
        validated_at=summary.get("validatedAt"),
        counts=summary.get("counts", {}),
        system_errors=_notices(system),
    )


def _sample(sample: dict[str, Any]) -> str:
    text = json.dumps(sample, ensure_ascii=False, sort_keys=True)
    return text if len(text) <= 300 else text[:297] + "…"


def markdown(summary: ValidationSummary, title: str, html_report: str = "report.html") -> str:
    lines = [f"# Validation GTFS : {title}", ""]
    if summary.validator_version:
        lines.append(f"- Validateur MobilityData {summary.validator_version}")
    if summary.validated_at:
        lines.append(f"- Validé le {summary.validated_at}")
    lines += [
        f"- Rapport complet : [{html_report}]({html_report})",
        "- **Aucune correction automatique** : le GTFS est importé tel que publié ; chaque"
        " avis ci-dessous reste à traiter avec le producteur des données.",
        "",
        "| Gravité | Avis distincts | Occurrences |",
        "|---------|----------------|-------------|",
    ]
    for severity in SEVERITIES:
        kinds = [n for n in summary.notices if n.severity == severity]
        lines.append(f"| {SEVERITY_LABELS[severity]} | {len(kinds)} | {summary.total(severity)} |")
    if summary.counts:
        lines += ["", "Volumes vus par le validateur :", ""]
        lines += [f"- {key} : {value}" for key, value in sorted(summary.counts.items())]
    if summary.system_errors:
        lines += ["", "## Erreurs du validateur lui-même", ""]
        lines += [f"- `{n.code}` ({n.total})" for n in summary.system_errors]
    lines += ["", "## Tous les avis", "", "| Gravité | Code | Occurrences |", "|---|---|---|"]
    lines += [
        f"| {SEVERITY_LABELS.get(n.severity, n.severity)} | `{n.code}` | {n.total} |"
        for n in summary.notices
    ]
    for notice in summary.notices:
        if notice.severity != "ERROR":
            continue
        lines += ["", f"### `{notice.code}` ({notice.total})", ""]
        lines += [f"- `{_sample(sample)}`" for sample in notice.samples]
        if notice.total > len(notice.samples):
            lines.append(f"- … {notice.total - len(notice.samples)} autre(s) : voir {html_report}")
    return "\n".join(lines) + "\n"

"""Quality of the « Éclaireurs » campaign (I0.12): agreement between double surveys.

Docs: docs/TERRAIN/PROTOCOLE-ECLAIREURS.md, « Protocole qualité ».
- 10 % of the lines are surveyed twice, by two different Éclaireurs (`double_de`).
- Two surveys of a line agree when they find the same stops (Jaccard index), in the same
  order, for about the same fare.
- Two counts of the same slot agree when departures and arrivals differ by one vehicle at
  most, the counted queues by 20 % at most, and the queue categories judged by eye agree
  beyond chance (Cohen's kappa).
Messages are in French: they are read by the campaign coordinator.
"""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from dataclasses import dataclass, field

from nemesis_pipelines.terrain.validation import DirectoryReport, Row, normalise

#: Acceptance thresholds (protocol). Changing one is a decision of the coordinator.
MIN_DOUBLED_SHARE = 0.10
MIN_STOPS_JACCARD = 0.80
MIN_ORDER_AGREEMENT = 0.95
MAX_FARE_GAP_XOF = 50
SAME_PLACE_M = 100.0
MIN_VEHICLE_AGREEMENT = 0.90
MIN_QUEUE_AGREEMENT = 0.80
MIN_KAPPA = 0.60
MIN_SLOTS_FOR_KAPPA = 8

#: Queue categories of the app (ALGORITHMES.md 1.2): [low, high] people.
QUEUE_LEVELS = {"peu": (0, 5), "moyen": (6, 20), "beaucoup": (21, 50), "tres_long": (51, None)}


@dataclass(frozen=True)
class Measure:
    name: str
    value: float | None
    threshold: str
    ok: bool | None

    def text(self) -> str:
        if self.value is None:
            return "—"
        if self.threshold.endswith("%"):
            return f"{self.value:.0%}"
        if self.threshold.endswith("F"):
            return f"{self.value:.0f} F"
        return f"{self.value:.2f}"


@dataclass
class Check:
    """One comparison: a pair of line surveys, or the double counts of a station line."""

    title: str
    measures: list[Measure] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def accepted(self) -> bool:
        return all(m.ok is not False for m in self.measures)


@dataclass
class QualityReport:
    lines: int
    doubled: int
    coverage: Measure
    surveys: list[Check]
    counts: list[Check]
    calibration: dict[str, tuple[int, int]]

    @property
    def accepted(self) -> bool:
        return (
            self.coverage.ok is not False
            and all(c.accepted for c in self.surveys)
            and all(c.accepted for c in self.counts)
        )


def _rows(reports: list[DirectoryReport], name: str) -> list[Row]:
    return [
        row for report in reports if name in report.datasets for row in report.datasets[name].rows
    ]


def _number(text: str) -> float | None:
    try:
        return float(text.replace(",", "."))
    except ValueError:
        return None


def _distance_m(a: tuple[float, float], b: tuple[float, float]) -> float:
    lat = math.radians((a[0] + b[0]) / 2)
    dy = (a[0] - b[0]) * 111_320
    dx = (a[1] - b[1]) * 111_320 * math.cos(lat)
    return math.hypot(dx, dy)


@dataclass(frozen=True)
class _Stop:
    rank: int
    name: str
    point: tuple[float, float] | None


def _stops(rows: list[Row], survey: str) -> list[_Stop]:
    stops = []
    for row in rows:
        v = row.values
        if v.get("releve_id") != survey:
            continue
        lat, lon = _number(v.get("latitude", "")), _number(v.get("longitude", ""))
        stops.append(
            _Stop(
                int(v["rang"]),
                normalise(v.get("nom", "")),
                (lat, lon) if lat is not None and lon is not None else None,
            )
        )
    return sorted(stops, key=lambda s: s.rank)


def _same(a: _Stop, b: _Stop) -> bool:
    if a.point and b.point and _distance_m(a.point, b.point) <= SAME_PLACE_M:
        return True
    return bool(a.name) and a.name == b.name


def match_stops(first: list[_Stop], second: list[_Stop]) -> list[tuple[int, int]]:
    """Pairs (index in first, index in second), each stop used once, in order of first."""
    used: set[int] = set()
    pairs = []
    for i, a in enumerate(first):
        for j, b in enumerate(second):
            if j not in used and _same(a, b):
                pairs.append((i, j))
                used.add(j)
                break
    return pairs


def order_agreement(pairs: list[tuple[int, int]]) -> float | None:
    """Share of pairs of matched stops seen in the same order by both surveys."""
    total = concordant = 0
    for x in range(len(pairs)):
        for y in range(x + 1, len(pairs)):
            total += 1
            concordant += int((pairs[x][1] < pairs[y][1]) == (pairs[x][0] < pairs[y][0]))
    return concordant / total if total else None


def cohen_kappa(first: list[str], second: list[str]) -> float | None:
    """Agreement between two raters beyond chance; None if undefined."""
    n = len(first)
    if n == 0:
        return None
    observed = sum(a == b for a, b in zip(first, second, strict=True)) / n
    ca, cb = Counter(first), Counter(second)
    expected = sum(ca[k] * cb[k] for k in set(ca) | set(cb)) / (n * n)
    if expected >= 1:
        return 1.0 if observed == 1 else None
    return (observed - expected) / (1 - expected)


def _line_key(v: dict[str, str]) -> tuple[str, str]:
    return v.get("mode", ""), normalise(v.get("ligne", ""))


def _survey_checks(reports: list[DirectoryReport]) -> tuple[int, int, list[Check]]:
    surveys = {row.values["id"]: row for row in _rows(reports, "releves_ligne")}
    stop_rows = _rows(reports, "arrets_releves")
    lines = {_line_key(r.values) for r in surveys.values()}
    doubled_lines = set()
    checks = []
    for second in surveys.values():
        target = second.values.get("double_de", "")
        if not target:
            continue
        first = surveys.get(target)
        check = Check(f"{target} et {second.values['id']}")
        checks.append(check)
        if first is None:
            check.notes.append(f"relevé {target} introuvable")
            check.measures.append(Measure("relevé d'origine", None, "présent", False))
            continue
        if first.values.get("eclaireur") == second.values.get("eclaireur"):
            check.notes.append("même Éclaireur : le double relevé doit être fait par un autre")
            check.measures.append(Measure("Éclaireurs différents", None, "oui", False))
        if _line_key(first.values) != _line_key(second.values):
            check.notes.append("les deux relevés ne portent pas sur la même ligne")
            check.measures.append(Measure("même ligne", None, "oui", False))
            continue
        doubled_lines.add(_line_key(first.values))
        a, b = _stops(stop_rows, target), _stops(stop_rows, second.values["id"])
        pairs = match_stops(a, b)
        union = len(a) + len(b) - len(pairs)
        jaccard = len(pairs) / union if union else None
        order = order_agreement(pairs)
        check.measures.append(
            Measure(
                "arrêts communs (Jaccard)",
                jaccard,
                f"≥ {MIN_STOPS_JACCARD:.0%}",
                None if jaccard is None else jaccard >= MIN_STOPS_JACCARD,
            )
        )
        check.measures.append(
            Measure(
                "ordre des arrêts",
                order,
                f"≥ {MIN_ORDER_AGREEMENT:.0%}",
                None if order is None else order >= MIN_ORDER_AGREEMENT,
            )
        )
        fa, fb = (
            _number(first.values.get("prix_paye", "")),
            _number(second.values.get("prix_paye", "")),
        )
        if fa is not None and fb is not None:
            gap = abs(fa - fb)
            check.measures.append(
                Measure(
                    "écart de prix (F)", gap, f"≤ {MAX_FARE_GAP_XOF} F", gap <= MAX_FARE_GAP_XOF
                )
            )
        check.notes.append(f"{len(a)} et {len(b)} arrêts, {len(pairs)} en commun")
    return len(lines), len(doubled_lines), checks


def _close(a: float, b: float, absolute: float, relative: float = 0.0) -> bool:
    return abs(a - b) <= max(absolute, relative * (a + b) / 2)


def _share(
    pairs: list[tuple[Row, Row]], name: str, absolute: float, relative: float = 0.0
) -> float:
    """Share of slots where both counts of `name` are close enough."""
    close = sum(
        _close(int(a.values[name]), int(b.values[name]), absolute, relative) for a, b in pairs
    )
    return close / len(pairs)


def _count_checks(reports: list[DirectoryReport]) -> tuple[list[Check], dict[str, tuple[int, int]]]:
    rows = _rows(reports, "comptages")
    slots: dict[tuple[str, str, str, str], list[Row]] = defaultdict(list)
    calibration: dict[str, list[int]] = {level: [0, 0] for level in QUEUE_LEVELS}
    for row in rows:
        v = row.values
        slots[(v["gare_id"], v["date"], normalise(v["ligne"]), v["tranche"])].append(row)
        if v.get("file_methode") == "comptee" and v.get("file_niveau") in QUEUE_LEVELS:
            low, high = QUEUE_LEVELS[v["file_niveau"]]
            count = int(v["file_debut"])
            calibration[v["file_niveau"]][1] += 1
            calibration[v["file_niveau"]][0] += int(
                count >= low and (high is None or count <= high)
            )
    groups: dict[tuple[str, str, str], list[tuple[Row, Row]]] = defaultdict(list)
    for (station, day, line, _), found in sorted(slots.items()):
        by_scout = {r.values["eclaireur"]: r for r in found}
        if len(by_scout) >= 2:
            first, second = sorted(by_scout)[:2]
            groups[(station, day, line)].append((by_scout[first], by_scout[second]))
    checks = []
    for (station, day, _line), pairs in groups.items():
        a0, b0 = pairs[0]
        check = Check(
            f"{station}, {day}, {a0.values['ligne']} : {a0.values['eclaireur']} et "
            f"{b0.values['eclaireur']}"
        )
        n = len(pairs)
        for label, name in (("départs à 1 près", "departs"), ("arrivées à 1 près", "arrivees")):
            value = _share(pairs, name, 1)
            check.measures.append(
                Measure(
                    label, value, f"≥ {MIN_VEHICLE_AGREEMENT:.0%}", value >= MIN_VEHICLE_AGREEMENT
                )
            )
        queue = _share(pairs, "file_debut", 3, 0.20)
        check.measures.append(
            Measure(
                "files à 20 % près",
                queue,
                f"≥ {MIN_QUEUE_AGREEMENT:.0%}",
                queue >= MIN_QUEUE_AGREEMENT,
            )
        )
        kappa = cohen_kappa(
            [a.values["file_niveau"] for a, _ in pairs], [b.values["file_niveau"] for _, b in pairs]
        )
        enough = n >= MIN_SLOTS_FOR_KAPPA
        check.measures.append(
            Measure(
                "catégories de file (kappa)",
                kappa,
                f"≥ {MIN_KAPPA:.2f}",
                None if kappa is None or not enough else kappa >= MIN_KAPPA,
            )
        )
        check.notes.append(f"{n} tranches comptées par les deux")
        if not enough:
            check.notes.append(f"moins de {MIN_SLOTS_FOR_KAPPA} tranches : kappa indicatif")
        checks.append(check)
    return checks, {k: (v[0], v[1]) for k, v in calibration.items()}


def assess(reports: list[DirectoryReport]) -> QualityReport:
    lines, doubled, surveys = _survey_checks(reports)
    share = doubled / lines if lines else None
    coverage = Measure(
        "lignes en double relevé",
        share,
        f"≥ {MIN_DOUBLED_SHARE:.0%}",
        None if share is None else share >= MIN_DOUBLED_SHARE,
    )
    counts, calibration = _count_checks(reports)
    return QualityReport(lines, doubled, coverage, surveys, counts, calibration)


def markdown(report: QualityReport) -> str:
    out = ["# Accord entre relevés (protocole qualité des Éclaireurs)", ""]
    out.append(
        f"- Lignes relevées : {report.lines} ; en double relevé : {report.doubled} "
        f"({report.coverage.text()}, seuil {report.coverage.threshold}) — "
        + (
            "conforme"
            if report.coverage.ok
            else "à compléter"
            if report.coverage.ok is False
            else "sans objet"
        )
    )
    for title, checks in (
        ("Relevés de ligne", report.surveys),
        ("Comptages en gare", report.counts),
    ):
        out += ["", f"## {title}", ""]
        if not checks:
            out.append("Aucune paire à comparer.")
            continue
        out += ["| Paire | Mesure | Valeur | Seuil | Résultat |", "|---|---|---|---|---|"]
        for check in checks:
            for m in check.measures:
                verdict = "—" if m.ok is None else ("ok" if m.ok else "**sous le seuil**")
                out.append(f"| {check.title} | {m.name} | {m.text()} | {m.threshold} | {verdict} |")
            for note in check.notes:
                out.append(f"| {check.title} | note | {note} | | |")
        out.append("")
        out.append(f"Paires acceptées : {sum(c.accepted for c in checks)} sur {len(checks)}.")
    out += [
        "",
        "## Catégories de file à l'œil, contre la file comptée",
        "",
        "| Catégorie | Tranches comptées | Dans la fourchette |",
        "|---|---|---|",
    ]
    for level, (inside, total) in report.calibration.items():
        share = f"{inside / total:.0%}" if total else "—"
        out.append(f"| {level} | {total} | {share} |")
    out += [
        "",
        "Verdict : " + ("accepté." if report.accepted else "à reprendre (voir le protocole)."),
    ]
    return "\n".join(out) + "\n"

"""Files of a run: the reports as the server would receive them, and the ground truth."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from nemesis_simulator import __version__
from nemesis_simulator.reports import Report, fixture_id, timestamp
from nemesis_simulator.scenario import hhmm
from nemesis_simulator.sim import Truth


def _csv(path: Path, header: list[str], rows: list[list[Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(header)
        writer.writerows(rows)


def _seconds(value: float | None) -> str:
    return "" if value is None else f"{value:.1f}"


def observations_jsonl(truth: Truth, reports: list[Report]) -> str:
    lines = [
        json.dumps(r.envelope(truth.scenario), ensure_ascii=False, sort_keys=True) for r in reports
    ]
    return "\n".join(lines) + ("\n" if lines else "")


def write_run(out: Path, truth: Truth, reports: list[Report], duration_s: float) -> dict[str, Any]:
    s = truth.scenario
    out.mkdir(parents=True, exist_ok=True)
    (out / "observations.jsonl").write_text(observations_jsonl(truth, reports), encoding="utf-8")
    truth_dir = out / "verite"
    _csv(
        truth_dir / "passengers.csv",
        [
            "passenger",
            "stop",
            "regime",
            "arrival_s",
            "destination",
            "lines",
            "queue_ahead",
            "vehicles_present",
            "free_front",
            "front_loading",
            "loading_elapsed_s",
            "rate_passengers_per_s",
            "rate_vehicles_per_s",
            "board_s",
            "depart_s",
            "line",
            "vehicle",
            "alight_s",
            "abandoned_s",
            "wait_s",
        ],
        [
            [
                p.id,
                p.stop,
                p.regime,
                _seconds(p.arrival_s),
                p.destination,
                " ".join(p.lines),
                p.queue_ahead,
                p.vehicles_present,
                p.free_front,
                int(p.front_loading),
                _seconds(p.loading_elapsed_s),
                f"{p.rate_passengers:.6f}",
                f"{p.rate_vehicles:.6f}",
                _seconds(p.board_s),
                _seconds(p.depart_s),
                p.line or "",
                "" if p.vehicle is None else p.vehicle,
                _seconds(p.alight_s),
                _seconds(p.abandoned_s),
                _seconds(p.wait_s),
            ]
            for p in truth.passengers
        ],
    )
    _csv(
        truth_dir / "passages.csv",
        ["t_s", "stop", "line", "vehicle", "free_seats", "boarded", "waiting"],
        [
            [_seconds(x.t_s), x.stop, x.line, x.vehicle, x.free_seats, x.boarded, x.waiting]
            for x in truth.passages
        ],
    )
    _csv(
        truth_dir / "departures.csv",
        ["t_s", "vehicle", "line", "reason", "onboard"],
        [[_seconds(d.t_s), d.vehicle, d.line, d.reason, d.onboard] for d in truth.departures],
    )
    # Head station, minute by minute: the state at the start of each minute.
    rows, index = [], 0
    states = truth.head_states
    for minute in range(s.start, s.end, 60):
        while index + 1 < len(states) and states[index + 1][0] <= minute:
            index += 1
        _, queue, vehicles = states[index]
        rows.append([hhmm(minute), queue, vehicles])
    _csv(truth_dir / "head_station.csv", ["time", "queue", "vehicles"], rows)
    _csv(
        truth_dir / "reports.csv",
        [
            "id",
            "kind",
            "contributor",
            "source_kind",
            "observed_at",
            "received_at",
            "honest",
            "fraud",
            "duplicate",
            "true_value",
            "reported",
        ],
        [
            [
                r.request["id"],
                r.request["kind"],
                r.contributor,
                r.source_kind,
                timestamp(s, r.observed_s),
                timestamp(s, r.received_s),
                int(r.honest),
                r.fraud or "",
                int(r.duplicate),
                r.true_value,
                json.dumps(r.request["payload"], ensure_ascii=False, sort_keys=True),
            ]
            for r in reports
        ],
    )
    summary = {
        "generator": f"nemesis-simulator {__version__}",
        "scenario": s.name,
        "is_fictional": True,
        "city": s.city,
        "city_id": fixture_id("city", s.city),
        "date": s.date,
        "window": [hhmm(s.start), hhmm(s.end)],
        "seed": truth.seed,
        "duration_s": round(duration_s, 3),
        "events": truth.events,
        "passengers": len(truth.passengers),
        "departures_from_head": len(truth.departures),
        "vehicles_turned_away": truth.turned_away,
        "passages": len(truth.passages),
        "abandoned": sum(p.abandoned_s is not None for p in truth.passengers),
        "longest_head_queue": max((q for _, q, _ in truth.head_states), default=0),
        "reports": len(reports),
        "reports_by_kind": _count(r.request["kind"] for r in reports),
        "fraudulent_reports": sum(not r.honest for r in reports),
        "resent_reports": sum(r.duplicate for r in reports),
    }
    (out / "run.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return summary


def _count(values: Any) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))

"""Command line: `nemesis-simulator simuler | evaluer | exemple`."""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import replace
from pathlib import Path

from nemesis_simulator.evaluate import evaluate, markdown, plausibility
from nemesis_simulator.output import observations_jsonl, write_run
from nemesis_simulator.reports import reports
from nemesis_simulator.scenario import DEFAULT_SCENARIO, Scenario, clock, load
from nemesis_simulator.sim import simulate

#: Short window of the example checked against the API contract (packages/openapi).
EXAMPLE = Path(__file__).resolve().parents[2] / "exemples" / "observations.jsonl"
EXAMPLE_SEED = 7
EXAMPLE_WINDOW = ("07:00", "07:30")


def _scenario(args: argparse.Namespace) -> Scenario:
    scenario = load(args.scenario)
    if getattr(args, "debut", None):
        scenario = replace(scenario, start=clock(args.debut))
    if getattr(args, "fin", None):
        scenario = replace(scenario, end=clock(args.fin))
    if scenario.end <= scenario.start:
        raise SystemExit("la fin doit suivre le début")
    return scenario


def _seeds(text: str) -> list[int]:
    if "-" in text:
        low, high = text.split("-")
        return list(range(int(low), int(high) + 1))
    return [int(part) for part in text.split(",")]


def example_text() -> str:
    scenario = load(DEFAULT_SCENARIO)
    scenario = replace(scenario, start=clock(EXAMPLE_WINDOW[0]), end=clock(EXAMPLE_WINDOW[1]))
    truth = simulate(scenario, EXAMPLE_SEED)
    return observations_jsonl(truth, reports(truth))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="nemesis-simulator", description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    run = commands.add_parser("simuler", help="simule une journée et écrit signalements et vérité")
    run.add_argument("--scenario", type=Path, default=DEFAULT_SCENARIO)
    run.add_argument("--graine", type=int, default=42)
    run.add_argument("--sortie", type=Path, default=Path("data/work/simulation"))
    run.add_argument("--debut", help="HH:MM, pour une fenêtre plus courte que le scénario")
    run.add_argument("--fin", help="HH:MM")

    check = commands.add_parser("evaluer", help="formules fermées contre le simulateur")
    check.add_argument("--scenario", type=Path, default=DEFAULT_SCENARIO)
    check.add_argument("--graines", default="0-4", help="« 0-4 » ou « 1,5,9 »")
    check.add_argument("--sortie", type=Path, help="dossier où écrire evaluation.json et .md")

    example = commands.add_parser("exemple", help="exemple versionné, validé contre le contrat")
    example.add_argument("--verifier", action="store_true", help="échoue si l'exemple a changé")

    args = parser.parse_args(argv)

    if args.command == "simuler":
        scenario = _scenario(args)
        started = time.perf_counter()
        truth = simulate(scenario, args.graine)
        sent = reports(truth)
        duration = time.perf_counter() - started
        summary = write_run(args.sortie, truth, sent, duration)
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        print(f"Simulation écrite dans {args.sortie} en {duration:.2f} s.", file=sys.stderr)
        return 0

    if args.command == "evaluer":
        scenario = _scenario(args)
        seeds = _seeds(args.graines)
        truths = [simulate(scenario, seed) for seed in seeds]
        result = evaluate(truths)
        checks = plausibility(truths[0], reports(truths[0]))
        result["plausibility_150m_first_seed"] = checks
        text = markdown(
            result,
            lambda: [
                f"## Règle des 150 m seule, graine {seeds[0]}",
                "",
                *(f"- {name} : {count}" for name, count in checks.items()),
            ],
        )
        if args.sortie:
            args.sortie.mkdir(parents=True, exist_ok=True)
            (args.sortie / "evaluation.json").write_text(
                json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
            (args.sortie / "evaluation.md").write_text(text, encoding="utf-8")
        print(text)
        return 0

    text = example_text()
    if args.verifier:
        if not EXAMPLE.exists() or EXAMPLE.read_text(encoding="utf-8") != text:
            print(
                f"{EXAMPLE} n'est plus à jour : lancer « nemesis-simulator exemple ».",
                file=sys.stderr,
            )
            return 1
        print(f"{EXAMPLE} est à jour.")
        return 0
    EXAMPLE.parent.mkdir(parents=True, exist_ok=True)
    EXAMPLE.write_text(text, encoding="utf-8")
    print(f"{EXAMPLE} écrit ({text.count(chr(10))} signalements).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Démo de la phase 0 (I0.13) : ce que le dépôt sait faire, hors ligne, en moins de 5 minutes.

Usage : `make demo`, ou `python3 tools/demo/demo.py [--avec-mobile]` depuis la racine.
Prérequis : uv et la chaîne Rust du dépôt (`rust-toolchain.toml`) ; Flutter pour
`--avec-mobile`. Aucun accès réseau, aucune base de données : tout tourne sur les données
fictives du dépôt. Le compte rendu est écrit dans data/work/demo/demo.md.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data/work/demo"
ROUTING = ROOT / "services/routing"
BINARY = ROUTING / "target/release/routing"
FICTIONAL_PACK = ROOT / "data/fixtures_fictives/pack"
REAL_PACK = ROOT / "data/work/packs/reel"
#: A Tuesday of the fictional calendar, at the morning peak: the demo always says the same.
WHEN = "2026-11-10T07:30"
BUDGET_S = 300

LABELS = {"cheapest": "le moins cher", "fastest": "le plus rapide", "simplest": "le plus simple"}


class Demo:
    def __init__(self) -> None:
        self.started = time.perf_counter()
        self.lines: list[str] = []
        self.failures = 0

    def say(self, text: str = "") -> None:
        print(text, flush=True)
        self.lines.append(text)

    def run(self, command: list[str], cwd: Path = ROOT) -> subprocess.CompletedProcess[str]:
        return subprocess.run(command, cwd=cwd, capture_output=True, text=True, check=False)

    def step(self, title: str, action) -> None:  # type: ignore[no-untyped-def]
        self.say(f"\n## {title}\n")
        begun = time.perf_counter()
        try:
            ok = action()
        except Exception as error:  # noqa: BLE001 — a demo reports, it does not crash
            self.say(f"Erreur : {error}")
            ok = False
        elapsed = time.perf_counter() - begun
        self.say(f"\n{'✓' if ok else '✗'} {elapsed:.1f} s")
        self.failures += 0 if ok else 1

    def check(self, result: subprocess.CompletedProcess[str], what: str) -> bool:
        if result.returncode != 0:
            self.say(f"Échec de {what} :")
            for line in (result.stdout + result.stderr).strip().splitlines()[-15:]:
                self.say(f"    {line}")
            return False
        return True


def francs(amount: int) -> str:
    """« 1 250 » : thousands separated by a narrow no-break space, as in French."""
    return f"{amount:,}".replace(",", "\u202f")


def plan_summary(demo: Demo, pack: Path, origin: str, destination: str) -> bool:
    result = demo.run(
        [
            str(BINARY),
            "plan",
            "--data",
            str(pack),
            "--from",
            origin,
            "--to",
            destination,
            "--at",
            WHEN if pack == FICTIONAL_PACK else "2023-06-13T07:30",
        ]
    )
    if not demo.check(result, "routing plan"):
        return False
    plan = json.loads(result.stdout)
    day = str(plan["date"])
    demo.say(
        f"{plan['from']} → {plan['to']}, le {day[:4]}-{day[4:6]}-{day[6:]} à {plan['time']} "
        f"({plan['day_type']}), calculé en {plan['computed_ms']:.0f} ms. "
        f"Notes : {', '.join(plan['notes']) or 'aucune'}."
    )
    demo.say("")
    demo.say("| Option | Durée (p50 à p80) | Prix | Correspondances | Étapes |")
    demo.say("|---|---|---|---|---|")
    for option in plan["options"]:
        labels = ", ".join(LABELS.get(label, label) for label in option["labels"]) or "autre"
        fare = option.get("fare")
        price = f"{francs(fare['p10'])} à {francs(fare['p90'])} F" if fare else "inconnu"
        legs = " → ".join(
            f"{leg['route_name']} (attente {leg['wait']['p50_min']} à "
            f"{leg['wait']['p80_min']} min, régime {leg['wait']['regime']})"
            if leg["type"] == "ride"
            else f"marche {leg['metres']} m"
            for leg in option["legs"]
            if leg["type"] == "ride" or leg["metres"] > 0
        )
        demo.say(
            f"| {labels} | {option['p50_min']} à {option['p80_min']} min | {price} "
            f"| {option['transfers']} | {legs} |"
        )
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--avec-mobile", action="store_true", help="lancer aussi les tests Flutter")
    args = parser.parse_args()
    demo = Demo()
    OUT.mkdir(parents=True, exist_ok=True)
    demo.say("# Démo de la phase 0")
    demo.say("")
    demo.say(
        "Tout tourne hors ligne, sur la ville fictive Lagune-Fictive : données inventées (règle 1)."
    )

    def fixtures() -> bool:
        result = demo.run(["uv", "run", "--quiet", "nemesis-fixtures", "generer", "--verifier"])
        if demo.check(result, "la vérification du jeu fictif"):
            demo.say("Le GTFS fictif, son extension, l'OSM fictif, le pack du moteur et les")
            demo.say("données de l'appli sont à jour de leur générateur.")
            return True
        return False

    def routing() -> bool:
        build = demo.run(
            ["cargo", "build", "--release", "--locked", "--quiet", "-p", "routing-cli"], ROUTING
        )
        if not demo.check(build, "la compilation du moteur"):
            return False
        demo.say("Moteur McRAPTOR à quatre critères, attentes simulées 500 fois (ADR-003) :")
        demo.say("")
        return plan_summary(demo, FICTIONAL_PACK, "Gare des Flamboyants", "Embarcadère Sud")

    def simulator() -> bool:
        run = demo.run(
            [
                "uv",
                "run",
                "--quiet",
                "nemesis-simulator",
                "simuler",
                "--graine",
                "42",
                "--sortie",
                str(OUT / "simulation"),
            ]
        )
        if not demo.check(run, "la simulation"):
            return False
        summary = json.loads(run.stdout)
        demo.say(
            f"Une journée du corridor G1 en {summary['duration_s']:.2f} s : "
            f"{summary['passengers']} passagers, "
            f"file la plus longue {summary['longest_head_queue']}, "
            f"{summary['reports']} signalements dont {summary['fraudulent_reports']} frauduleux."
        )
        check = demo.run(
            [
                "uv",
                "run",
                "--quiet",
                "nemesis-simulator",
                "evaluer",
                "--graines",
                "0-4",
                "--sortie",
                str(OUT / "simulation"),
            ]
        )
        if not demo.check(check, "l'évaluation des formules"):
            return False
        result = json.loads((OUT / "simulation/evaluation.json").read_text(encoding="utf-8"))
        demo.say("Couverture du p80 des attentes, visée 78 à 82 % (ALGORITHMES.md 1.8) :")
        demo.say("")
        for key, label in (
            ("regime_a_documented", "régime A documenté"),
            ("regime_a_corrected_profile", "régime A corrigé"),
            ("regime_b_documented", "régime B documenté"),
        ):
            rows = result[key]
            parts = [
                f"{group} {rows[group]['coverage_p80']:.0%}"
                for group in ("tous", "pointe", "pluie", "d'autres attendent")
                if group in rows and rows[group]["coverage_p80"] is not None
            ]
            demo.say(f"- {label} : {', '.join(parts)}")
        return True

    def field() -> bool:
        valid = demo.run(
            [
                "uv",
                "run",
                "--quiet",
                "nemesis-terrain",
                "valider",
                "--fictif",
                "data/fixtures_fictives/terrain",
            ]
        )
        if not demo.check(valid, "la validation des données de terrain"):
            return False
        for line in valid.stdout.strip().splitlines():
            demo.say(f"- {line.replace(str(ROOT) + '/', '')}")
        accord = demo.run(
            [
                "uv",
                "run",
                "--quiet",
                "nemesis-terrain",
                "accord",
                "--fictif",
                "--strict",
                "data/fixtures_fictives/terrain/eclaireurs",
            ]
        )
        if not demo.check(accord, "la mesure d'accord"):
            return False
        verdict = [line for line in accord.stdout.splitlines() if line.startswith("Verdict")]
        demo.say(f"Double relevé des Éclaireurs : {verdict[-1] if verdict else '?'}")
        return True

    def real() -> bool:
        if (REAL_PACK / "pack.json").exists():
            demo.say("Pack réel d'Abidjan présent (GTFS 2023, évaluation interne, H-030) :")
            demo.say("")
            return plan_summary(demo, REAL_PACK, "Adjamé Liberté", "Gare de Bassam")
        demo.say("Le pack réel n'est pas dans data/work : il demande l'extrait OSM de Geofabrik.")
        demo.say("Il se construit avec « uv run nemesis-data pack reel » (réseau requis).")
        demo.say("En CI, le workflow « Itinéraire réel de bout en bout (I0.9) » le construit et")
        demo.say("calcule des itinéraires réels à chaque modification du moteur.")
        return True

    def mobile() -> bool:
        if shutil.which("flutter") is None:
            demo.say("Flutter absent : étape passée. La CI « Mobile (Flutter) » la couvre.")
            return True
        result = demo.run(["flutter", "test", "test/app_test.dart"], ROOT / "apps/mobile")
        if demo.check(result, "les tests de l'appli"):
            demo.say("Parcours de l'appli testés : accueil, recherche, résultats, pas à pas,")
            demo.say("signalement en deux pressions, fiche gare, carte.")
            return True
        return False

    demo.step("1. Le jeu fictif", fixtures)
    demo.step("2. Le moteur d'itinéraires, hors ligne", routing)
    demo.step("3. Le simulateur et les formules d'attente", simulator)
    demo.step("4. Les données de terrain", field)
    demo.step("5. L'itinéraire réel", real)
    if args.avec_mobile:
        demo.step("6. L'appli mobile", mobile)

    total = time.perf_counter() - demo.started
    demo.say("")
    demo.say(
        f"Durée totale : {total:.0f} s (budget {BUDGET_S} s) ; "
        f"{'aucune étape en échec' if not demo.failures else f'{demo.failures} étape(s) en échec'}."
    )
    (OUT / "demo.md").write_text("\n".join(demo.lines) + "\n", encoding="utf-8")
    if demo.failures:
        return 1
    if total > BUDGET_S:
        print(f"La démo dépasse {BUDGET_S} s.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

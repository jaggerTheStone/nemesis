"""Déclare dans pubspec.yaml les données de 2023 d'Abidjan, pour l'APK de test (H-030).

Usage, depuis apps/mobile : python3 tool/avec_donnees_2023.py
Puis : flutter build apk --dart-define=NEMESIS_DATA=reel …

Elles ne sont pas déclarées par défaut : l'APK mesuré pour l'ADR-001 et les tests gardent
la ville fictive. Le script est idempotent ; « git checkout pubspec.yaml » le défait.
"""

from pathlib import Path

ANCHOR = "    - assets/fictif/pack/gtfs/\n"
EXTRA = "".join(f"    - assets/reel/{d}\n" for d in ("", "carte/", "pack/", "pack/gtfs/"))

pubspec = Path(__file__).resolve().parent.parent / "pubspec.yaml"
text = pubspec.read_text(encoding="utf-8")
if EXTRA not in text:
    if ANCHOR not in text:
        raise SystemExit("pubspec.yaml : déclaration des données fictives introuvable")
    pubspec.write_text(text.replace(ANCHOR, ANCHOR + EXTRA), encoding="utf-8")
print("données de 2023 déclarées dans", pubspec)

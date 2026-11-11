# Données de l'APK de test : lignes de 2023 d'Abidjan

Ces fichiers servent seulement à l'APK de test yafohi, pour évaluer l'appli sur des données réelles anciennes (H-030). Ils ne sont pas déclarés dans `pubspec.yaml` par défaut : `tool/avec_donnees_2023.py` les ajoute, et le build reçoit `--dart-define=NEMESIS_DATA=reel`.

- **Lignes et arrêts** : GTFS « Abidjan 2023 » de DigitalTransport4Africa, licence CC BY-NC 4.0 (pas d'usage commercial). Noms de lignes nettoyés (préfixe « gbaka : » retiré). Pas de prix, une seule fréquence par ligne. L'appli affiche « Lignes de 2023 · à confirmer ».
- **Graphe piéton, lieux, fond de carte** : © contributeurs OpenStreetMap, licence ODbL.
- **Régénérer** : `tools/maquette/appli_2023.py` (voir `tools/maquette/README.md`).

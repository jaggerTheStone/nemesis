# Données collectées

- `requetes/` : `requetes-AAAA-MM-JJ-E01.csv`
- `trajets/` : `trajets.csv` et `reponses.csv`
- `ux/<session>/` : `participants.csv`, plus `observations.csv` ou `icones.csv`
- `eclaireurs/` : un fichier par jeu, par jour et par Éclaireur (`releves_ligne-AAAA-MM-JJ-E01.csv`, `arrets_releves-…`, `gares-…`, `prix-…`, `comptages-…`), plus `photos-…` et `traces-…` exportés par l'appli

Avant chaque envoi : `uv run nemesis-terrain valider data/terrain/collecte`. En fin de semaine, pour les Éclaireurs : `uv run nemesis-terrain accord data/terrain/collecte/eclaireurs`.

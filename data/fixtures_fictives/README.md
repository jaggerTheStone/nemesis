# data/fixtures_fictives

Jeux de test entièrement fictifs (règle 1.3.1). Chaque enregistrement porte `is_fictional = true`, ou la colonne `is_fictional` à 1 dans les fichiers GTFS. Aucune donnée réelle inventée (ligne, gare, prix, horaire, nom, numéro) ne doit apparaître ici.

## La ville « Lagune-Fictive » (I0.5)

Elle est placée en pleine mer, dans le golfe de Guinée (H-027), pour ne jamais être confondue avec un lieu réel. Tous les noms portent « (fictif) ». Prix, fréquences et attentes sont des ordres de grandeur plausibles pour les tests, jamais des affirmations sur un réseau réel.

| Élément | Contenu |
|---------|---------|
| Communes | 3 : Nord, Centre, Sud ; une lagune sépare le Centre du Sud, avec un pont à l'ouest |
| Gares | 8 : 6 gares artisanales et 2 embarcadères, plus 27 arrêts informels |
| Lignes | 12 : 4 gbakas, 3 wôrô-wôrôs communaux, 2 intercommunaux, 1 bus, 1 express, 1 bateau-bus |
| Service | Fréquences par tranche (pointe, creuse, soir) pour les jours ouvrables, le samedi et le dimanche ; montée et descente continues pour le transport artisanal |
| Prix | GTFS-Fares v2 (zones = communes, paiement en espèces) et fourchettes observées par condition (normale, pointe, pluie, nuit, fête) |
| Attentes | Profils par tranche de 15 min, calculés avec les formules des régimes A et B ([ALGORITHMES.md](../../docs/ALGORITHMES.md)) |
| Repères | 16 lieux avec leurs alias (orthographes, abréviations, ancien nom) |

## Fichiers

| Chemin | Contenu |
|--------|---------|
| `gtfs/` | GTFS Schedule (dont `frequencies.txt`), GTFS-Fares v2 et extension du projet (`ext_*.txt`, ADR-007) |
| `db/seed.sql` | La même ville pour la base de développement, chargée par `docker compose up` |
| `terrain/` | Exemples fictifs des données de terrain (I0.2) |

`gtfs/` et `db/seed.sql` sont **générés** à partir d'une seule description de la ville (`data/pipelines/src/nemesis_pipelines/fixtures/city.py`), avec une graine fixe :

```bash
uv run nemesis-fixtures generer            # régénérer après une modification
uv run nemesis-fixtures generer --verifier # vérifier (lancé par make check et en CI)
make gtfs-validate                         # validateur MobilityData (Docker, accès à GHCR)
```

Comme l'exige l'ADR-007, le GTFS ne publie que les profils et estimations qui reposent sur au moins 20 contributeurs distincts. La base de développement les reçoit tous, avec une confiance « faible » sous ce seuil.

Après la mise à jour d'I0.5, une base de développement créée en I0.4 doit être recréée avec `make dev-reset`, puis `make dev` : les identifiants du jeu de départ ont changé.

# services/routing

Moteur d'itinéraires en Rust (option B de la partie 8.1, retenue par l'[ADR-003](../../docs/DECISIONS/ADR-003-moteur-itineraires.md) après le spike I0.8 ; McRAPTOR depuis I0.9).

## Composants

- `routing-core` : bibliothèque partagée entre le serveur et le téléphone (le cœur compile pour Android arm64).
  - `gtfs` : lecture du GTFS, avec les calendriers et l'extension nemesis (profils d'attente, prix estimés, zones et alias d'arrêts).
  - `network` : réseau à fréquences, une variante par course avec ses tranches ; points de montée virtuels le long des tracés (option).
  - `walk` : graphe piéton du pack, rattachement des points à moins de 200 m, Dijkstra borné.
  - `model` : lois d'attente (régime A par les profils, régime B par les intervalles du GTFS), prix par zones, générateur pseudo-aléatoire à graine.
  - `mcraptor` : McRAPTOR à quatre critères (arrivée avec attentes médianes, prix p50, marche par tranches de 250 m, véhicules).
  - `options` : Monte-Carlo (500 tirages), front de Pareto, quasi-doublons, étiquettes.
  - `engine` : interface `RoutingEngine` et son implémentation `McRaptorEngine` ; recherche de lieux par coordonnées ou par nom d'arrêt.
  - `raptor` : RAPTOR du spike I0.8, conservé pour `routing spike`.
- `routing-cli` : binaire `routing`.

## Pack ville (format 1)

Un dossier produit par `nemesis-data pack reel` ([data/pipelines](../../data/pipelines/README.md)) ou versionné pour les fixtures (`data/fixtures_fictives/pack`) :

- `pack.json` : ville, version du réseau, données fictives ou non, usage (`produit` ou `evaluation`), chemins, sources ;
- le GTFS (dossier `gtfs`, chemin donné par `pack.json`) ;
- `walk_nodes.csv` (`node,lat,lon`) et `walk_edges.csv` (`from,to,metres`) : graphe piéton non orienté tiré d'OSM, nœuds aux intersections et au plus tous les 100 m.

## Commandes

```bash
cargo run --release -p routing-cli -- plan \
  --data ../../data/fixtures_fictives/pack \
  --from "Gare des Flamboyants" --to "Embarcadère Sud" --at 2026-11-10T07:30
```

- `routing plan --from <lat,lon|lieu> --to <lat,lon|lieu> --at <AAAA-MM-JJTHH:MM> --data <pack> [--virtual-spacing <m>]` écrit un JSON :
  - les options étiquetées `cheapest`, `fastest`, `simplest` (une option peut en porter plusieurs ; d'autres options sans étiquette si elles restent raisonnables) ;
  - pour chaque option : durées p50 et p80 en minutes, heures d'arrivée, correspondances, marche, fourchette de prix arrondie à 50 F ou `null` si inconnue ;
  - pour chaque étape : sa source (`osm_walking_graph`, `straight_line`, `gtfs_timetable`) et, pour l'attente, son régime (`A` ou `B`), sa source et ses quantiles ;
  - des notes : `fictional_data`, `evaluation_only_data`, `fares_unknown`, `no_service` ;
  - la graine et le nombre de tirages, pour rejouer le calcul.
- `routing bench --data <pack> --pairs <couples.csv> --date <AAAA-MM-JJ> --out <mesures.json>` mesure la latence sur des couples origine-destination (trois heures par défaut).
- `routing spike` mesure l'option B du spike ([tools/routing-spike](../../tools/routing-spike/README.md)).

Un lieu donné par son nom est cherché parmi les arrêts et leurs alias, sans accents ni casse ; plusieurs arrêts à moins de 500 m les uns des autres sont fusionnés, sinon le lieu est déclaré ambigu.

## Simplifications de la v0 (règle 1.3.8)

- Marche sans pénalités (traversées, zones inondées) ; un arrêt hors du graphe piéton est rejoint en ligne droite × 1,3, et l'étape l'indique.
- Temps à bord tirés des horaires du GTFS, sans vitesses par tronçon ni tirage aléatoire.
- Régime A modélisé par une loi log-normale ajustée sur p50 et p80, en attendant la loi Gamma de la section 1.2 d'ALGORITHMES.md.
- Prix estimés en condition « normale » seulement, sans pluie ni nuit.
- Paramètres à calibrer (H-032) : tranches de marche de 250 m, filtre des options sans étiquette, 5 options au plus.

## Tests

- `make check-rust` : formatage, Clippy, tests (dont les tests par propriétés sur des villes en grille tirées au hasard, et les tests sur le pack fictif).
- Workflow « Itinéraire réel de bout en bout (I0.9) » : pack réel d'Abidjan, itinéraires et latence.
- Audit : `make audit-rust` (cargo-deny : vulnérabilités, licences permissives, sources).
- Version de Rust figée dans `rust-toolchain.toml`.

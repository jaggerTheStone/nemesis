# tools/routing-spike

Spike du moteur d'itinéraires (incrément I0.8) : il compare les deux options de l'[ADR-003](../../docs/DECISIONS/ADR-003-moteur-itineraires.md) sur les mêmes couples origine-destination.
- **Option A** : OpenTripPlanner 2.10, image épinglée dans `data/pipelines/sources.toml`.
- **Option B** : RAPTOR à fréquences en Rust, commande `routing spike` de [services/routing](../../services/routing/README.md).

```bash
make routing-spike   # Docker, osmium-tool, cargo et accès à Geofabrik ; sinon le workflow de CI
```

Le workflow « Spike du moteur d'itinéraires (ADR-003) » tourne à chaque modification du moteur ou de ces outils. Il écrit la comparaison dans son journal et la conserve en artefact.

| Fichier | Rôle |
|---------|------|
| `couples.csv` | Les 25 couples du spike. Ils sont tirés des arrêts réels du GTFS « Abidjan 2023 » (identifiants de nœuds OSM), sans rien inventer, et ne servent qu'à l'évaluation interne (H-030). |
| `select_pairs.py` | Sélection reproductible des couples, détaillée ci-dessous. |
| `otp.py` | Option A : construction du graphe (temps, mémoire, avertissements), service, requêtes GraphQL chronométrées. |
| `compare.py` | Réévalue les itinéraires des deux moteurs avec une seule fonction de coût, puis écrit `comparaison.md` et `comparaison.json`. |
| `run.sh` | Toute la chaîne : extrait OSM de l'emprise, option B en trois variantes, option A, comparaison. |

## Les couples

Le corridor pilote n'est pas encore choisi (décision du porteur). Les couples couvrent donc le réseau :
- **pôles** : les arrêts où commencent ou finissent le plus de courses, fusionnés à moins de 300 m (24 pôles) ;
- **20 couples entre pôles**, sans utiliser un pôle plus de deux fois : 5 courts (2 à 5 km), 8 moyens (5 à 10 km), 7 longs (plus de 10 km) ;
- **5 couples « bord de route »** : départ sur le tracé même d'une ligne, au milieu d'un intervalle de plus de 800 m entre deux arrêts. Ils éprouvent la montée entre deux arrêts.

Chaque couple est demandé à 06:30, 11:00 et 18:30, un mardi (2023-06-13, dans le calendrier du GTFS).

Quand le corridor pilote sera choisi, ses couples remplaceront ceux-ci. La suite de trajets de référence (I0.2) permettra alors de noter le réalisme.

## La fonction de coût commune

`compare.py` recalcule la durée de chaque itinéraire, quel que soit le moteur qui l'a produit :
- **marche** : ligne droite × 1,3 à 4,5 km/h ;
- **attente** : médiane du régime B, ln 2 × intervalle de la tranche (ALGORITHMES.md, section 1.3) ;
- **trajet** : temps du GTFS entre la montée et la descente.

Avec `--seed`, chaque attente est multipliée, pour chaque arrêt et chaque ligne, par un facteur entre 0,5 et 3, tiré d'un hachage. Ce sont des **attentes en direct simulées**, jamais présentées comme des observations ; Rust (`SimulatedLive`) et Python les calculent de la même façon, ce que vérifie un test.

Le script vérifie aussi que les durées calculées par l'option B suivent exactement cette fonction.

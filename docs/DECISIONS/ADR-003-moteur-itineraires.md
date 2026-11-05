# ADR-003 — Moteur d'itinéraires

- **Statut** : accepté, figé en I0.8 après le spike demandé par la partie 8.1. Le porteur peut le rouvrir à la relecture.
- **Date** : 2026-11-04, figé le 2026-11-05
- **Casquettes consultées** : ingénieur transport, architecte, ingénieur mobile, SRE

## Contexte

Le réseau artisanal est surtout un réseau **à fréquences**, sans horaires :
- les gbakas partent quand ils sont pleins ;
- la montée et la descente sont **continues** le long de la ligne ;
- le coût de montée réel est l'**attente estimée en direct**, différente selon la gare et l'heure.

Le calcul doit produire un **front de Pareto** multicritère : temps au 80e centile, temps médian, coût en FCFA, changements, marche, et la nuit une pénalité de sûreté. Il doit donner **les mêmes résultats en ligne et hors ligne**.

Budgets (9.3) : 2 s au 95e centile côté serveur, 3 s sur le téléphone de référence.

## Options

| | A : OpenTripPlanner 2, puis réévaluation des candidats | B : RAPTOR à fréquences maison, en Rust |
|---|---|---|
| Principe | OTP calcule des itinéraires ; on les réévalue ensuite avec l'attente en direct | L'attente en direct est le coût de montée, dans le calcul même |
| Hors ligne, mêmes résultats | Impossible : Java, non embarquable sur le téléphone | Le même code sur le serveur et le téléphone |
| Licence | LGPL-3.0, utilisable comme service séparé | Notre code |

## Le spike (I0.8)

Outils et mode d'emploi : [tools/routing-spike](../../tools/routing-spike/README.md). Mesures : workflow « Spike du moteur d'itinéraires (ADR-003) », exécution du 2026-11-05.

**Données** :
- le GTFS « Abidjan 2023 », en évaluation interne seulement (H-030) : 4 834 arrêts, 980 courses à fréquences ;
- l'extrait OSM d'Abidjan découpé dans celui de Geofabrik (emprise de H-029).

**Requêtes** : 25 couples tirés des arrêts réels, à 06:30, 11:00 et 18:30 un mardi, soit 75 requêtes.
- 20 couples entre pôles : 5 courts, 8 moyens, 7 longs ;
- 5 couples partant du bord de la route, entre deux arrêts éloignés.

**Option A** : OpenTripPlanner 2.10.0 (image épinglée), configuration par défaut, sauf les bornes du calendrier. 5 itinéraires demandés par requête.

**Option B** : premier moteur dans `services/routing` :
- réseau à fréquences, une variante par course ;
- attente médiane du régime B (ln 2 × intervalle) comme coût de montée ;
- correspondances à pied jusqu'à 400 m ;
- accès et sortie jusqu'à 800 m ;
- une variante avec des points de montée virtuels tous les 250 m le long des tracés.

**Comparaison équitable** : les itinéraires des deux moteurs sont recalculés avec **une seule fonction de coût** (marche, attente, trajet du GTFS). Seule la recherche diffère donc. Deux jeux d'attentes sont testés :
1. les attentes médianes du régime B ;
2. des **attentes en direct simulées** : la médiane multipliée par un facteur de 0,5 à 3 par arrêt et par ligne, tiré d'un hachage reproductible.
   - Le second jeu imite une file longue ici, courte là.
   - Ce sont des conditions de test, pas des observations.
   - A réévalue ses candidats avec ces attentes ; B calcule directement avec.

### Mesures

| Mesure | A : OpenTripPlanner 2.10 | B : RAPTOR à fréquences | B avec points de montée virtuels |
|--------|--------------------------|--------------------------|----------------------------------|
| Préparation | Graphe en 23 s, 1,36 Gio de mémoire au plus, 45,5 Mio sur disque | 45 ms | 293 ms (13 774 points virtuels, 1,3 million de liaisons à pied) |
| Mémoire en service | 1 019 Mio (JVM) | 12 Mio | 43 Mio |
| Latence par requête | Médiane 689 ms, pire requête 5,1 s, HTTP compris | Médiane 0,6 ms, 95e centile 0,9 ms | Médiane 1,9 ms, 95e centile 2,5 ms |
| Requêtes sans itinéraire | 0 sur 75 | 0 sur 75 | 0 sur 75 |
| Options distinctes par requête | 1 à 3 lignes différentes sur 5 itinéraires : les autres répètent la même ligne aux départs suivants | 1 à 3 options sur le front « arrivée × nombre de véhicules » | idem |
| Compile pour Android arm64 | Non (JVM) | Oui : `cargo check --target aarch64-linux-android` en CI | Oui |

**Avec la même fonction de coût :**

| Jeu d'attentes | Requêtes comparées | B meilleur de plus de 5 min | A meilleur de plus de 5 min | Gain médian de B | Gain maximal de B |
|----------------|--------------------|-----------------------------|-----------------------------|------------------|-------------------|
| Attentes médianes du régime B | 75 | 9 | 5 | 0,1 min | 42,9 min |
| Attentes en direct simulées | 74 (1 couple sans trajet faisable dans les deux) | **44** | 3 | **9,2 min** | 49,5 min |
| B sans puis avec l'attente dans le calcul | 74 | 47 | 0 | 8,4 min | 49,0 min |

### Constats

**Option A, OpenTripPlanner 2.10 :**
- **Fréquences** : OTP lit `frequencies.txt` sans horaires exacts comme des départs réguliers. Il fait partir le véhicule un **intervalle complet** après l'heure demandée (vérifié sur le jeu fictif : départ à 06:35:12 pour 06:30, intervalle de 312 s). C'est une attente fixe et pessimiste, qui ignore l'état en direct. Le régime B donne 0,69 fois l'intervalle en médiane.
- **Montée continue** : même déclarée (`continuous_pickup = 0`), OTP ne fait pas monter entre deux arrêts. Il fait marcher jusqu'à l'arrêt suivant : 568 m dans le test fictif.
- **Piège de configuration** : par défaut, OTP ne garde le service que d'un an en arrière à trois ans en avant de la date du jour. Le GTFS de 2023 serait vidé de tout service sans les bornes `transitServiceStart` et `transitServiceEnd`.
- **Latence et mémoire** :
  - la médiane, 0,7 s, tient le budget serveur de 2 s, mais la pire requête prend 5,1 s ;
  - il faut environ 1 Gio de mémoire pour un réseau de 4 834 arrêts ;
  - impossible à embarquer sur le téléphone.
- **Réévaluation** : avec les attentes en direct simulées, la meilleure option parmi les candidats d'OTP est plus lente de plus de 5 min dans 44 requêtes sur 74 que l'optimum calculé avec ces attentes. C'est le défaut prévu par cet ADR, désormais mesuré : l'option qui deviendrait la meilleure n'est pas parmi les candidats.

**Option B, RAPTOR à fréquences :**
- Elle tient les budgets avec une marge de trois ordres de grandeur, même avec les points de montée virtuels. Sa mémoire est compatible avec un téléphone de 2 Go.
- **Points de montée virtuels** : ils raccourcissent souvent la marche et la durée. Ils comptent surtout pour les couples « bord de route ».
- **Équivalence avec A sans état en direct** : gain médian de 0,1 min.
- **Cas où A fait mieux de plus de 5 min**, avec les attentes médianes :
  - OD07 à 06:30 (8 min) ;
  - OD21 à 06:30 (6 min) ;
  - OD23 aux trois heures (9 à 10 min).

  Ce sont des départs en bord de route ou loin des arrêts. Piste à vérifier en I0.9 : B limite l'accès à 800 m à vol d'oiseau, alors qu'OTP marche plus loin, sur le vrai réseau de rues.
- **Défaut trouvé et corrigé pendant le spike** : la vérification croisée de `compare.py` a trouvé 3 trajets dont l'arrivée annoncée dépassait de 98 s celle des étapes. Une correspondance à pied partait d'un arrêt déjà atteint à pied dans le même tour. Les arrivées en véhicule sont désormais séparées de la marche, avec un test de non-régression.

**Données (les deux options) :**
- 271 des 980 courses du GTFS 2023 (28 %) durent exactement 120 min, à 2–6 km/h : ce sont manifestement des valeurs par défaut. Les 709 autres roulent à 11–18 km/h (écart interquartile).
- Les deux moteurs utilisent ces temps tels quels ; ils pèsent sur le réalisme, pas sur la comparaison.
- Le GTFS ne contient ni prix (`fare_attributes.txt` vide) ni montée continue déclarée.

### Ce que le spike n'a pas pu mesurer (écarts au protocole)

- **Réalisme selon la règle de notation** ([protocole](../TERRAIN/PROTOCOLE-TRAJETS-REFERENCE.md)) : il faut les réponses de la suite de trajets de référence, dont la collecte attend une équipe sur place (Q-03). Le spike n'en donne que des indices, comme l'équivalence de A et B en attentes médianes. La notation se fera en I0.9 ou dès que la suite existera.
- **Corridor pilote** : il n'est pas choisi (décision du porteur). Les couples couvrent donc tout le réseau.
- **Temps de réponse sur le téléphone de référence** : il faut l'appareil. Le spike vérifie seulement que le cœur compile pour Android arm64. La mesure sur téléphone se fera en I0.11, avec le prototype Flutter. À 2 ms sur le serveur, le budget de 3 s laisse une marge de plus de mille fois.
- **Marche de B** : estimée en ligne droite × 1,3, sans le graphe piéton d'OSM (Dijkstra en I0.9). Dans la comparaison, les deux moteurs sont pourtant notés avec la même règle de marche.
- **Critère de prix** : aucun des deux ne peut produire « Le moins cher » sur ce GTFS, faute de prix.

## Décision

**Option B : RAPTOR à fréquences en Rust, étendu en McRAPTOR en I0.9.**

Raisons, mesurées :
1. **L'attente en direct dans le calcul change le résultat.**
   - Avec des attentes qui varient d'un arrêt à l'autre, réévaluer les candidats d'OTP perd plus de 5 min dans 44 requêtes sur 74 (médiane 9,2 min).
   - À moteur égal, mettre l'attente dans le calcul gagne 8,4 min en médiane.
2. **Mêmes résultats en ligne et hors ligne** : seul B tourne sur le téléphone. Le cœur compile pour Android arm64, avec 12 à 43 Mio de mémoire.
3. **Budgets** : B répond en millisecondes. A dépasse le budget serveur sur sa pire requête (5,1 s) et demande environ 1 Gio.
4. **Fréquences et montée continue** : OTP 2.10 modélise les unes par un intervalle complet et ignore l'autre. B les modélise directement.

**OpenTripPlanner reste un outil de comparaison**, gardé dans `tools/routing-spike` :
- ses itinéraires servent de référence indépendante dans le workflow du spike ;
- le repli de la version proposée (OTP comme moteur serveur provisoire) n'est plus nécessaire.

## Conséquences

**I0.9** :
- interface `RoutingEngine` ;
- McRAPTOR (temps p50 et p80, coût, changements, marche) ;
- marche sur le graphe piéton d'OSM, jusqu'à environ 1,5 km, ce qui répond aussi aux cas où A faisait mieux ;
- Monte-Carlo ;
- options étiquetées ;
- tests par propriétés (14.1) ;
- notation du réalisme dès que la suite de référence existe.

**Autres conséquences** :
- **Points de montée virtuels** : gardés, avec un pas de 250 m à calibrer (150 à 300 m dans ALGORITHMES.md). Ils seront placés là où l'on monte réellement, quand les relevés des Éclaireurs existeront.
- **I0.11** : mesure sur le téléphone de référence, par une liaison native entre Flutter et le cœur Rust.
- **Données** : les durées de 120 min du GTFS 2023 sont signalées dans DATA.md. Le temps à bord viendra des vitesses par tronçon (ALGORITHMES.md, section 6) dès qu'il y aura des observations.
- **Risque** : le vivier de développeurs Rust en Côte d'Ivoire (Q-02). Le cœur du moteur reste petit et fortement testé.
- **Réversibilité** : bonne. L'interface `RoutingEngine` isole le reste du système.
- **À revoir si** :
  - la mesure sur téléphone dépasse 3 s ;
  - le McRAPTOR complet sort des budgets ;
  - une version d'OTP modélise un jour l'attente en direct et la montée continue.

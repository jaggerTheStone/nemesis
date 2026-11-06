# tools/simulator

Simulateur par agents d'un corridor (I0.10). Il produit, sans données de terrain :
- un flux de signalements au format de l'API ;
- la vérité terrain correspondante.

Il sert à tester l'agrégation, les estimations et la charge. Il sert d'abord à confronter les formules d'attente d'[ALGORITHMES.md](../../docs/ALGORITHMES.md) à une simulation (sections 1.2 et 1.3). Ce dossier s'ajoute à l'arborescence de la partie 9.7 (H-015).

**Tout est fictif** (règle 1) :
- le scénario reprend les arrêts, les intervalles et les tarifs du jeu `fixtures_fictives` ;
- les débits de passagers, les occupations et les comportements sont des paramètres choisis (H-033) ;
- le chargeur refuse un scénario qui ne se déclare pas fictif.

## Lancer

```bash
make simulation        # journée de pointe (graine 42) et évaluation sur 5 graines, dans data/work/simulation
uv run nemesis-simulator simuler --graine 42 --sortie data/work/simulation [--debut 07:00 --fin 09:00]
uv run nemesis-simulator evaluer --graines 0-4 [--sortie data/work/simulation]
uv run nemesis-simulator exemple [--verifier]   # exemple versionné, validé contre le contrat
```

Une journée de 5 h à 22 h se simule en environ 0,1 s ; la même graine donne les mêmes fichiers.

## Le corridor simulé

Il est décrit par le scénario [`scenarios/corridor-g1.toml`](scenarios/corridor-g1.toml) : la ligne G1 de Lagune-Fictive, sens 0, de la Gare des Flamboyants à la Gare du Grand Marché, un jour ouvrable.

- **Gare de tête, régime A.**
  - Les passagers arrivent selon un processus de Poisson ; le débit est constant sur chaque tranche de 15 min.
  - Les gbakas vides arrivent selon un processus de renouvellement : intervalles Gamma de coefficient de variation 0,81, comme dans le GTFS fictif. Le débit suit le profil de la journée.
  - Au-delà de 3 véhicules en attente, un véhicule qui arrive repart ailleurs.
  - Les véhicules chargent l'un après l'autre, dans l'ordre d'arrivée des passagers. Chacun part 1 min (*d*₀) après être plein, ou 20 min (*T*max) après son premier passager.
- **Bord de route, régime B.**
  - Les gbakas de G1 et le bus B1 qui longe le corridor s'arrêtent si quelqu'un descend ou monte.
  - Un passager prend le premier véhicule qui a une place et dessert sa destination.
  - Quand il y a plus de monde que de places, l'ordre de montée est tiré au hasard (bousculade) ou suit l'ordre d'arrivée (`boarding = "fifo"`).
  - Passé sa patience (20 à 60 min), le passager renonce : son attente est censurée.
- **Pluie** (16 h 45 à 18 h) : 30 % de véhicules en moins, 15 % de passagers en plus, trafic 40 % plus lent, prix « pluie ».

## Sorties

| Fichier | Contenu |
|---------|---------|
| `observations.jsonl` | Un signalement par ligne, dans l'ordre de réception. Chaque ligne contient : `request`, un `ContributionRequest` valide ; `received_at` ; `source_kind` ; `contributor`, un pseudonyme `sim-…` |
| `verite/passengers.csv` | Chaque passager : arrêt, régime, arrivée, état vu à l'arrivée (file devant, véhicules, places libres, débits), montée, départ, descente, abandon, attente |
| `verite/passages.csv` | Chaque passage d'un véhicule à un arrêt de bord de route : places libres, montées, personnes en attente |
| `verite/departures.csv` | Chaque départ de la gare de tête, avec sa raison (`plein`, `attente_max`) |
| `verite/head_station.csv` | File et véhicules présents à la gare de tête, minute par minute |
| `verite/reports.csv` | La vérité de chaque signalement : honnête ou non, type de fraude, renvoi, valeur vraie, valeur déclarée |
| `run.json` | Résumé : graine, durée, volumes |

Les identifiants d'arrêts et de lignes sont ceux de la ville fictive en base (`uuid5`, `data/pipelines/.../fixtures/sql.py`).

## Signalements

Champs propres à chaque type (`payload`, H-033) :

| Type | `payload` |
|------|-----------|
| `file` | `level` : `peu`, `moyen`, `beaucoup`, `tres_long` |
| `vehicules_presents` | `vehicles` : `aucun`, `1_2`, `3_plus` |
| `attente_reelle` | `wait_s` |
| `prix_paye` | `amount_xof` |
| `vehicule_plein` | rien |

Ce que les données ont de réaliste :
- **Bruit** : une catégorie de file ou de véhicules sur cinq glisse vers sa voisine. Les attentes déclarées sont arrondies à la minute, avec une erreur log-normale.
- **Retards** : envoi après 20 s en moyenne ; 10 % des envois attendent le réseau, jusqu'à 30 min.
- **Renvois** : 3 % des signalements sont renvoyés avec le même identifiant, pour tester l'idempotence.
- **Chef de gare vérifié** : un relevé exact de la file et des véhicules toutes les 10 min en moyenne.
- **Fraude** : 3 pseudonymes signalent une file « très longue » depuis 2,5 km, ou un prix triplé.

## Formules contre la simulation (`evaluer`)

À chaque passager, la formule reçoit l'état réel du système à son arrivée et les débits réels : c'est un oracle. On mesure ainsi l'erreur de la formule seule, pas celle de l'estimation de ses entrées.

On juge la couverture du p80 comme en section 1.8 d'ALGORITHMES.md : l'intervalle de Wilson à 95 % est comparé à la bande de 78 à 82 %. Les passagers d'un même véhicule ne sont pas indépendants : cet intervalle est donc trop étroit, d'où l'évaluation sur 5 graines.

Les formules évaluées :
- **Régime A** :
  - la formule documentée ;
  - une formule corrigée, qui attend aussi le remplissage du véhicule ;
  - la même, intégrée sur les débits des tranches à venir.
- **Régime B** :
  - l'exponentielle documentée ;
  - une borne qui compte les personnes déjà en attente.

Résultats et conclusions : [ALGORITHMES.md](../../docs/ALGORITHMES.md), sections 1.2 et 1.3. Le workflow Python affiche l'évaluation dans le résumé de son exécution.

## Tests

`uv run pytest tools/simulator`, soit 19 tests en environ 10 s.

- **Exemples numériques** : ceux d'ALGORITHMES.md sont retrouvés.
- **Formules** : elles sont calibrées quand leurs hypothèses tiennent (débits constants, arrivées de Poisson).
- **Constats** : les constats sur le corridor sont vérifiés.
- **Simulation** : durée, reproductibilité, ordre d'arrivée à la gare, places.
- **Signalements** : bruit, retards, renvois, fraude, règle des 150 m.
- **Contrat** : identifiants de la base, exemple à jour.

L'exemple versionné ([`exemples/observations.jsonl`](exemples/observations.jsonl), 7 h à 7 h 30, graine 7) est validé contre le contrat OpenAPI par `packages/openapi/test/simulator-reports.test.ts`.

## Limites (règle 1.3.8)

- **Un seul corridor et un seul sens.** Pas de réseau, ni de retour des véhicules : l'offre à la gare de tête est un processus exogène.
- **Temps à bord** : ils suivent les horaires du GTFS fictif, multipliés par un facteur de trafic et un bruit log-normal. Pas de congestion modélisée.
- **Bord de route** : un passager qui renonce disparaît. Il ne marche pas jusqu'à la gare et ne prend pas de taxi.
- **Comportements fictifs** : le comportement des signaleurs et des fraudeurs est inventé et devra être recalé sur les premières données du pilote.

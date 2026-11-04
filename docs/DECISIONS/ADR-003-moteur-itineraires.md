# ADR-003 — Moteur d'itinéraires

- **Statut** : proposé. Il sera figé en I0.8, après le spike de deux jours demandé par la partie 8.1.
- **Date** : 2026-11-04
- **Casquettes consultées** : ingénieur transport, architecte, ingénieur mobile, SRE

## Contexte

Le réseau artisanal est surtout un réseau **à fréquences**, sans horaires :
- les gbakas partent quand ils sont pleins ;
- la montée et la descente sont **continues** le long de la ligne ;
- le coût de montée réel est l'**attente estimée en direct**, différente selon la gare et l'heure.

Le calcul doit produire un **front de Pareto** multicritère : temps au 80e centile, temps médian, coût en FCFA, changements, marche, pénalité de sûreté la nuit. Il doit donner **les mêmes résultats en ligne et hors ligne**.

Budgets : 2 s au 95e centile côté serveur, 3 s sur le téléphone de référence (9.3).

## Options envisagées

| Critère | A : OpenTripPlanner 2, puis réévaluation | B : McRAPTOR maison en Rust |
|---------|------------------------------------------|------------------------------|
| Délai de mise en œuvre | Court : GTFS et OSM gérés d'emblée | Plus long : moteur, graphe piéton, préparation des données |
| Réseau à fréquences | `frequencies.txt` pris en charge ; traitement exact à vérifier dans le spike | Conçu pour : intervalles et lois d'attente natives |
| Montée continue | Prise en charge à vérifier dans le spike | Points de montée virtuels tous les 150 à 300 m |
| Attente en direct comme coût de montée | Non native : réévaluation après coup des itinéraires candidats, sans garantie que le meilleur soit parmi eux | Native : la loi d'attente entre dans le calcul |
| Critère de prix (FCFA) dans le Pareto | Limité ; réévaluation après coup | Natif |
| Hors ligne, mêmes résultats | Impossible (Java, pas embarquable sur le téléphone) : il faudrait un second moteur | Le même code sur le serveur et le téléphone |
| Mémoire et exploitation | Service Java ; mémoire du graphe à mesurer | Petit binaire ; réseau précompilé |
| Licence | LGPL-3.0 : compatible avec un code propriétaire si utilisé comme service séparé | Notre code |

D'autres moteurs existent. Ils ne seront évalués que si A et B échouent tous les deux.

## Protocole du spike (I0.8, deux jours)

1. **Données et requêtes** : le GTFS Abidjan 2023 et l'extrait OSM, importés en I0.7, et 20 couples origine-destination du corridor pilote, à trois heures différentes.
2. **Option A** : vérifier que le GTFS se charge et voir comment les fréquences et la montée continue sont traitées. Mesurer le temps de réponse et la mémoire. Tester la réévaluation des candidats avec des attentes simulées.
3. **Option B** : un RAPTOR à fréquences minimal, avec un coût de montée égal à l'attente médiane. Mesurer le temps de réponse sur le serveur et sur un téléphone Android (bibliothèque compilée pour arm64).
4. **Comparaison** sur les 20 couples :
   - réalisme, jugé par la règle de notation de la suite de référence ([protocole](../TERRAIN/PROTOCOLE-TRAJETS-REFERENCE.md)) ;
   - temps de réponse ;
   - capacité à produire les trois options étiquetées.

## Décision proposée, avant le spike

**L'option B est la cible, comme la recommande la partie 8.1.** Deux exigences ne sont satisfaites que par elle :
- les **mêmes résultats en ligne et hors ligne** ;
- l'**attente en direct dans le calcul** même.

Avec l'option A, la réévaluation après coup ne garantit pas de trouver la meilleure option : si OpenTripPlanner écarte l'option qui deviendrait la meilleure une fois l'attente réelle connue, aucune réévaluation ne la retrouvera.

**Repli** : si le spike montre que B ne peut pas être prêt pour la phase 1, A sert de moteur serveur provisoire. Le calcul hors ligne passe alors en mode dégradé : itinéraires préenregistrés et attentes historiques. Ce mode dégradé devra être documenté (règle 1.3.3).

**Désaccord entre casquettes.** Le SRE et le product manager voient dans A un démarrage plus rapide et moins de code à maintenir. L'ingénieur transport et l'ingénieur mobile voient dans B la seule réponse aux deux exigences ci-dessus. On tranche par le spike, avec le repli explicite décrit ci-dessus. Un risque reste à peser : le vivier de développeurs Rust en Côte d'Ivoire est probablement étroit (question Q-02).

## Conséquences

- **Coût de B** : plus de travail initial ; il faut construire le graphe piéton depuis OSM et tester finement le moteur. Les tests par propriétés de la partie 14.1 (aucune option dominée, monotonie, symétrie raisonnable) deviennent essentiels.
- **Réversibilité** : bonne. Une interface unique `RoutingEngine` (8.1) isole le reste du système, ce qui permet de changer de moteur sans toucher à l'API ni à l'appli.
- **À revoir si** le spike montre un temps de réponse de B supérieur à 3 s sur le téléphone, ou une préparation des données hors de portée de la phase 1.

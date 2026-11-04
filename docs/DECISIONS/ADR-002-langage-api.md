# ADR-002 — Langage et framework de l'API principale

- **Statut** : proposé
- **Date** : 2026-11-04
- **Casquettes consultées** : architecte, ingénieur backend, SRE, product manager

## Contexte

L'API principale est un monolithe modulaire (9.1). Elle sert les recherches de lieux, les fiches de gare, les contributions, l'état en direct, les packs, les comptes et le back-office.

Le calcul d'itinéraire, la partie la plus gourmande en processeur, est confié au service Rust (ADR-003). Les modèles d'apprentissage sont confiés au service Python.

Cibles de la deuxième année (9.4) :
- 300 000 utilisateurs actifs par jour ;
- 50 000 connectés simultanément en pointe ;
- 2 000 événements entrants par seconde ;
- pics brutaux pendant les pluies.

Le squelette d'I0.1 utilise déjà NestJS 12 sur Fastify.

## Options envisagées

| Critère | TypeScript et NestJS | Go | Autres (Kotlin et Spring, Python et FastAPI, Rust) |
|---------|----------------------|-----|----------------------------------------------------|
| Débit et mémoire | Corrects pour des entrées-sorties ; un seul fil d'exécution par processus, donc plusieurs processus par machine | Meilleurs : concurrence native, faible mémoire par connexion | Kotlin bon mais JVM gourmande ; Python plus lent ; Rust excellent |
| Coût d'exploitation | Un peu plus de machines à charge égale | Le plus bas | Variable |
| Recrutement en Côte d'Ivoire | Vivier JavaScript et TypeScript large ; à vérifier | Vivier plus étroit ; à vérifier | Java courant ; Rust rare |
| Partage avec le reste du code | Types partagés avec le back-office (React) et les pages légères ; types générés depuis OpenAPI | Génération depuis OpenAPI | Aucun partage |
| Maturité (validation, OpenAPI, tests, ORM) | Très bonne | Bonne, plus artisanale | Bonne |
| Nombre de langages dans le dépôt | Aucun en plus | Un cinquième langage | Un de plus |

## Décision proposée

**TypeScript avec NestJS 12, sur Fastify.**

1. **Les calculs lourds sont ailleurs.** L'API fait surtout des entrées-sorties (PostgreSQL, Redis, NATS), un domaine où Node est efficace.
2. **Le recrutement et le partage de code** avec le back-office priment, à ce stade, sur le gain de machines qu'apporterait Go.
3. **La diffusion de l'état en direct est isolée dans un module** (`live`) derrière une interface. Si les tests de charge k6 montrent que Node coûte trop cher, ce module seul sera réécrit en Go.
   - Seuil proposé : plus de 2 fois le nombre de machines d'une version Go équivalente, mesuré sur un prototype.
   - L'ADR-006 réduit fortement ce risque : il propose un temps réel sans connexions permanentes pour la carte.

**Précisions techniques :**
- NestJS 12 est distribué en ESM uniquement : l'API est un paquet ESM.
- Fastify est retenu plutôt qu'Express pour son débit et l'injection de requêtes dans les tests.
- Les tests compilent avec SWC, car l'injection de dépendances de NestJS a besoin des métadonnées de décorateurs.

**Désaccord entre casquettes.** L'ingénieur backend et le SRE préfèrent Go pour le coût par utilisateur. Le product manager préfère TypeScript pour la vitesse de livraison et le recrutement. On tranche pour TypeScript, avec une sortie prévue et mesurable (le module `live`).

## Conséquences

- **Coût** : quelques machines de plus à grande échelle, à chiffrer dans [COUTS.md](../COUTS.md) après les tests k6.
- **Réversibilité** : bonne, module par module. Les contrats OpenAPI et Protocol Buffers sont indépendants du langage.
- **À revoir si** les tests de charge de la phase 1 dépassent le seuil ci-dessus, ou si le recrutement local montre un vivier Go suffisant.

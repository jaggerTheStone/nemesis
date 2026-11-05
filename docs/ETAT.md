# État du projet

Ce fichier permet à une nouvelle session de reprendre le travail sans perte (partie 1.4 du cahier des charges).

**Dernière mise à jour** : 2026-11-04.

## Où en est-on

- **Phase** : 0, Fondations (plan : `docs/PHASE-0.md`, validé le 2026-11-04).
- **Hypothèses** : toutes validées le 2026-11-04 (`docs/HYPOTHESES.md`).
- **Incréments terminés** :
  - I0.1, socle du dépôt et intégration continue ;
  - I0.2, kits de terrain (`docs/TERRAIN/README.md`) ;
  - I0.3, documents fondateurs et ADR, en attente de relecture par le porteur :
    - ARCHITECTURE, DATA, PRIVACY, COUTS, ALGORITHMES ;
    - ADR-001 à ADR-007 au statut « proposé ».
  - I0.4, base de données et environnement local (`data/schema/README.md`) ;
  - I0.5, jeu fictif « Lagune-Fictive » en GTFS et en SQL (`data/fixtures_fictives/README.md`) ;
  - I0.6, contrat OpenAPI et Protobuf, squelette d'API sur la base (`packages/openapi/README.md`, `services/api/README.md`) ;
  - I0.7, pipelines d'import, rapports de validation et d'écarts, tuiles (`data/pipelines/README.md`). La chaîne fictive et l'import du GTFS 2023 sont vérifiés localement ; la chaîne réelle complète tourne en CI (voir « Imports réels » ci-dessous) ;
  - I0.8, spike du moteur d'itinéraires : **ADR-003 accepté, option B** (RAPTOR à fréquences en Rust), mesures à l'appui (`tools/routing-spike/README.md`).
- **Prochain incrément** : I0.9, moteur d'itinéraires en ligne de commande :
  - interface `RoutingEngine` et McRAPTOR ;
  - marche sur le graphe piéton d'OSM ;
  - Monte-Carlo ;
  - options étiquetées ;
  - tests par propriétés.
- **En attente côté porteur** :
  - **la licence du GTFS « Abidjan 2023 » (H-030)** : CC BY-NC 4.0, pas d'usage commercial. Demander l'autorisation à DigitalTransport4Africa (partenariat, 15.6) et faire valider la démarche par un juriste ;
  - la validation des hypothèses H-029 (emprise d'Abidjan) et H-031 (budget du fond de carte), et la relecture de l'ADR-009 (schéma des tuiles) ;
  - la relecture de l'ADR-003 (option B retenue) ; le choix du corridor pilote, dont les couples remplaceront ceux du spike ;
  - une équipe sur place pour lancer les collectes (Q-03) ;
  - les contreparties des participants et des validateurs ;
  - la relecture juridique des consentements ;
  - la validation des hypothèses H-022 à H-028 ;
  - la relecture de l'ADR-008 (versionnement du réseau) ;
  - la relecture des documents d'I0.3, en particulier :
    - ADR-004, hébergement : décision du porteur ;
    - ADR-006 : écart signalé à la partie 9.1 ;
    - le conseil « remonter à la gare », corrigé dans ALGORITHMES.md, section 1.7 ;
  - les prix unitaires de [COUTS.md](COUTS.md), surtout ceux des canaux ;
  - les questions au juriste de [PRIVACY.md](PRIVACY.md).

## Ce que contient le dépôt après I0.8

| Composant | Contenu | Tests |
|-----------|---------|-------|
| `services/api` | NestJS 12 (ESM) sur Fastify, branché sur PostgreSQL : santé, villes, recherche de lieux, fiche d'arrêt ; problème RFC 9457, ETag, Brotli | 2 + 20 (base) |
| `packages/openapi` | Contrat OpenAPI 3.1 (26 opérations), types générés, règles du contrat | 15 |
| `services/channels` | Outils GSM 7 bits pour le SMS : détection, translittération, comptage des segments | 9 |
| `apps/web-lite` | Rendu HTML échappé, budget de 100 Ko vérifié | 4 |
| `apps/admin` | React et Vite, textes en clés de traduction | 1 |
| `packages/proto` | `EstimateMeta` et `nemesis.live.v1` (deltas par tuile), contrôlés par buf (lint, format, compatibilité) | lint |
| `services/routing` | Espace Cargo : `routing-core` (GTFS, réseau à fréquences, points de montée virtuels, modèles d'attente, RAPTOR) et le binaire `routing` (`spike`) ; le cœur compile pour Android arm64 | 19 |
| `tools/routing-spike` | Spike I0.8 : couples origine-destination, OpenTripPlanner 2.10, comparaison avec une fonction de coût commune ; `make routing-spike` et workflow dédié | vérification croisée |
| `services/ml` | FastAPI, `GET /health` | 1 |
| `data/pipelines` | Données de terrain (`nemesis-terrain`) ; jeu fictif (`nemesis-fixtures` : GTFS, extension, jeu SQL, OSM fictif) ; imports (`nemesis-data` : manifeste des sources, téléchargements vérifiés, GTFS et OSM en staging, validateur, lieux, rapport d'écarts, tuiles) | 3 + 47 + 11 + 37, et 6 contre une base |
| `data/schema` | Huit migrations dbmate (partitions, rôles, audit chaîné, versions du réseau, imports et garde de licence), jeu de départ fictif ; `make db-test` | 25 |
| `tools/simulator` | Générateur aléatoire à graine fixe | 2 |
| `apps/mobile` | Flutter 3.47.7, `minSdk 26`, traductions ARB | 1 |

Commandes : `make dev` (environnement Docker Compose), `make db-test`, `make api-test` et `make pipelines-test` (tests contre une base jetable, Docker requis), `make data-import` et `make data-import-fictif` (chaînes d'import), `make check` (tout, hors réseau, y compris `check-terrain` et `check-docs`), `make audit` (audits de dépendances), `make fmt`, `make fiches-pdf` (régénère les PDF des fiches, Playwright requis).

## Versions figées

Node 22.23.4 (`.nvmrc`), pnpm 10.28.0, TypeScript 6.0 (typescript-eslint ne prend pas encore en charge TypeScript 7), Rust 1.97.0 (`rust-toolchain.toml`), Python 3.13 (`.python-version`), uv 0.11.32, Flutter 3.47.7, cargo-deny 0.20.2, pip-audit 2.10.1, Trivy 0.75.0.

Garde-fous de la chaîne d'approvisionnement : pnpm refuse les versions publiées depuis moins de 14 jours ; uv ignore les versions publiées après le 2026-10-21 (`exclude-newer`, à avancer lors des mises à jour du verrou).

## Imports réels (I0.7)

Le workflow « Imports de données réelles (hebdomadaire) » produit, en artefacts, les rapports de la chaîne réelle : validation du GTFS 2023, écarts GTFS ↔ OSM, tailles des tuiles, volumes. Il se déclenche aussi quand le manifeste, le style OSM, le rapport ou le schéma de tuiles changent.

Première exécution le 2026-11-04, verte, en moins de 3 minutes. Chiffres détaillés dans [DATA.md](DATA.md), section « Volumes importés ».

| Étape | Résultat |
|-------|----------|
| Extrait OSM | 85,6 Mo, MD5 de Geofabrik vérifiée ; 217 443 voies, 61 855 points d'intérêt, 8 266 arrêts, 1 257 lignes en staging |
| Validation du GTFS 2023 | 0 erreur, 245 avertissements, 974 informations |
| Lieux d'Abidjan | 33 284 lieux et 34 455 alias promus |
| Écarts | 4 815 arrêts sur 4 834 retrouvés dans OSM, 974 tracés sur 974 ; 71 tracés différents ; 2 004 arrêts et 282 lignes d'OSM absents du GTFS |
| Tuiles | 57,6 Mo pour le pays ; **4,5 Mo pour Abidjan**, dans le budget de 45 Mo |

Les rapports complets (`rapports-reels`) et les tuiles d'Abidjan (`tuiles-abidjan`) sont conservés en artefacts ; ils sont aussi écrits dans le journal du workflow, l'hôte des artefacts étant bloqué dans l'environnement cloud.

## Points d'attention pour la reprise

- **Environnement cloud** (H-021) :
  - bloqués : `download.geofabrik.de` (et les autres sources d'extraits OSM), `hub.tumidata.org`, `transit.land`, `dl.google.com` et `github.com` hors de ce dépôt ;
  - accessibles : `gitlab.com`, d'où vient le GTFS 2023, et `raw.githubusercontent.com` ;
  - conséquence : l'import OSM réel, les tuiles réelles et le build Android (I0.11) ne sont vérifiables qu'en GitHub Actions ;
  - Flutter s'installe depuis `storage.googleapis.com`, qui reste accessible.
- **osm2pgsql en local** : `apt-get install osm2pgsql` donne la version 1.11.0 d'Ubuntu 24.04, la même qu'en CI. Les workflows épinglent les paquets (`osm2pgsql=1.11.0+ds-1`, `osmium-tool=1.16.0-1build1`) : une mise à jour de sécurité d'Ubuntu fera échouer l'installation, et il faudra alors mettre la version à jour.
- **Chaîne fictive en local, sans GHCR** : `make data-import-fictif DATA_OPTIONS="--sans-validation --sans-tuiles"`.
- **Licence du GTFS 2023** : `usage = "evaluation"` dans `sources.toml`. C'est ce réglage qui fait refuser par la base toute entrée de ce GTFS dans le réseau : ne jamais le passer en `produit` sans l'autorisation écrite demandée en H-030.
- **Spike du moteur** : le workflow « Spike du moteur d'itinéraires (ADR-003) » tourne à chaque modification du moteur. Il prend environ 8 min, dont 7 pour les 375 requêtes d'OpenTripPlanner. `compare.py` échoue si un trajet de B ne suit pas la fonction de coût commune : c'est ainsi qu'un défaut de reconstruction a été trouvé.
- **Python des runners** : 3.12 ; l'environnement cloud a 3.11, 3.12 et 3.13 (`/usr/bin/python3.12` pour reproduire).
- **Fond léger sans océan** (ADR-009) : à reprendre avec le style de carte. La plus grosse tuile d'Abidjan pèse 104 Ko compressée (zoom 12, voirie) : à surveiller pour la data consommée par la carte en 3G.
- **Version du validateur** : l'image `gtfs-validator:8.0.1` se déclare « 8.0.1-SNAPSHOT » dans ses rapports. À vérifier lors de sa prochaine mise à jour.
- **Lieux promus** : la chaîne réelle crée la ville réelle « abidjan » et ses lieux dans la base où elle tourne (celle de `make dev` par défaut). La recherche de l'API les sert alors, avec la source `osm_cote_divoire`.
- **File d'attente de GitHub Actions** : le 2026-11-04, les workflows d'I0.6 ont attendu un runner pendant plus de 10 minutes, puis sont passés au vert. Une attente n'est pas un échec.
- **Docker dans l'environnement cloud** :
  - le démon n'est pas lancé au démarrage : `nohup dockerd > /tmp/dockerd.log 2>&1 &` suffit ;
  - Docker Hub est accessible, mais limite le nombre de requêtes anonymes ;
  - le stockage des images de GitHub (GHCR) est bloqué : l'image dbmate est prise sur Docker Hub, avec la même empreinte.
- **Images épinglées par empreinte** dans `docker-compose.yml` (PostGIS 16-3.5, Valkey 9.1.1, NATS 2.15.0, Caddy 2.10.2, dbmate 2.36.0). Le workflow « Base de données » vérifie que l'image PostGIS de la CI est la même.
- **Maintenance de la base** : `ops.maintain_partitions()` et `ops.purge_expired()` ne sont pas encore planifiées. En développement, elles tournent au démarrage ; leur planification quotidienne relève de la phase 1.
- **Validateur GTFS** : MobilityData 8.0.1, épinglé par empreinte depuis GHCR et déclaré dans `data/pipelines/sources.toml` (un test vérifie que `ci-gtfs.yml` utilise la même image). Il ne tourne qu'en CI, parce que GHCR est bloqué dans l'environnement cloud. Planetiler 0.10.2 (publié le 29 mars 2026) est dans le même cas. Sa date de publication n'a pas pu être vérifiée depuis l'environnement ; c'est une version corrective de la 8.0.0.
- **Jeu fictif** : une base de développement créée avant I0.5 doit être recréée (`make dev-reset`, puis `make dev`).
- **Démarrage de l'environnement** : `make dev` démarre d'abord les services permanents, puis lance la migration en avant-plan (`docker compose run --rm migrate`). En effet, `docker compose up --wait` échoue de façon aléatoire quand le conteneur de migration se termine pendant l'attente. `docker compose up` seul reste utilisable de façon interactive.
- **Contrat d'API** : après toute modification d'`openapi.yaml`, lancer `pnpm --filter @nemesis/openapi run types`. Les scripts racine `typecheck` et `test` construisent d'abord `@nemesis/openapi`, dont l'API importe la version compilée.
- **Compatibilité Protobuf** : `make proto-breaking` compare avec `main` quand `main` contient `packages/proto`. Jusqu'à la première fusion, le contrôle est ignoré, en le signalant.
- **API dans Docker Compose** : pas encore de service `api` ; l'API se lance avec pnpm contre la base de `make dev`.
- **Valkey** remplace Redis pour une raison de licence (ADR-005, mise à jour) : dans la documentation, « Redis » désigne ce stockage compatible.
- **NestJS 12** est distribué en ESM uniquement : l'API est un paquet ESM, avec des imports relatifs en `.js`. Point à reprendre dans l'ADR-002, avec le choix de Fastify.
- **Starlette** déprécie `httpx` pour son client de test : on utilise `httpx2`.
- **Audit** : `pnpm audit` signale une vulnérabilité modérée dans `minimatch`, tirée par ESLint, en développement seulement. Le seuil bloquant est « élevée » ; à corriger dès qu'ESLint publie une version corrigée.
- **CI** : les 5 workflows sont verts sur le commit d'I0.1. GitHub avertit que `actions/checkout@v4`, `actions/setup-node@v4` et `actions/cache@v4` ciblent Node 20, déprécié et exécuté de force sous Node 24. Passer à leurs versions majeures suivantes lors d'un prochain incrément, après avoir vérifié qu'elles existent.
- **Licences** : la politique « dépendances permissives » n'est vérifiée automatiquement que pour Rust (cargo-deny). La vérification pour JavaScript, Python et Dart reste à ajouter.
- **Fiches papier** : les fichiers HTML de `docs/TERRAIN/fiches/` en sont la source. Après toute modification, lancer `make fiches-pdf` ; sinon, un test échoue. La CI n'a pas Chromium et ne régénère pas les PDF.
- **Schémas de terrain** : après toute modification, lancer `uv run nemesis-terrain generer` pour régénérer les modèles et le dictionnaire.
- Aucune donnée personnelle réelle ne doit être collectée avant la déclaration ARTCI ou un avis juridique (H-020).

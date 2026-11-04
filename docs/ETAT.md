# État du projet

Ce fichier permet à une nouvelle session de reprendre le travail sans perte (partie 1.4 du cahier des charges).

**Dernière mise à jour** : 2026-11-04.

## Où en est-on

- **Phase** : 0, Fondations (plan : `docs/PHASE-0.md`, validé le 2026-11-04).
- **Hypothèses** : toutes validées le 2026-11-04 (`docs/HYPOTHESES.md`).
- **Incréments terminés** :
  - I0.1, socle du dépôt et intégration continue ;
  - I0.2, kits de terrain (`docs/TERRAIN/README.md`).
- **Prochain incrément** : I0.3, documents fondateurs et ADR (ARCHITECTURE, DATA, PRIVACY, COUTS, ALGORITHMES, ADR-001 à 007).
- **En attente côté porteur** :
  - une équipe sur place pour lancer les collectes (Q-03) ;
  - les contreparties des participants et des validateurs ;
  - la relecture juridique des consentements ;
  - la validation des hypothèses H-022 à H-026.

## Ce que contient le dépôt après I0.2

| Composant | Contenu | Tests |
|-----------|---------|-------|
| `services/api` | NestJS 12 (ESM) sur Fastify, `GET /v1/health` | 2 |
| `services/channels` | Outils GSM 7 bits pour le SMS : détection, translittération, comptage des segments | 9 |
| `apps/web-lite` | Rendu HTML échappé, budget de 100 Ko vérifié | 4 |
| `apps/admin` | React et Vite, textes en clés de traduction | 1 |
| `packages/proto` | `EstimateMeta` (fraîcheur, confiance, source), contrôlé par buf | lint |
| `services/routing` | Espace Cargo : `routing-core` et le binaire `routing` | 4 |
| `services/ml` | FastAPI, `GET /health` | 1 |
| `data/pipelines` | Vérification d'empreinte SHA-256 ; données de terrain (`nemesis-terrain` : schémas, validateur, modèles et dictionnaire générés, rapport d'icônes) | 3 + 47 |
| `tools/simulator` | Générateur aléatoire à graine fixe | 2 |
| `apps/mobile` | Flutter 3.47.7, `minSdk 26`, traductions ARB | 1 |

Commandes : `make check` (tout, hors réseau, y compris `check-terrain`), `make audit` (audits de dépendances), `make fmt`, `make fiches-pdf` (régénère les PDF des fiches, Playwright requis).

## Versions figées

Node 22.23.4 (`.nvmrc`), pnpm 10.28.0, TypeScript 6.0 (typescript-eslint ne prend pas encore en charge TypeScript 7), Rust 1.97.0 (`rust-toolchain.toml`), Python 3.13 (`.python-version`), uv 0.11.32, Flutter 3.47.7, cargo-deny 0.20.2, pip-audit 2.10.1, Trivy 0.75.0.

Garde-fous de la chaîne d'approvisionnement : pnpm refuse les versions publiées depuis moins de 14 jours ; uv ignore les versions publiées après le 2026-10-21 (`exclude-newer`, à avancer lors des mises à jour du verrou).

## Points d'attention pour la reprise

- **Environnement cloud** (H-021) : `download.geofabrik.de`, `hub.tumidata.org`, `transit.land`, `dl.google.com` et `github.com` hors de ce dépôt sont bloqués. Les imports (I0.7) et le build Android (I0.11) ne sont vérifiables qu'en GitHub Actions. Flutter s'installe depuis `storage.googleapis.com`, qui reste accessible.
- **Docker** est installé, mais son démon n'est pas lancé dans l'environnement cloud ; à démarrer pour vérifier `docker compose up` en I0.4.
- **NestJS 12** est distribué en ESM uniquement : l'API est un paquet ESM, avec des imports relatifs en `.js`. Point à reprendre dans l'ADR-002, avec le choix de Fastify.
- **Starlette** déprécie `httpx` pour son client de test : on utilise `httpx2`.
- **Audit** : `pnpm audit` signale une vulnérabilité modérée dans `minimatch`, tirée par ESLint, en développement seulement. Le seuil bloquant est « élevée » ; à corriger dès qu'ESLint publie une version corrigée.
- **CI** : les 5 workflows sont verts sur le commit d'I0.1. GitHub avertit que `actions/checkout@v4`, `actions/setup-node@v4` et `actions/cache@v4` ciblent Node 20, déprécié et exécuté de force sous Node 24. Passer à leurs versions majeures suivantes lors d'un prochain incrément, après avoir vérifié qu'elles existent.
- **Licences** : la politique « dépendances permissives » n'est vérifiée automatiquement que pour Rust (cargo-deny). La vérification pour JavaScript, Python et Dart reste à ajouter.
- **Fiches papier** : les fichiers HTML de `docs/TERRAIN/fiches/` en sont la source. Après toute modification, lancer `make fiches-pdf` ; sinon, un test échoue. La CI n'a pas Chromium et ne régénère pas les PDF.
- **Schémas de terrain** : après toute modification, lancer `uv run nemesis-terrain generer` pour régénérer les modèles et le dictionnaire.
- Aucune donnée personnelle réelle ne doit être collectée avant la déclaration ARTCI ou un avis juridique (H-020).

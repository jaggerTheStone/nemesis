# État du projet

Ce fichier permet à une nouvelle session de reprendre le travail sans perte (partie 1.4 du cahier des charges).

**Dernière mise à jour** : 2026-11-04.

## Où en est-on

- **Phase** : 0, Fondations (plan : `docs/PHASE-0.md`, validé le 2026-11-04).
- **Hypothèses** : toutes validées le 2026-11-04 (`docs/HYPOTHESES.md`).
- **Incrément terminé** : I0.1, socle du dépôt et intégration continue.
- **Prochain incrément** : I0.2, kits de terrain prioritaires (gabarits des 300 requêtes et des 200 trajets, protocole de test des maquettes).

## Ce que contient le dépôt après I0.1

| Composant | Contenu | Tests |
|-----------|---------|-------|
| `services/api` | NestJS 12 (ESM) sur Fastify, `GET /v1/health` | 2 |
| `services/channels` | Outils GSM 7 bits pour le SMS : détection, translittération, comptage des segments | 9 |
| `apps/web-lite` | Rendu HTML échappé, budget de 100 Ko vérifié | 4 |
| `apps/admin` | React et Vite, textes en clés de traduction | 1 |
| `packages/proto` | `EstimateMeta` (fraîcheur, confiance, source), contrôlé par buf | lint |
| `services/routing` | Espace Cargo : `routing-core` et le binaire `routing` | 4 |
| `services/ml` | FastAPI, `GET /health` | 1 |
| `data/pipelines` | Vérification d'empreinte SHA-256 | 3 |
| `tools/simulator` | Générateur aléatoire à graine fixe | 2 |
| `apps/mobile` | Flutter 3.47.7, `minSdk 26`, traductions ARB | 1 |

Commandes : `make check` (tout, hors réseau), `make audit` (audits de dépendances), `make fmt`.

## Versions figées

Node 22.23.4 (`.nvmrc`), pnpm 10.28.0, TypeScript 6.0 (typescript-eslint ne prend pas encore en charge TypeScript 7), Rust 1.97.0 (`rust-toolchain.toml`), Python 3.13 (`.python-version`), uv 0.11.32, Flutter 3.47.7, cargo-deny 0.20.2, pip-audit 2.10.1, Trivy 0.75.0.

Garde-fous de la chaîne d'approvisionnement : pnpm refuse les versions publiées depuis moins de 14 jours ; uv ignore les versions publiées après le 2026-10-21 (`exclude-newer`, à avancer lors des mises à jour du verrou).

## Points d'attention pour la reprise

- **Environnement cloud** (H-021) : `download.geofabrik.de`, `hub.tumidata.org`, `transit.land`, `dl.google.com` et `github.com` hors de ce dépôt sont bloqués. Les imports (I0.7) et le build Android (I0.11) ne sont vérifiables qu'en GitHub Actions. Flutter s'installe depuis `storage.googleapis.com`, qui reste accessible.
- **Docker** est installé, mais son démon n'est pas lancé dans l'environnement cloud ; à démarrer pour vérifier `docker compose up` en I0.4.
- **NestJS 12** est distribué en ESM uniquement : l'API est un paquet ESM, avec des imports relatifs en `.js`. Point à reprendre dans l'ADR-002, avec le choix de Fastify.
- **Starlette** déprécie `httpx` pour son client de test : on utilise `httpx2`.
- **Audit** : `pnpm audit` signale une vulnérabilité modérée dans `minimatch`, tirée par ESLint, en développement seulement. Le seuil bloquant est « élevée » ; à corriger dès qu'ESLint publie une version corrigée.
- **Licences** : la politique « dépendances permissives » n'est vérifiée automatiquement que pour Rust (cargo-deny). La vérification pour JavaScript, Python et Dart reste à ajouter.
- Aucune donnée personnelle réelle ne doit être collectée avant la déclaration ARTCI ou un avis juridique (H-020).

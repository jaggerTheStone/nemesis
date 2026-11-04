# nemesis

Nom de code d'une solution d'abord mobile qui réduit le temps que les usagers du transport en commun perdent à attendre et à chercher un véhicule en Côte d'Ivoire, en commençant par le Grand Abidjan. Le nom public reste à choisir.

**État** : phase 0 (fondations) en cours ; voir [docs/ETAT.md](docs/ETAT.md).

## Démarrer

Prérequis : Node 22 et pnpm 10, Rust (installé automatiquement selon `rust-toolchain.toml`), uv, Flutter 3.47.

```bash
make install   # dépendances de tous les écosystèmes
make check     # lint, typage et tests de tous les composants
make audit     # audits de dépendances (réseau requis)
```

Environnement local, avec Docker :

```bash
make dev       # PostgreSQL et PostGIS, Valkey, NATS, tuiles ; base migrée et jeu fictif
make db-test   # tests du schéma contre une base jetable
make api-test  # tests de contrat de l'API contre une base jetable
make dev-down  # arrêt (make dev-reset efface aussi les données)
```

Imports de données ([data/pipelines/README.md](data/pipelines/README.md)), avec osm2pgsql 1.11 et Docker :

```bash
make data-import-fictif  # chaîne complète sur les données fictives du dépôt
make data-import         # OSM Côte d'Ivoire et GTFS « Abidjan 2023 » (réseau requis)
make pipelines-test      # tests des pipelines contre une base jetable
```

`docker compose up` seul fonctionne aussi. Les ports ne sont exposés que sur 127.0.0.1, et les variables sont décrites dans `.env.example`.

## Organisation du dépôt

| Dossier | Rôle |
|---------|------|
| `apps/mobile` | Appli Flutter (usagers, puis mode Pro) |
| `apps/admin` | Back-office web |
| `apps/web-lite` | Pages légères partageables |
| `services/api` | API principale (NestJS) |
| `services/routing` | Moteur d'itinéraires (Rust) |
| `services/ml` | Modèles d'attente, de prix, de détection (Python) |
| `services/channels` | WhatsApp, SMS, USSD, serveur vocal |
| `packages/openapi` | Contrat OpenAPI 3.1 de l'API, types générés, règles du contrat |
| `packages/proto` | Schémas Protocol Buffers partagés |
| `data/pipelines` | Imports OSM et GTFS, tuiles, packs hors ligne |
| `data/schema` | Schéma de la base : migrations dbmate et tests |
| `data/fixtures_fictives` | Jeux de test fictifs |
| `data/terrain` | Modèles de saisie et données collectées sur le terrain |
| `tools/simulator` | Simulateur par agents |
| `tools/terrain` | Rendu des fiches de terrain en PDF |
| `infra` | Docker, puis Terraform et Ansible |
| `docs` | Documentation vivante et ADR |

## Documents

- [Cahier des charges](docs/CAHIER_DES_CHARGES.md) : la référence du projet.
- [Plan de la phase 0](docs/PHASE-0.md).
- [Architecture](docs/ARCHITECTURE.md), [données](docs/DATA.md), [algorithmes](docs/ALGORITHMES.md).
- [Vie privée](docs/PRIVACY.md) et [coûts](docs/COUTS.md).
- [Hypothèses](docs/HYPOTHESES.md).
- [Kits de terrain](docs/TERRAIN/README.md) : protocoles, fiches à imprimer, dictionnaire des données.
- [Décisions d'architecture](docs/DECISIONS/README.md).
- [État du projet](docs/ETAT.md).
- [Journal des modifications](CHANGELOG.md) et [sécurité](SECURITY.md).

Code et documentation : licence propriétaire, voir [LICENSE](LICENSE).

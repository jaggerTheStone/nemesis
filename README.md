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

L'environnement local complet (`docker compose up`) arrive avec l'incrément I0.4.

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
| `packages/proto` | Schémas Protocol Buffers partagés |
| `data/pipelines` | Imports OSM et GTFS, tuiles, packs hors ligne |
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

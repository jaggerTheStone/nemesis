# Point d'entrée unique des contrôles du monorepo.
#   make check   lint, typage et tests de tous les composants (hors réseau)
#   make audit   audits de dépendances (réseau requis)
#   make fmt     formatage automatique
#   make fiches-pdf  PDF des fiches de terrain (Playwright requis)
# Chaque écosystème a aussi sa cible : check-ts, check-rust, check-py, check-terrain, check-fixtures, check-docs, check-mobile.
#   make dev     environnement local (docker compose) : base migrée et jeu fictif
#   make db-test tests du schéma contre une base PostGIS jetable
#   make api-test tests de contrat de l'API contre une base PostGIS jetable
#   make data-import         imports réels : OSM, GTFS 2023, rapports et tuiles (réseau requis)
#   make data-import-fictif  la même chaîne sur les données fictives du dépôt
#   make pipelines-test      tests des pipelines contre une base PostGIS jetable (osm2pgsql requis)
#   make routing-spike       spike du moteur d'itinéraires, options A et B (réseau et Docker requis)
#   make simulation          journée simulée du corridor fictif et formules d'attente confrontées (I0.10)

ROUTING := services/routing
MOBILE := apps/mobile
# Image PostGIS lue dans docker-compose.yml : une seule source de vérité.
POSTGIS_IMAGE := $(shell awk '/image: postgis\//{print $$2; exit}' docker-compose.yml)
DB_TEST_PORT ?= 55432
API_TEST_PORT ?= 55433
PIPELINES_TEST_PORT ?= 55434

.PHONY: check check-ts check-proto check-rust check-py check-terrain check-fixtures check-docs check-mobile \
        audit audit-ts audit-rust audit-py fmt install fiches-pdf \
        dev dev-down dev-reset db-migrate db-test gtfs-validate api-test proto-breaking \
        data-import data-import-fictif data-tiles-verify pipelines-test routing-spike simulation

check: check-ts check-proto check-rust check-py check-terrain check-fixtures check-docs check-mobile
	@echo "Tous les contrôles sont au vert."

install:
	pnpm install --frozen-lockfile
	uv sync --locked --all-packages
	cd $(MOBILE) && flutter pub get

check-ts:
	pnpm install --frozen-lockfile
	pnpm run lint
	pnpm run openapi:lint
	pnpm run typecheck
	pnpm run test
	pnpm run build

check-proto:
	pnpm run proto:lint

# Compatibilité du contrat Protobuf avec main (ignorée tant que main n'en a pas).
proto-breaking:
	@if git cat-file -e origin/main:packages/proto/buf.yaml 2>/dev/null; then \
		pnpm exec buf breaking packages/proto --against '.git#ref=origin/main,subdir=packages/proto'; \
	else \
		echo "Pas de contrat Protobuf sur main : contrôle de compatibilité ignoré."; \
	fi

check-rust:
	cd $(ROUTING) && cargo fmt --check
	cd $(ROUTING) && cargo clippy --all-targets --locked -- -D warnings
	cd $(ROUTING) && cargo test --locked

check-py:
	uv sync --locked --all-packages
	uv run ruff check .
	uv run ruff format --check .
	uv run pytest

# Données de terrain (I0.2) : fichiers générés à jour, exemples fictifs et collecte réelle valides.
check-terrain:
	uv run nemesis-terrain generer --verifier
	uv run nemesis-terrain valider --fictif data/fixtures_fictives/terrain
	uv run nemesis-terrain accord --fictif --strict data/fixtures_fictives/terrain/eclaireurs > /dev/null
	uv run nemesis-terrain valider data/terrain/collecte

# Jeu fictif Lagune-Fictive (I0.5) : GTFS et jeu SQL à jour par rapport au générateur.
check-fixtures:
	uv run nemesis-fixtures generer --verifier

# Validateur canonique de MobilityData sur le GTFS fictif (image GHCR, Docker requis).
# Image déclarée dans data/pipelines/sources.toml ; un test vérifie que la CI utilise la même.
GTFS_VALIDATOR_IMAGE := $(shell awk -F'"' '/^gtfs_validator = /{print $$2; exit}' data/pipelines/sources.toml)
gtfs-validate:
	rm -rf data/work/gtfs && mkdir -p data/work/gtfs
	cd data/fixtures_fictives/gtfs && zip -q -X ../../work/gtfs/lagune-fictive.zip ./*.txt
	docker run --rm -v "$(CURDIR)/data/work/gtfs:/work" $(GTFS_VALIDATOR_IMAGE) -i /work/lagune-fictive.zip -o /work/rapport
	uv run nemesis-fixtures verifier-rapport data/work/gtfs/rapport/report.json

# Liens relatifs de toute la documentation Markdown.
check-docs:
	python3 tools/docs/check_links.py

# Régénère les PDF des fiches (Playwright et Chromium requis, hors CI).
fiches-pdf:
	node tools/terrain/fiches-pdf.cjs

check-mobile:
	cd $(MOBILE) && flutter pub get
	cd $(MOBILE) && flutter gen-l10n
	cd $(MOBILE) && dart format --output=none --set-exit-if-changed lib test
	cd $(MOBILE) && flutter analyze
	cd $(MOBILE) && flutter test

audit: audit-ts audit-rust audit-py

audit-ts:
	pnpm audit --audit-level high

audit-rust:
	cd $(ROUTING) && cargo deny check

audit-py:
	uv export --frozen --all-packages --no-emit-workspace --format requirements-txt --quiet \
		| uvx pip-audit@2.10.1 -r /dev/stdin --require-hashes --disable-pip --progress-spinner off

fmt:
	pnpm run format
	cd $(ROUTING) && cargo fmt
	uv run ruff format .
	uv run ruff check --fix .
	cd $(MOBILE) && dart format lib test

# Environnement local : PostgreSQL et PostGIS, Valkey, NATS, serveur de tuiles.
# Les services permanents d'abord, puis la migration en avant-plan : « up --wait »
# échouerait si le conteneur de migration se terminait pendant l'attente.
DEV_SERVICES := db valkey nats tiles
dev:
	docker compose up -d --wait $(DEV_SERVICES)
	docker compose run --rm migrate
	@echo "Environnement prêt : base sur 127.0.0.1:5432, tuiles sur http://127.0.0.1:8080"

dev-down:
	docker compose down

# Supprime aussi les volumes : la base repart de zéro.
dev-reset:
	docker compose down -v

db-migrate:
	docker compose run --rm migrate

db-test:
	@docker rm -f nemesis-db-test >/dev/null 2>&1 || true
	docker run -d --name nemesis-db-test -e POSTGRES_PASSWORD=test \
		-p 127.0.0.1:$(DB_TEST_PORT):5432 $(POSTGIS_IMAGE) >/dev/null
	@until docker exec nemesis-db-test pg_isready -h 127.0.0.1 -U postgres -q; do sleep 1; done
	NEMESIS_TEST_DATABASE_URL=postgres://postgres:test@127.0.0.1:$(DB_TEST_PORT)/postgres \
		NEMESIS_REQUIRE_DB=1 uv run pytest data/schema -rs; \
		status=$$?; docker rm -f nemesis-db-test >/dev/null; exit $$status

# Tests de contrat de l'API contre une base PostGIS jetable (Docker requis).
api-test:
	@docker rm -f nemesis-api-test >/dev/null 2>&1 || true
	docker run -d --name nemesis-api-test -e POSTGRES_PASSWORD=test \
		-p 127.0.0.1:$(API_TEST_PORT):5432 $(POSTGIS_IMAGE) >/dev/null
	@until docker exec nemesis-api-test pg_isready -h 127.0.0.1 -U postgres -q; do sleep 1; done
	pnpm --filter @nemesis/openapi run build
	NEMESIS_TEST_DATABASE_URL=postgres://postgres:test@127.0.0.1:$(API_TEST_PORT)/postgres \
		NEMESIS_REQUIRE_DB=1 pnpm --filter @nemesis/api test; \
		status=$$?; docker rm -f nemesis-api-test >/dev/null; exit $$status

# Imports de données (I0.7), contre la base de make dev par défaut. Il faut osm2pgsql 1.11,
# Docker (validateur GTFS et Planetiler) et, pour le jeu fictif, osmium-tool.
# DATA_OPTIONS="--sans-validation --sans-tuiles" quand les images GHCR sont inaccessibles.
DATABASE_URL ?= postgres://nemesis_admin:$(or $(NEMESIS_DB_PASSWORD),nemesis_dev)@127.0.0.1:$(or $(NEMESIS_DB_PORT),5432)/nemesis
DATA_OPTIONS ?=
data-import:
	DATABASE_URL=$(DATABASE_URL) uv run nemesis-data chaine reel $(DATA_OPTIONS)

data-import-fictif:
	DATABASE_URL=$(DATABASE_URL) uv run nemesis-data chaine fictif $(DATA_OPTIONS)

# Exemples du schéma de tuiles (planetiler verify).
data-tiles-verify:
	uv run nemesis-data verifier-schema-tuiles

pipelines-test:
	@docker rm -f nemesis-pipelines-test >/dev/null 2>&1 || true
	docker run -d --name nemesis-pipelines-test -e POSTGRES_PASSWORD=test \
		-p 127.0.0.1:$(PIPELINES_TEST_PORT):5432 $(POSTGIS_IMAGE) >/dev/null
	@until docker exec nemesis-pipelines-test pg_isready -h 127.0.0.1 -U postgres -q; do sleep 1; done
	NEMESIS_TEST_DATABASE_URL=postgres://postgres:test@127.0.0.1:$(PIPELINES_TEST_PORT)/postgres \
		NEMESIS_REQUIRE_DB=1 NEMESIS_REQUIRE_OSM2PGSQL=1 uv run pytest data/pipelines -rs; \
		status=$$?; docker rm -f nemesis-pipelines-test >/dev/null; exit $$status

# Spike du moteur d'itinéraires (I0.8, ADR-003) : OpenTripPlanner et RAPTOR à fréquences sur
# les mêmes couples. Il faut osmium-tool, Docker et l'accès à Geofabrik (sinon : CI).
SPIKE_OSM ?= data/work/sources/osm_cote_divoire/ivory-coast-latest.osm.pbf
SPIKE_GTFS ?= data/work/sources/gtfs_abidjan_2023/Abidjan_Paratransit_GTFS_20230726.zip
routing-spike:
	uv run nemesis-data telecharger osm_cote_divoire gtfs_abidjan_2023
	tools/routing-spike/run.sh $(SPIKE_OSM) $(SPIKE_GTFS) data/work/spike

# Simulateur par agents (I0.10) : une journée de pointe du corridor fictif G1, signalements
# au format de l'API et vérité terrain, puis les formules d'attente contre la simulation.
SIM_SEED ?= 42
simulation:
	uv run nemesis-simulator simuler --graine $(SIM_SEED) --sortie data/work/simulation
	uv run nemesis-simulator evaluer --graines 0-4 --sortie data/work/simulation

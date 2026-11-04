# Point d'entrée unique des contrôles du monorepo.
#   make check   lint, typage et tests de tous les composants (hors réseau)
#   make audit   audits de dépendances (réseau requis)
#   make fmt     formatage automatique
#   make fiches-pdf  PDF des fiches de terrain (Playwright requis)
# Chaque écosystème a aussi sa cible : check-ts, check-rust, check-py, check-terrain, check-docs, check-mobile.
#   make dev     environnement local (docker compose) : base migrée et jeu fictif
#   make db-test tests du schéma contre une base PostGIS jetable

ROUTING := services/routing
MOBILE := apps/mobile
# Image PostGIS lue dans docker-compose.yml : une seule source de vérité.
POSTGIS_IMAGE := $(shell awk '/image: postgis\//{print $$2; exit}' docker-compose.yml)
DB_TEST_PORT ?= 55432

.PHONY: check check-ts check-proto check-rust check-py check-terrain check-docs check-mobile \
        audit audit-ts audit-rust audit-py fmt install fiches-pdf \
        dev dev-down dev-reset db-migrate db-test

check: check-ts check-proto check-rust check-py check-terrain check-docs check-mobile
	@echo "Tous les contrôles sont au vert."

install:
	pnpm install --frozen-lockfile
	uv sync --locked --all-packages
	cd $(MOBILE) && flutter pub get

check-ts:
	pnpm install --frozen-lockfile
	pnpm run lint
	pnpm run typecheck
	pnpm run test
	pnpm run build

check-proto:
	pnpm run proto:lint

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
	uv run nemesis-terrain valider data/terrain/collecte

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
dev:
	docker compose up -d --wait
	docker compose wait migrate
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

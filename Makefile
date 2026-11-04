# Point d'entrée unique des contrôles du monorepo.
#   make check   lint, typage et tests de tous les composants (hors réseau)
#   make audit   audits de dépendances (réseau requis)
#   make fmt     formatage automatique
# Chaque écosystème a aussi sa cible : check-ts, check-rust, check-py, check-mobile.
# `make dev` arrive avec Docker Compose en I0.4.

ROUTING := services/routing
MOBILE := apps/mobile

.PHONY: check check-ts check-proto check-rust check-py check-mobile \
        audit audit-ts audit-rust audit-py fmt install

check: check-ts check-proto check-rust check-py check-mobile
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

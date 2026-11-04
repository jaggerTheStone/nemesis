"""Reads and applies dbmate migration files (data/schema/migrations).

dbmate is the reference tool (docker-compose.yml, `make db-migrate`). This module
applies the same `-- migrate:up` / `-- migrate:down` sections for the test suite,
each migration in its own transaction, like dbmate does by default.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "migrations"
_SECTION = re.compile(r"^-- migrate:(up|down)\b.*$", re.MULTILINE)
_NAME = re.compile(r"^[0-9]{14}_[a-z0-9_]+\.sql$")


@dataclass(frozen=True)
class Migration:
    version: str
    name: str
    up: str
    down: str


def parse_migration(path: Path) -> Migration:
    """Splits a dbmate file into its up and down sections."""
    if not _NAME.match(path.name):
        raise ValueError(f"{path.name}: expected AAAAMMJJHHMMSS_nom.sql")
    text = path.read_text(encoding="utf-8")
    markers = list(_SECTION.finditer(text))
    kinds = [marker.group(1) for marker in markers]
    if kinds != ["up", "down"]:
        raise ValueError(f"{path.name}: expected one '-- migrate:up' then one '-- migrate:down'")
    up = text[markers[0].end() : markers[1].start()].strip()
    down = text[markers[1].end() :].strip()
    if not up or not down:
        raise ValueError(f"{path.name}: empty up or down section")
    return Migration(path.name.split("_", 1)[0], path.name, up, down)


def load_migrations(directory: Path = MIGRATIONS_DIR) -> list[Migration]:
    return [parse_migration(path) for path in sorted(directory.glob("*.sql"))]


def apply_migrations(
    connection: Any,
    direction: Literal["up", "down"] = "up",
    directory: Path = MIGRATIONS_DIR,
) -> list[str]:
    """Applies every migration (or rolls them all back), one transaction each."""
    migrations = load_migrations(directory)
    if direction == "down":
        migrations.reverse()
    applied = []
    cursor = connection.cursor()
    for migration in migrations:
        cursor.execute(migration.up if direction == "up" else migration.down)
        connection.commit()
        applied.append(migration.name)
    return applied

"""Fixtures for database tests.

Set NEMESIS_TEST_DATABASE_URL to an administrator URL of a PostgreSQL 16 server
with PostGIS (for example the container started by `make db-test`). Each test
session creates its own throwaway database. Without the variable the tests are
skipped, unless NEMESIS_REQUIRE_DB=1 (CI), in which case they fail.
"""

from __future__ import annotations

import os
import uuid
from collections.abc import Iterator
from typing import Any

import pg8000.dbapi
import pytest

from nemesis_schema.migrations import apply_migrations
from nemesis_schema.testing import Db, connection_parameters

URL_VARIABLE = "NEMESIS_TEST_DATABASE_URL"


@pytest.fixture(scope="session")
def database() -> Iterator[dict[str, Any]]:
    url = os.environ.get(URL_VARIABLE)
    if not url:
        message = f"{URL_VARIABLE} absent : tests de base de données ignorés"
        if os.environ.get("NEMESIS_REQUIRE_DB") == "1":
            pytest.fail(message)
        pytest.skip(message)
    params = connection_parameters(url)
    name = f"nemesis_test_{uuid.uuid4().hex[:12]}"
    admin = pg8000.dbapi.connect(**params)
    admin.autocommit = True
    admin.cursor().execute(f'create database "{name}"')
    try:
        connection = pg8000.dbapi.connect(**{**params, "database": name})
        apply_migrations(connection)
        connection.close()
        yield {**params, "database": name}
    finally:
        admin.cursor().execute(f'drop database "{name}" with (force)')
        admin.close()


@pytest.fixture
def db(database: dict[str, Any]) -> Iterator[Db]:
    connection = pg8000.dbapi.connect(**database)
    try:
        yield Db(connection)
    finally:
        connection.rollback()
        connection.close()

"""Fixtures for database tests.

Set NEMESIS_TEST_DATABASE_URL to an administrator URL of a PostgreSQL 16 server
with PostGIS (for example the container started by `make db-test`). Each test
session creates its own throwaway database. Without the variable the tests are
skipped, unless NEMESIS_REQUIRE_DB=1 (CI), in which case they fail.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from typing import Any

import pg8000.dbapi
import pytest

from nemesis_schema.testing import URL_VARIABLE, Db, server_url, throwaway_database


@pytest.fixture(scope="session")
def database() -> Iterator[dict[str, Any]]:
    url = server_url()
    if not url:
        message = f"{URL_VARIABLE} absent : tests de base de données ignorés"
        if os.environ.get("NEMESIS_REQUIRE_DB") == "1":
            pytest.fail(message)
        pytest.skip(message)
    with throwaway_database(url) as params:
        yield params


@pytest.fixture
def db(database: dict[str, Any]) -> Iterator[Db]:
    connection = pg8000.dbapi.connect(**database)
    try:
        yield Db(connection)
    finally:
        connection.rollback()
        connection.close()

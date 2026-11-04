"""Test helpers for database tests (used by data/schema/tests and later suites)."""

from __future__ import annotations

import os
import urllib.parse
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import pg8000.dbapi

from nemesis_schema.connection import connection_parameters
from nemesis_schema.migrations import apply_migrations

__all__ = [
    "URL_VARIABLE",
    "Db",
    "connection_parameters",
    "database_url",
    "server_url",
    "throwaway_database",
]

URL_VARIABLE = "NEMESIS_TEST_DATABASE_URL"


def server_url() -> str | None:
    """Administrator URL of the test server, or None (tests are then skipped, or fail in CI)."""
    return os.environ.get(URL_VARIABLE) or None


def database_url(params: dict[str, Any]) -> str:
    """postgres:// URL of a connection, for tools such as osm2pgsql."""
    user = urllib.parse.quote(params["user"], safe="")
    password = params.get("password")
    credentials = f"{user}:{urllib.parse.quote(password, safe='')}" if password else user
    return f"postgres://{credentials}@{params['host']}:{params['port']}/{params['database']}"


@contextmanager
def throwaway_database(url: str) -> Iterator[dict[str, Any]]:
    """Creates a migrated database on the server of `url`, then drops it."""
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


class Db:
    """Thin helper over a pg8000 connection; each test runs in one transaction."""

    def __init__(self, connection: pg8000.dbapi.Connection) -> None:
        self.connection = connection
        self.cursor = connection.cursor()

    def _execute(self, sql: str, params: tuple[Any, ...]) -> None:
        if params:
            self.cursor.execute(sql, params)
        else:
            self.cursor.execute(sql)

    def run(self, sql: str, *params: Any) -> list[tuple[Any, ...]]:
        self._execute(sql, params)
        try:
            return [tuple(row) for row in self.cursor.fetchall()]
        except pg8000.dbapi.ProgrammingError:
            return []

    def value(self, sql: str, *params: Any) -> Any:
        rows = self.run(sql, *params)
        assert len(rows) == 1 and len(rows[0]) == 1, rows
        return rows[0][0]

    def error(self, sql: str, *params: Any) -> tuple[str, str]:
        """Runs a statement that must fail; returns (SQLSTATE, message)."""
        self.cursor.execute("savepoint expected_error")
        try:
            self._execute(sql, params)
        except pg8000.dbapi.DatabaseError as error:
            details = error.args[0]
            self.cursor.execute("rollback to savepoint expected_error")
            return details["C"], details["M"]
        self.cursor.execute("release savepoint expected_error")
        raise AssertionError(f"statement succeeded unexpectedly: {sql}")

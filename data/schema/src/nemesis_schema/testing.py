"""Test helpers for database tests (used by data/schema/tests and later suites)."""

from __future__ import annotations

import urllib.parse
from typing import Any

import pg8000.dbapi


def connection_parameters(url: str) -> dict[str, Any]:
    parts = urllib.parse.urlsplit(url)
    return {
        "user": urllib.parse.unquote(parts.username or "postgres"),
        "password": urllib.parse.unquote(parts.password) if parts.password else None,
        "host": parts.hostname or "localhost",
        "port": parts.port or 5432,
        "database": parts.path.lstrip("/") or "postgres",
    }


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

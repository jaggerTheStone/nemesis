"""Connection to PostgreSQL from a URL (postgres://user:password@host:port/database)."""

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


def connect(url: str) -> pg8000.dbapi.Connection:
    return pg8000.dbapi.connect(**connection_parameters(url))

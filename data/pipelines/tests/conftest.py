"""Fixtures of the pipeline tests (I0.7).

Database tests need NEMESIS_TEST_DATABASE_URL (a PostgreSQL 16 + PostGIS server, for
example the one of `make db-test`); each test gets its own migrated database. The OSM
import tests also need osm2pgsql. Without them the tests are skipped, unless
NEMESIS_REQUIRE_DB=1 or NEMESIS_REQUIRE_OSM2PGSQL=1 (CI), in which case they fail.
"""

from __future__ import annotations

import os
import shutil
from collections.abc import Iterator
from pathlib import Path

import pytest

from nemesis_schema.testing import URL_VARIABLE, database_url, server_url, throwaway_database

REPOSITORY = Path(__file__).resolve().parents[3]


def _missing(message: str, variable: str) -> None:
    if os.environ.get(variable) == "1":
        pytest.fail(message)
    pytest.skip(message)


@pytest.fixture
def pg_url() -> Iterator[str]:
    url = server_url()
    if not url:
        _missing(f"{URL_VARIABLE} absent : tests de base de données ignorés", "NEMESIS_REQUIRE_DB")
    assert url is not None
    with throwaway_database(url) as params:
        yield database_url(params)


@pytest.fixture
def osm2pgsql() -> None:
    if shutil.which("osm2pgsql") is None:
        _missing("osm2pgsql absent : tests d'import OSM ignorés", "NEMESIS_REQUIRE_OSM2PGSQL")


@pytest.fixture
def repository() -> Path:
    return REPOSITORY

"""Schema tests (I0.4): constraints, roles, versions, audit chain, partitions."""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pg8000.dbapi
import pytest

from nemesis_schema.migrations import MIGRATIONS_DIR, apply_migrations, load_migrations
from nemesis_schema.testing import Db

SEED = Path(__file__).resolve().parents[2] / "fixtures_fictives" / "db" / "seed.sql"

# Vocabulary and configuration tables: not business data, no is_fictional.
NON_BUSINESS_TABLES = {"network.mode", "network.stop_kind", "ops.partition_policy"}


def make_city(db: Db, code: str, fictional: bool = False) -> str:
    db.run(
        "insert into network.source (id, name, license) values ('test', 'Test', 'test') "
        "on conflict (id) do nothing"
    )
    return db.value(
        "insert into network.city (code, name, metric_srid, is_fictional) "
        "values (%s, %s, 32630, %s) returning id::text",
        code,
        code,
        fictional,
    )


def make_stop(db: Db, city: str, code: str, fictional: bool = False) -> str:
    return db.value(
        "insert into network.stop (city_id, is_fictional, code, kind, name, geom, source_id) "
        "values (%s, %s, %s, 'gare_artisanale', %s, "
        "ST_SetSRID(ST_MakePoint(-4.0, 5.3), 4326), 'test') returning id::text",
        city,
        fictional,
        code,
        code,
    )


def make_route(db: Db, city: str, code: str, fictional: bool = False) -> str:
    return db.value(
        "insert into network.route (city_id, is_fictional, code, mode, spoken_name, source_id) "
        "values (%s, %s, %s, 'gbaka', %s, 'test') returning id::text",
        city,
        fictional,
        code,
        code,
    )


def make_staff(db: Db, role: str = "curateur") -> str:
    return db.value(
        "insert into ops.staff_account (display_name, email, role, mfa_enabled) "
        "values ('Test', %s, %s, true) returning id::text",
        f"{uuid.uuid4().hex}@example.invalid",
        role,
    )


@pytest.fixture
def fresh_database(database: dict[str, Any]) -> Iterator[dict[str, Any]]:
    """An empty database (no migrations) for tests that need their own."""
    name = f"nemesis_test_{uuid.uuid4().hex[:12]}"
    admin = pg8000.dbapi.connect(**{**database, "database": "postgres"})
    admin.autocommit = True
    admin.cursor().execute(f'create database "{name}"')
    try:
        yield {**database, "database": name}
    finally:
        admin.cursor().execute(f'drop database "{name}" with (force)')
        admin.close()


# --- Migrations ---------------------------------------------------------------------------


def test_migration_files_are_well_formed() -> None:
    migrations = load_migrations()
    assert [m.name for m in migrations] == sorted(
        path.name for path in MIGRATIONS_DIR.glob("*.sql")
    )
    assert len({m.version for m in migrations}) == len(migrations)


def test_migrations_round_trip(fresh_database: dict[str, Any]) -> None:
    connection = pg8000.dbapi.connect(**fresh_database)
    cursor = connection.cursor()
    schemas = (
        "select count(*) from information_schema.schemata "
        "where schema_name in ('network', 'mobility', 'identity', 'ops')"
    )
    apply_migrations(connection, "up")
    apply_migrations(connection, "down")
    cursor.execute(schemas)
    assert cursor.fetchone()[0] == 0
    apply_migrations(connection, "up")
    cursor.execute(schemas)
    assert cursor.fetchone()[0] == 4
    connection.close()


# --- Fictional data and city consistency (rule 1.3.1) -------------------------------------


def test_every_business_table_carries_is_fictional_and_city_link(db: Db) -> None:
    tables = db.run(
        "select n.nspname || '.' || c.relname from pg_class c "
        "join pg_namespace n on n.oid = c.relnamespace "
        "where n.nspname in ('network', 'mobility', 'identity', 'ops') "
        "and c.relkind in ('r', 'p') and not c.relispartition order by 1"
    )
    checked = 0
    for (table,) in tables:
        if table in NON_BUSINESS_TABLES:
            continue
        schema, name = table.split(".")
        columns = dict(
            db.run(
                "select column_name, is_nullable from information_schema.columns "
                "where table_schema = %s and table_name = %s",
                schema,
                name,
            )
        )
        assert columns.get("is_fictional") == "NO", f"{table} : is_fictional manquant ou nullable"
        if "city_id" in columns:
            links = db.value(
                "select count(*) from pg_constraint k "
                "where k.contype = 'f' and k.conrelid = %s::regclass "
                "and k.confrelid = 'network.city'::regclass "
                "and (select array_agg(a.attname::text order by a.attname) from pg_attribute a "
                "     where a.attrelid = k.conrelid and a.attnum = any(k.conkey)) "
                "    = array['city_id', 'is_fictional']",
                table,
            )
            assert links == 1, f"{table} : clé (city_id, is_fictional) vers network.city absente"
        checked += 1
    assert checked >= 30


def test_fictional_and_real_records_cannot_be_mixed(db: Db) -> None:
    real_city = make_city(db, "ville-reelle")
    code, _ = db.error(
        "insert into network.stop (city_id, is_fictional, code, kind, name, geom, source_id) "
        "values (%s, true, 'x', 'gare_artisanale', 'x', "
        "ST_SetSRID(ST_MakePoint(-4, 5), 4326), 'test')",
        real_city,
    )
    assert code == "23503"


def test_records_of_two_cities_cannot_be_linked(db: Db) -> None:
    city_a = make_city(db, "ville-a")
    city_b = make_city(db, "ville-b")
    route_a = make_route(db, city_a, "ligne-a")
    code, _ = db.error(
        "insert into network.route_pattern (city_id, route_id, code, direction_id) "
        "values (%s, %s, 'p', 0)",
        city_b,
        route_a,
    )
    assert code == "23503"


# --- Network versions (partie 6.3, ADR-008) -----------------------------------------------


def test_version_numbers_are_sequential_per_city(db: Db) -> None:
    city_a = make_city(db, "ville-a")
    city_b = make_city(db, "ville-b")
    numbers = [
        db.value("insert into network.network_version (city_id) values (%s) returning number", city)
        for city in (city_a, city_a, city_b)
    ]
    assert numbers == [1, 2, 1]


def test_publication_requires_review_and_refuses_fictional_city_in_production(db: Db) -> None:
    city = make_city(db, "lagune-test", fictional=True)
    version = db.value(
        "insert into network.network_version (city_id, is_fictional) "
        "values (%s, true) returning id",
        city,
    )
    assert db.error("select network.publish_version(%s)", version)[0] == "NM002"

    db.run("update network.network_version set status = 'en_revue' where id = %s", version)
    db.run("select set_config('nemesis.environment', 'production', true)")
    code, message = db.error("select network.publish_version(%s)", version)
    assert code == "NM001" and "fictive" in message

    db.run("select set_config('nemesis.environment', 'development', true)")
    db.run("select network.publish_version(%s)", version)
    assert (
        db.value("select status from network.network_version where id = %s", version) == "publiee"
    )

    assert (
        db.error("update network.network_version set notes = 'x' where id = %s", version)[0]
        == "NM002"
    )
    assert db.error("delete from network.network_version where id = %s", version)[0] == "NM002"


def test_status_cannot_jump_to_published_without_the_function(db: Db) -> None:
    city = make_city(db, "ville-reelle")
    version = db.value(
        "insert into network.network_version (city_id) values (%s) returning id", city
    )
    code, _ = db.error(
        "update network.network_version set status = 'publiee', published_at = now() where id = %s",
        version,
    )
    assert code == "NM002"


def test_change_requests_need_a_second_person_and_a_reason_to_reject(db: Db) -> None:
    city = make_city(db, "ville-reelle")
    author, reviewer = make_staff(db), make_staff(db, "moderateur")
    insert = (
        "insert into network.change_request "
        "(city_id, title, operations, status, proposed_by, reviewed_by, reviewed_at, "
        "review_reason) "
        "values (%s, 't', '[]', %s, %s, %s, %s, %s)"
    )
    now = datetime.now(UTC)
    assert db.error(insert, city, "approuvee", author, author, now, None)[0] == "23514"
    assert db.error(insert, city, "rejetee", author, reviewer, now, " ")[0] == "23514"
    assert db.error(insert, city, "approuvee", author, None, None, None)[0] == "23514"
    db.run(insert, city, "rejetee", author, reviewer, now, "Doublon de la demande précédente")


# --- Roles (H-016) ------------------------------------------------------------------------


def test_roles_separate_identity_from_mobility(db: Db) -> None:
    db.run("set local role nemesis_api")
    assert db.error("select count(*) from identity.account")[0] == "42501"
    db.run("select count(*) from network.city")
    db.run("select count(*) from mobility.observation")
    db.run("reset role")

    db.run("set local role nemesis_analyst")
    assert db.error("select count(*) from mobility.observation")[0] == "42501"
    assert db.error("select count(*) from mobility.trace_segment")[0] == "42501"
    db.run("select count(*) from mobility.queue_state")
    db.run("reset role")

    db.run("set local role nemesis_identity")
    db.run("select count(*) from identity.account")
    db.run("select id, status from mobility.observation limit 1")
    assert db.error("select geom from mobility.observation limit 1")[0] == "42501"
    db.run("reset role")


def test_only_maintenance_can_run_partition_maintenance(db: Db) -> None:
    db.run("set local role nemesis_api")
    assert db.error("select * from ops.maintain_partitions()")[0] == "42501"
    db.run("reset role")


# --- Audit log (partie 12.3) --------------------------------------------------------------


def test_audit_log_is_append_only_and_chained(db: Db) -> None:
    for action in ("creation", "modification", "publication"):
        db.run(
            "insert into ops.audit_log (actor_role, action, entity_table, details) "
            "values ('curateur', %s, 'network.stop', '{\"champ\": \"nom\"}')",
            action,
        )
    assert db.value("select ops.verify_audit_chain()") is None
    assert db.value("select count(*) from ops.audit_log where prev_hash is null") == 1

    assert db.error("update ops.audit_log set action = 'x'")[0] == "NM003"
    assert db.error("delete from ops.audit_log")[0] == "NM003"
    assert db.error("truncate ops.audit_log")[0] == "NM003"

    # Simulated tampering by someone who bypasses the triggers.
    db.run("alter table ops.audit_log disable trigger audit_log_no_update")
    db.run('update ops.audit_log set details = \'{"champ": "autre"}\' where chain_seq = 2')
    db.run("alter table ops.audit_log enable trigger audit_log_no_update")
    assert db.value("select ops.verify_audit_chain()") == 2


# --- Partitions and retention (ADR-005, docs/PRIVACY.md) ----------------------------------


def partitions(db: Db, table: str) -> list[str]:
    return [
        name
        for (name,) in db.run(
            "select c.relname from pg_inherits i join pg_class c on c.oid = i.inhrelid "
            "where i.inhparent = %s::regclass order by 1",
            table,
        )
    ]


def test_partitions_are_created_ahead_and_dropped_after_retention(db: Db) -> None:
    city = make_city(db, "ville-reelle")
    reference = datetime(2030, 1, 15, 12, tzinfo=UTC)
    db.run("select * from ops.maintain_partitions(%s)", reference)
    observation_days = [p for p in partitions(db, "mobility.observation") if "_p2030" in p]
    assert observation_days[0] == "observation_p20300108"
    assert observation_days[-1] == "observation_p20300122"
    assert len(observation_days) == 15

    insert = (
        "insert into mobility.observation "
        "(id, observed_at, received_at, city_id, kind, source_kind) "
        "values (%s, %s, %s, %s, 'file', 'usager')"
    )
    db.run(insert, str(uuid.uuid4()), reference, reference, city)
    later = reference + timedelta(days=30)
    assert db.error(insert, str(uuid.uuid4()), later, later, city)[0] == "23514"

    # 13 months later: 2030-01 observations are past the 12-month retention,
    # and positions are past their 30 days.
    actions = db.run("select * from ops.maintain_partitions(%s)", reference + timedelta(days=400))
    dropped = {name for action, name in actions if action == "supprimee"}
    assert "observation_p20300115" in dropped
    assert "position_event_p20300115" in dropped
    assert not [
        p for p in partitions(db, "mobility.observation") if p.startswith("observation_p203001")
    ]


# --- Observations and estimates -----------------------------------------------------------


def test_observations_are_idempotent_and_reject_future_clocks(db: Db) -> None:
    city = make_city(db, "ville-reelle")
    db.run("select * from ops.maintain_partitions()")
    now = datetime.now(UTC)
    key = str(uuid.uuid4())
    insert = (
        "insert into mobility.observation (id, observed_at, city_id, kind, source_kind) "
        "values (%s, %s, %s, 'dans_la_file', 'usager')"
    )
    db.run(insert, key, now, city)
    assert db.error(insert, key, now, city)[0] == "23505"
    assert db.error(insert, str(uuid.uuid4()), now + timedelta(minutes=10), city)[0] == "23514"


def test_estimates_carry_freshness_confidence_and_source(db: Db) -> None:
    city = make_city(db, "ville-reelle")
    stop = make_stop(db, city, "gare")
    insert = (
        "insert into mobility.queue_state "
        "(city_id, stop_id, level, wait_p50_s, wait_p80_s, confidence, main_source, "
        "last_observed_at) "
        "values (%s, %s, 'beaucoup', %s, %s, %s, 'usagers', now())"
    )
    assert db.error(insert, city, stop, 600, 1200, None)[0] == "23502"
    assert db.error(insert, city, stop, 1200, 600, "moyenne")[0] == "23514"
    db.run(insert, city, stop, 600, 1200, "moyenne")


def test_fare_estimates_are_ordered_percentiles(db: Db) -> None:
    city = make_city(db, "ville-reelle")
    route = make_route(db, city, "ligne")
    areas = [
        db.value(
            "insert into network.fare_area (city_id, code, name) "
            "values (%s, %s, %s) returning id::text",
            city,
            code,
            code,
        )
        for code in ("zone-a", "zone-b")
    ]
    insert = (
        "insert into mobility.fare_estimate "
        "(city_id, route_id, from_area_id, to_area_id, condition, "
        "fare_p10, fare_p50, fare_p90, n_obs, n_contributors, last_observed_at, confidence) "
        "values (%s, %s, %s, %s, 'pointe', %s, %s, %s, 30, 25, now(), 'moyenne')"
    )
    assert db.error(insert, city, route, *areas, 400, 300, 500)[0] == "23514"
    db.run(insert, city, route, *areas, 300, 350, 500)


def test_service_slots_are_quarter_hours(db: Db) -> None:
    city = make_city(db, "ville-reelle")
    stop = make_stop(db, city, "gare")
    route = make_route(db, city, "ligne")
    pattern = db.value(
        "insert into network.route_pattern (city_id, route_id, code, direction_id) "
        "values (%s, %s, 'p0', 0) returning id::text",
        city,
        route,
    )
    insert = (
        "insert into network.service_profile "
        "(city_id, route_pattern_id, stop_id, day_type, slot_start, active, departs_when_full) "
        "values (%s, %s, %s, 'ouvrable', %s, true, true)"
    )
    assert db.error(insert, city, pattern, stop, "06:20")[0] == "23514"
    db.run(insert, city, pattern, stop, "06:15")


# --- Reference data, geometry, search -----------------------------------------------------


def test_text_normalization_and_trigram_search(db: Db) -> None:
    assert (
        db.value("select network.normalize_text('  Wôrô-wôrô  du Marché !')")
        == "woro woro du marche"
    )
    city = make_city(db, "ville-reelle")
    place = db.value(
        "insert into network.place (city_id, category, name, geom, source_id) "
        "values (%s, 'gare', 'Gare des Flamboyants', "
        "ST_SetSRID(ST_MakePoint(-4, 5.3), 4326), 'test') "
        "returning id::text",
        city,
    )
    db.run(
        "insert into network.place_alias (place_id, city_id, alias, alias_kind) "
        "values (%s, %s, 'Gare des Flamboyants', 'nom')",
        place,
        city,
    )
    best = db.value(
        "select place_id::text from network.place_alias "
        "where normalized % network.normalize_text('flamboyan gare') "
        "order by similarity(normalized, network.normalize_text('flamboyan gare')) desc limit 1"
    )
    assert best == place


def test_geometries_must_be_wgs84(db: Db) -> None:
    city = make_city(db, "ville-reelle")
    code, _ = db.error(
        "insert into network.stop (city_id, code, kind, name, geom, source_id) "
        "values (%s, 'x', 'gare_artisanale', 'x', "
        "ST_SetSRID(ST_MakePoint(-445000, 590000), 3857), 'test')",
        city,
    )
    assert code == "22023"


def test_back_office_accounts_require_two_factor_authentication(db: Db) -> None:
    code, _ = db.error(
        "insert into ops.staff_account (display_name, email, role) "
        "values ('Test', 'test@example.invalid', 'curateur')"
    )
    assert code == "23514"


def test_reference_vocabularies_match_the_specification(db: Db) -> None:
    modes = {code for (code,) in db.run("select code from network.mode")}
    assert modes == {
        "bus_sotra",
        "bus_express",
        "bateau_bus",
        "pinasse",
        "gbaka",
        "woro_communal",
        "woro_intercommunal",
        "taxi_compteur",
        "moto_taxi",
        "tricycle",
        "metro",
        "brt",
        "car_interurbain",
    }
    assert db.value("select count(*) from network.stop_kind") == 8


# --- Retention of non-partitioned data -----------------------------------------------------


def test_expired_rows_are_purged(db: Db) -> None:
    long_ago = datetime.now(UTC) - timedelta(days=40)
    db.run(
        "insert into identity.account (phone_hmac, phone_encrypted, deleted_at) "
        "values (sha256('a'::bytea), 'x'::bytea, %s), (sha256('b'::bytea), 'y'::bytea, now())",
        long_ago,
    )
    purged = dict(db.run("select * from ops.purge_expired()"))
    assert purged["identity.account"] == 1
    assert db.value("select count(*) from identity.account") == 1


# --- Development seed ----------------------------------------------------------------------


def test_development_seed_is_fictional_and_idempotent(fresh_database: dict[str, Any]) -> None:
    connection = pg8000.dbapi.connect(**fresh_database)
    apply_migrations(connection)
    connection.autocommit = True
    cursor = connection.cursor()
    seed = SEED.read_text(encoding="utf-8")
    cursor.execute(seed)
    cursor.execute(seed)
    cursor.execute(
        "select (select count(*) from network.stop), (select count(*) from network.route), "
        "(select count(*) from network.city where not is_fictional), "
        "(select count(*) from network.stop where not is_fictional), "
        "(select count(*) from network.network_version)"
    )
    assert tuple(cursor.fetchone()) == (4, 2, 0, 0, 1)
    connection.close()

"""Data embedded in the mobile prototype (I0.11): fictional, consistent with the database
and with the engine's pack."""

import json

from nemesis_pipelines.fixtures.cli import generated_files
from nemesis_pipelines.fixtures.mobile import ASSETS, ENGINE_FILES
from nemesis_pipelines.fixtures.sql import ident


def test_the_app_carries_the_engine_pack_with_its_gtfs_beside_it() -> None:
    files = generated_files()
    pack = json.loads(files[ASSETS / "pack" / "pack.json"])
    assert pack["gtfs"] == "gtfs"
    assert pack["is_fictional"] is True
    for name in ("stops.txt", "stop_times.txt", "frequencies.txt", "ext_wait_profiles.txt"):
        assert (ASSETS / "pack" / "gtfs" / name) in files
    carried = {p.name for p in files if p.parent == ASSETS / "pack" / "gtfs"}
    assert carried <= set(ENGINE_FILES)
    assert "ext_service_profiles.txt" not in carried


def test_city_json_is_fictional_and_names_the_database_identifiers() -> None:
    city = json.loads(generated_files()[ASSETS / "city.json"])
    assert city["city"]["is_fictional"] is True
    stops = {s["code"]: s for s in city["stops"]}
    assert stops["flamboyants"]["id"] == ident("stop", "flamboyants")
    assert all(
        s["name"].endswith("(fictif)") and "(fictif) (fictif)" not in s["name"]
        for s in city["stops"]
    )
    assert {line["code"] for line in city["lines"]} >= {"g1", "b1"}
    assert "g1" in stops["flamboyants"]["lines"]
    flamboyants = [w for w in city["waits"] if w["stop"] == "flamboyants" and w["line"] == "g1"]
    assert flamboyants and all(w["regime"] == "A" for w in flamboyants)
    slots = flamboyants[0]["slots"]
    assert all(p50 <= p80 for _, p50, p80, _ in slots)


def test_the_map_has_streets_and_line_shapes() -> None:
    data = json.loads(generated_files()[ASSETS / "map.json"])
    assert len(data["roads"]["features"]) > 10
    lines = {f["properties"]["line"] for f in data["lines"]["features"]}
    assert {"g1", "b1"} <= lines

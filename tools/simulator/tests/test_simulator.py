"""Simulator (I0.10): reproducibility, duration, invariants, reports, and the key test of
PHASE-0.md — the closed formulas of the waits (ALGORITHMES.md 1.2, 1.3) against the
simulation, through the coverage of their 80th percentile."""

from __future__ import annotations

import json
import time
from dataclasses import replace
from functools import cache
from pathlib import Path

import pytest

from nemesis_simulator.cli import EXAMPLE, example_text, main
from nemesis_simulator.evaluate import PLAUSIBLE_M, distance_m, evaluate, wilson
from nemesis_simulator.formulas import (
    Cumulative,
    HeadState,
    corrected_a,
    documented_a,
    documented_b,
    erlang_cdf,
    quantile,
)
from nemesis_simulator.output import observations_jsonl
from nemesis_simulator.reports import fixture_id, reports
from nemesis_simulator.scenario import Profile, Scenario, load
from nemesis_simulator.sim import simulate

SEEDS = range(5)


def constant(value: float) -> Profile:
    return Profile((0,), (value,))


@cache
def scenario() -> Scenario:
    return load()


@cache
def stationary() -> Scenario:
    """Constant rates, Poisson vehicles, no rain: the hypotheses of the formulas hold."""
    s = scenario()
    return replace(
        s,
        rain=(),
        head=replace(
            s.head,
            vehicle_headway_cv=1.0,
            vehicle_headway_s=constant(312),
            passengers_per_min=constant(3.3),
        ),
        travel=replace(s.travel, traffic_factor=constant(1.0)),
    )


@cache
def poisson_roadside() -> Scenario:
    """Roadside stops served by the passing bus only, at Poisson times, few passengers."""
    s = scenario()
    return replace(
        s,
        rain=(),
        head=replace(s.head, vehicle_headway_s=constant(1e9), passengers_per_min=constant(0.0)),
        passing=tuple(
            replace(p, headway_cv=1.0, headway_s=constant(600), free_seats_mean=constant(1.5))
            for p in s.passing
        ),
        roadside=replace(
            s.roadside,
            stops=("arret-03", "arret-02", "arret-01"),
            passengers_per_min=constant(0.03),
            destinations={"arret-02": 1, "arret-01": 1, "baobab": 2},
        ),
        travel=replace(s.travel, traffic_factor=constant(1.0)),
    )


@cache
def results(name: str) -> dict:
    variant = {"real": scenario, "stationary": stationary, "poisson": poisson_roadside}[name]()
    return evaluate(simulate(variant, seed) for seed in SEEDS)


# Formulas -----------------------------------------------------------------------------


def test_the_examples_of_algorithmes_md_are_reproduced() -> None:
    # 1.2, case 1: r = 6, λp = 1,5 per minute: W − d0 ~ Gamma(5, 1,5), p50 3,1 min, p80 4,5 min.
    assert quantile(lambda x: erlang_cdf(5, 1.5, x), 0.5) == pytest.approx(3.1, abs=0.05)
    assert quantile(lambda x: erlang_cdf(5, 1.5, x), 0.8) == pytest.approx(4.5, abs=0.05)
    # 1.2, case 2: n = 3, λv = 0,2 per minute: p50 13,4 min, p80 21,4 min.
    assert quantile(lambda x: erlang_cdf(3, 0.2, x), 0.5) == pytest.approx(13.4, abs=0.05)
    assert quantile(lambda x: erlang_cdf(3, 0.2, x), 0.8) == pytest.approx(21.4, abs=0.05)
    # 1.3: λ = 3 per hour: p50 13,9 min, p80 32,2 min.
    p50, p80 = documented_b(3 / 60)
    assert (round(p50, 1), round(p80, 1)) == (13.9, 32.2)


def test_the_corrected_formula_waits_for_the_vehicle_to_fill() -> None:
    # Nobody in the queue, no vehicle: the documented formula only waits for a vehicle,
    # the corrected one also for the 17 passengers who will fill it.
    state = HeadState(0, 0, 0, False, None, 18, 2 / 60, 1 / 300, 60, 1200)
    doc, cor = documented_a(state), corrected_a(state)
    assert cor[0] > doc[0] + 60
    # A long queue: the vehicles fill at once, both formulas agree.
    state = replace(state, queue_ahead=80)
    assert corrected_a(state) == pytest.approx(documented_a(state), abs=1.0)


def test_a_constant_profile_gives_the_constant_rate_formula() -> None:
    profile = Cumulative([0.0, 3600.0, 7200.0], lambda t: 0.05)
    state = HeadState(30, 0, 0, False, None, 18, 0.05, 1 / 300, 60, 1200)
    along = replace(
        state,
        passengers_profile=(profile, 100.0),
        vehicles_profile=(Cumulative([0.0, 3600.0], lambda t: 1 / 300), 100.0),
    )
    assert corrected_a(along, along_profile=True) == pytest.approx(corrected_a(state), abs=0.2)


def test_wilson_interval() -> None:
    low, high = wilson(80, 100)
    assert (round(low, 3), round(high, 3)) == (0.711, 0.867)


# The key test: closed formulas against the simulator ---------------------------------


def test_regime_a_formulas_are_calibrated_when_their_hypotheses_hold() -> None:
    result = results("stationary")
    for key in ("regime_a_documented", "regime_a_corrected"):
        for group in ("tous", "cas 1", "cas 2"):
            row = result[key][group]
            assert row["n"] > 1000
            assert row["verdict"] == "calibrée", (key, group, row)


def test_the_exponential_of_regime_b_is_calibrated_with_poisson_passages() -> None:
    row = results("poisson")["regime_b_documented"]["tous"]
    assert row["n"] > 300
    assert row["verdict"] == "calibrée", row


def test_on_the_corridor_the_rates_of_the_coming_slots_calibrate_regime_a() -> None:
    result = results("real")
    for group in ("tous", "pointe", "pluie"):
        row = result["regime_a_corrected_profile"][group]
        assert 0.76 <= row["coverage_p80"] <= 0.86, (group, row)
    # Without them, rain is overestimated: the wait spans its end, when vehicles come back.
    assert result["regime_a_documented"]["pluie"]["verdict"] == "trop prudente"


def test_regime_b_is_too_optimistic_when_others_wait_for_the_same_seats() -> None:
    """Finding of I0.10, reported in ALGORITHMES.md 1.3: the exponential ignores the
    competition for free seats. A newcomer alone is well served by it."""
    result = results("real")["regime_b_documented"]
    assert result["d'autres attendent"]["verdict"] == "trop optimiste"
    assert result["d'autres attendent"]["coverage_p80"] < 0.7
    assert result["seul à attendre"]["verdict"] == "calibrée"


# Runs ----------------------------------------------------------------------------------


def test_a_peak_day_takes_well_under_a_minute_and_is_reproducible() -> None:
    started = time.perf_counter()
    truth = simulate(scenario(), 42)
    sent = reports(truth)
    assert time.perf_counter() - started < 60
    again = simulate(scenario(), 42)
    assert observations_jsonl(truth, sent) == observations_jsonl(again, reports(again))
    assert [p.wait_s for p in truth.passengers] == [p.wait_s for p in again.passengers]
    other = simulate(scenario(), 43)
    assert [p.wait_s for p in truth.passengers] != [p.wait_s for p in other.passengers]


def test_the_peak_builds_a_queue_at_the_head_station() -> None:
    truth = simulate(scenario(), 42)
    longest = max(q for _, q, _ in truth.head_states)
    assert 30 <= longest <= 300
    waits = sorted(p.wait_s for p in truth.passengers if p.regime == "A" and p.wait_s)
    assert 20 * 60 < waits[-1] < 3 * 3600


def test_the_head_station_is_first_come_first_served() -> None:
    truth = simulate(scenario(), 42)
    head = [p for p in truth.passengers if p.regime == "A" and p.depart_s is not None]
    departures = [p.depart_s for p in sorted(head, key=lambda p: p.arrival_s)]
    assert departures == sorted(departures)
    seats = scenario().head.seats
    for departure in truth.departures:
        assert 0 < departure.onboard <= seats
        if departure.reason == "plein":
            assert departure.onboard == seats


def test_vehicles_never_carry_more_than_their_seats() -> None:
    truth = simulate(scenario(), 42)
    assert all(passage.free_seats >= 0 for passage in truth.passages)
    assert all(passage.boarded <= passage.free_seats for passage in truth.passages)


def test_only_fictional_scenarios_are_accepted(tmp_path: Path) -> None:
    text = (
        scenario()
        .path.read_text(encoding="utf-8")
        .replace("is_fictional = true", "is_fictional = false")
    )
    path = tmp_path / "reel.toml"
    path.write_text(text, encoding="utf-8")
    with pytest.raises(ValueError, match="fictives"):
        load(path)


# Reports -------------------------------------------------------------------------------


def test_reports_carry_noise_delays_resends_and_fraud() -> None:
    truth = simulate(scenario(), 42)
    sent = reports(truth)
    kinds = {r.request["kind"] for r in sent}
    assert kinds == {"file", "vehicules_presents", "attente_reelle", "prix_paye", "vehicule_plein"}
    assert all(r.received_s >= r.observed_s for r in sent)
    resent = [r for r in sent if r.duplicate]
    assert resent
    first = {r.request["id"] for r in sent if not r.duplicate}
    assert all(r.request["id"] in first for r in resent)
    # The station manager is exact; some honest users are not.
    manager = [r for r in sent if r.source_kind == "chef_de_gare"]
    assert manager
    assert all(list(r.request["payload"].values()) == [r.true_value] for r in manager)
    queue = [r for r in sent if r.request["kind"] == "file" and r.honest]
    assert any(r.request["payload"]["level"] != r.true_value for r in queue)
    # The 150 m rule catches the reports made from afar, and no honest one.
    stops = {fixture_id("stop", s.code): s for s in scenario().stops}
    for r in sent:
        stop = stops[r.request["stop_id"]]
        far = distance_m(r.request["location"], stop.lat, stop.lon) > PLAUSIBLE_M
        assert far == (r.fraud == "file_a_distance"), r


def test_identifiers_are_those_of_the_fictional_city_in_the_database() -> None:
    sql = pytest.importorskip("nemesis_pipelines.fixtures.sql")
    for code in ("flamboyants", "arret-03", "grand-marche"):
        assert fixture_id("stop", code) == sql.ident("stop", code)
    assert fixture_id("route", "g1") == sql.ident("route", "g1")


def test_the_versioned_example_is_up_to_date() -> None:
    assert EXAMPLE.read_text(encoding="utf-8") == example_text()


def test_the_command_line_writes_reports_and_truth(tmp_path: Path) -> None:
    out = tmp_path / "run"
    assert main(["simuler", "--sortie", str(out), "--debut", "07:00", "--fin", "08:00"]) == 0
    summary = json.loads((out / "run.json").read_text(encoding="utf-8"))
    assert summary["is_fictional"] is True
    assert summary["reports"] == len((out / "observations.jsonl").read_text().splitlines())
    for name in ("passengers", "passages", "departures", "head_station", "reports"):
        assert (out / "verite" / f"{name}.csv").exists()
    assert main(["exemple", "--verifier"]) == 0

"""Fictional OSM extract of Lagune-Fictive (I0.7)."""

from __future__ import annotations

import xml.etree.ElementTree as ElementTree
from pathlib import Path

from nemesis_pipelines.fixtures.city import build_city
from nemesis_pipelines.fixtures.geo import distance_m
from nemesis_pipelines.fixtures.osm import (
    EXTRA_ROUTE,
    EXTRA_STOP,
    MISSING_ROUTE,
    MISSING_STOP,
    MOVED_FAR,
    MOVED_NEAR,
    RENAMED,
    osm_xml,
)


def _tree() -> ElementTree.Element:
    return ElementTree.fromstring(osm_xml(build_city()))


def _tags(element: ElementTree.Element) -> dict[str, str]:
    return {tag.get("k", ""): tag.get("v", "") for tag in element.findall("tag")}


def test_the_extract_is_deterministic_and_committed(repository: Path) -> None:
    content = osm_xml(build_city())
    assert content == osm_xml(build_city())
    committed = repository / "data/fixtures_fictives/osm/lagune-fictive.osm"
    assert committed.read_bytes().decode("utf-8") == content


def test_every_element_is_fictional_and_every_name_says_so() -> None:
    root = _tree()
    elements = [e for e in root if e.tag in ("node", "way", "relation")]
    assert elements
    for element in elements:
        tags = _tags(element)
        assert tags.get("fictional") == "yes", element.attrib
        if "name" in tags:
            assert tags["name"].endswith("(fictif)"), tags["name"]


def test_references_are_consistent() -> None:
    root = _tree()
    ids = {kind: {e.get("id") for e in root.iter(kind)} for kind in ("node", "way", "relation")}
    for way in root.iter("way"):
        assert {nd.get("ref") for nd in way.iter("nd")} <= ids["node"]
    for relation in root.iter("relation"):
        for member in relation.iter("member"):
            assert member.get("ref") in ids[member.get("type", "")]


def test_the_deliberate_gaps_are_in_the_extract() -> None:
    city = build_city()
    root = _tree()
    stops = {(_tags(n).get("name")): n for n in root.iter("node") if "name" in _tags(n)}

    def position(name: str) -> tuple[float, float]:
        node = stops[name]
        return float(node.get("lon", 0)), float(node.get("lat", 0))

    assert city.stops[MISSING_STOP].name not in stops
    near = city.stops[MOVED_NEAR[0]]
    assert round(distance_m(near.lon, near.lat, *position(near.name))) == MOVED_NEAR[1]
    far = city.stops[MOVED_FAR[0]]
    assert round(distance_m(far.lon, far.lat, *position(far.name))) == MOVED_FAR[1]
    assert city.stops[RENAMED[0]].name not in stops and RENAMED[1] in stops
    # The OSM-only stop is not within matching distance of any GTFS stop.
    lon, lat = position(EXTRA_STOP[0])
    assert min(distance_m(s.lon, s.lat, lon, lat) for s in city.stops.values()) > 50

    refs = {_tags(r).get("ref") for r in root.iter("relation") if _tags(r).get("type") == "route"}
    assert MISSING_ROUTE.upper() not in refs
    assert EXTRA_ROUTE[0] in refs
    assert len([r for r in root.iter("relation") if _tags(r).get("type") == "route_master"]) == 11

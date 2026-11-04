"""Source manifest and verified downloads (I0.7)."""

from __future__ import annotations

import hashlib
import http.server
import json
import re
import threading
import zipfile
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from nemesis_pipelines.checksum import ChecksumMismatchError
from nemesis_pipelines.download import fetch, gtfs_zip, parse_md5
from nemesis_pipelines.sources import ManifestError, Source, load_manifest, parse_manifest


def _manifest(**overrides: Any) -> dict[str, Any]:
    source = {
        "kind": "gtfs",
        "name": "Source de test",
        "url": "https://example.org/gtfs.zip",
        "sha256": "0" * 64,
        "license": "ODbL-1.0",
        "attribution": "Exemple",
        "usage": "produit",
    }
    source.update(overrides)
    return {"sources": {"test": {k: v for k, v in source.items() if v is not None}}}


def test_the_repository_manifest_is_valid(repository: Path) -> None:
    manifest = load_manifest(repository / "data/pipelines/sources.toml")
    assert set(manifest.profiles) == {"reel", "fictif"}
    gtfs = manifest.source("gtfs_abidjan_2023")
    # CC BY-NC 4.0 (README of the original repository): internal evaluation only (H-030).
    assert (gtfs.license, gtfs.usage) == ("CC-BY-NC-4.0", "evaluation")
    assert gtfs.sha256 and "ref=da5d9faf" in (gtfs.url or "")
    osm = manifest.source("osm_cote_divoire")
    assert osm.md5_url and osm.attribution == "© les contributeurs d'OpenStreetMap"
    for profile in manifest.profiles.values():
        city = manifest.city(profile.city)
        assert manifest.source(profile.osm).is_fictional == city.is_fictional


def test_the_validator_image_is_the_one_of_the_ci(repository: Path) -> None:
    manifest = load_manifest(repository / "data/pipelines/sources.toml")
    workflow = (repository / ".github/workflows/ci-gtfs.yml").read_text(encoding="utf-8")
    match = re.search(r"VALIDATOR_IMAGE: (\S+)", workflow)
    assert match and match.group(1) == manifest.tool("gtfs_validator")


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"sha256": None}, "non vérifiable"),
        ({"md5_url": "https://example.org/x.md5"}, "non vérifiable"),
        ({"url": "http://example.org/gtfs.zip"}, "https"),
        ({"attribution": None}, "attribution"),
        ({"usage": "libre"}, "usage"),
        ({"is_fictional": True}, "fichier du dépôt"),
        ({"url": None, "sha256": None, "path": "x"}, "que fictif"),
        ({"sha256": "abc"}, "64 caractères"),
        ({"licence": "faute de frappe"}, "clés inconnues"),
    ],
)
def test_an_unverifiable_or_inconsistent_source_is_refused(
    overrides: dict[str, Any], message: str
) -> None:
    with pytest.raises(ManifestError, match=message):
        parse_manifest(_manifest(**overrides))


def test_a_profile_cannot_mix_fictional_and_real_data() -> None:
    data = _manifest()
    data["sources"]["osm"] = {
        "kind": "osm",
        "name": "OSM fictif",
        "path": "x.osm",
        "license": "test",
        "usage": "produit",
        "is_fictional": True,
    }
    data["cities"] = {
        "ville": {
            "name": "Ville",
            "timezone": "Africa/Abidjan",
            "metric_srid": 32630,
            "bbox": [-4.1, 5.1, -3.9, 5.3],
        }
    }
    data["profiles"] = {"p": {"city": "ville", "osm": "osm", "gtfs": "test"}}
    with pytest.raises(ManifestError, match="mêlent fictif et réel"):
        parse_manifest(data)


def test_tool_images_are_pinned_by_digest() -> None:
    data = {**_manifest(), "tools": {"planetiler": "ghcr.io/onthegomap/planetiler:latest"}}
    with pytest.raises(ManifestError, match="empreinte"):
        parse_manifest(data)


# --- Downloads ---------------------------------------------------------------------------


class _Files(http.server.BaseHTTPRequestHandler):
    files: dict[str, bytes] = {}
    requests: list[str] = []

    def do_GET(self) -> None:  # noqa: N802 (http.server API)
        self.requests.append(self.path)
        body = self.files.get(self.path)
        if body is None:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Last-Modified", "Wed, 04 Nov 2026 06:00:00 GMT")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args: object) -> None:
        pass


@pytest.fixture
def server() -> Iterator[str]:
    _Files.files, _Files.requests = {}, []
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Files)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}"
    httpd.shutdown()


def _source(**values: Any) -> Source:
    # Built directly: the manifest only accepts https, the test server is plain http.
    base = {
        "id": "test",
        "kind": "osm",
        "name": "Test",
        "license": "ODbL-1.0",
        "usage": "produit",
        "attribution": "Exemple",
    }
    return Source(**{**base, **values})


def test_a_pinned_file_is_verified_and_its_provenance_kept(server: str, tmp_path: Path) -> None:
    body = b"contenu de test"
    _Files.files["/x.pbf"] = body
    source = _source(url=f"{server}/x.pbf", sha256=hashlib.sha256(body).hexdigest())
    fetched = fetch(source, tmp_path)
    assert fetched.path.read_bytes() == body
    provenance = json.loads((fetched.path.parent / "provenance.json").read_text(encoding="utf-8"))
    assert provenance["verified_by"] == "sha256_epinglee"
    assert provenance["size_bytes"] == len(body)
    assert provenance["last_modified"] == "Wed, 04 Nov 2026 06:00:00 GMT"
    assert provenance["license"] == "ODbL-1.0"
    # Already there and unchanged: no second download.
    fetch(source, tmp_path)
    assert _Files.requests == ["/x.pbf"]


def test_a_file_that_does_not_match_its_pin_is_deleted(server: str, tmp_path: Path) -> None:
    _Files.files["/x.pbf"] = b"autre contenu"
    source = _source(url=f"{server}/x.pbf", sha256="0" * 64)
    with pytest.raises(ChecksumMismatchError, match="la source a changé"):
        fetch(source, tmp_path)
    assert not list((tmp_path / "sources" / "test").glob("x.pbf*"))


def test_the_md5_published_by_the_source_is_checked(server: str, tmp_path: Path) -> None:
    body = b"extrait du jour"
    digest = hashlib.md5(body, usedforsecurity=False).hexdigest()
    _Files.files.update({"/x.pbf": body, "/x.pbf.md5": f"{digest}  x.pbf\n".encode()})
    fetched = fetch(_source(url=f"{server}/x.pbf", md5_url=f"{server}/x.pbf.md5"), tmp_path)
    assert fetched.provenance.verified_by == "md5_publiee"
    assert fetched.provenance.md5 == digest

    _Files.files["/y.pbf"] = b"fichier corrompu"
    _Files.files["/y.pbf.md5"] = f"{digest}  y.pbf\n".encode()
    with pytest.raises(ChecksumMismatchError, match="différente de celle publiée"):
        fetch(_source(id="y", url=f"{server}/y.pbf", md5_url=f"{server}/y.pbf.md5"), tmp_path)


def test_an_unreadable_md5_is_an_error() -> None:
    with pytest.raises(ChecksumMismatchError):
        parse_md5("<html>404</html>")
    assert (
        parse_md5("D41D8CD98F00B204E9800998ECF8427E  vide\n") == "d41d8cd98f00b204e9800998ecf8427e"
    )


def test_repository_files_are_fictional_and_archived_deterministically(
    repository: Path, tmp_path: Path
) -> None:
    manifest = load_manifest(repository / "data/pipelines/sources.toml")
    source = manifest.source("gtfs_lagune_fictive")
    first = fetch(source, tmp_path / "a", root=repository)
    second = fetch(source, tmp_path / "b", root=repository)
    assert first.provenance.sha256 == second.provenance.sha256
    assert first.provenance.verified_by == "fichier_du_depot"
    assert first.provenance.is_fictional
    with zipfile.ZipFile(first.path) as archive:
        assert "stops.txt" in archive.namelist()


def test_gtfs_zip_ignores_non_gtfs_files(tmp_path: Path) -> None:
    (tmp_path / "gtfs").mkdir()
    (tmp_path / "gtfs" / "stops.txt").write_text("stop_id\n", encoding="utf-8")
    (tmp_path / "gtfs" / "notes.md").write_text("x", encoding="utf-8")
    gtfs_zip(tmp_path / "gtfs", tmp_path / "out.zip")
    with zipfile.ZipFile(tmp_path / "out.zip") as archive:
        assert archive.namelist() == ["stops.txt"]

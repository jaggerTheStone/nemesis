"""Verified downloads with provenance (I0.7, docs/DATA.md « Provenance et versions »).

Every file is written next to a `provenance.json` that records where it came from,
when, under which licence, and how its integrity was checked. A file that does not
match its pinned SHA-256, or the MD5 published by the source, is deleted and the
import stops: an unverified file never reaches the database.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import time
import urllib.request
import zipfile
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from nemesis_pipelines.checksum import ChecksumMismatchError, sha256_file
from nemesis_pipelines.sources import Source

USER_AGENT = "nemesis-pipelines/0.0 (+https://github.com/jaggerTheStone/nemesis)"
_CHUNK = 1024 * 1024
# Fixed timestamp for archives built from repository files: same bytes on every run.
_ZIP_DATE = (2026, 1, 1, 0, 0, 0)

Opener = Callable[..., Any]


@dataclass(frozen=True)
class Provenance:
    source_id: str
    kind: str
    url: str
    file_name: str
    sha256: str
    size_bytes: int
    verified_by: str
    retrieved_at: str
    license: str
    usage: str
    is_fictional: bool
    attribution: str | None = None
    license_url: str | None = None
    md5: str | None = None
    last_modified: str | None = None

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, indent=2) + "\n"


@dataclass(frozen=True)
class Fetched:
    path: Path
    provenance: Provenance


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _request(url: str) -> urllib.request.Request:
    return urllib.request.Request(url, headers={"User-Agent": USER_AGENT})


def _retry(action: Callable[[], Any], attempts: int = 4, delay_s: float = 2.0) -> Any:
    """Retries network failures with exponential backoff (2, 4, 8 s)."""
    for attempt in range(attempts):
        try:
            return action()
        except OSError:
            if attempt == attempts - 1:
                raise
            time.sleep(delay_s * 2**attempt)
    raise AssertionError("unreachable")


def fetch_text(url: str, opener: Opener = urllib.request.urlopen, timeout: float = 60) -> str:
    def action() -> str:
        with opener(_request(url), timeout=timeout) as response:
            return response.read().decode("utf-8")

    return _retry(action)


def download_file(
    url: str, destination: Path, opener: Opener = urllib.request.urlopen, timeout: float = 120
) -> dict[str, Any]:
    """Streams `url` to `destination`; returns its size, SHA-256, MD5 and Last-Modified."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_name(destination.name + ".part")

    def action() -> dict[str, Any]:
        sha256, md5, size = hashlib.sha256(), hashlib.md5(usedforsecurity=False), 0
        with opener(_request(url), timeout=timeout) as response, partial.open("wb") as out:
            while chunk := response.read(_CHUNK):
                out.write(chunk)
                sha256.update(chunk)
                md5.update(chunk)
                size += len(chunk)
            last_modified = response.headers.get("Last-Modified")
        return {
            "sha256": sha256.hexdigest(),
            "md5": md5.hexdigest(),
            "size": size,
            "last_modified": last_modified,
        }

    try:
        result = _retry(action)
    except BaseException:
        partial.unlink(missing_ok=True)
        raise
    partial.replace(destination)
    return result


def parse_md5(text: str) -> str:
    """Reads a `md5sum` line (« <md5>  <file> »)."""
    token = text.strip().split()[0].lower() if text.strip() else ""
    if len(token) != 32 or any(c not in "0123456789abcdef" for c in token):
        raise ChecksumMismatchError(f"empreinte MD5 illisible : {text[:80]!r}")
    return token


def gtfs_zip(directory: Path, destination: Path) -> None:
    """Deterministic archive of a GTFS directory (sorted names, fixed dates)."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(directory.glob("*.txt")):
            info = zipfile.ZipInfo(path.name, date_time=_ZIP_DATE)
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, path.read_bytes())


def _provenance(source: Source, **values: Any) -> Provenance:
    return Provenance(
        source_id=source.id,
        kind=source.kind,
        license=source.license,
        usage=source.usage,
        is_fictional=source.is_fictional,
        attribution=source.attribution,
        license_url=source.license_url,
        **values,
    )


def _read_provenance(path: Path) -> Provenance | None:
    if not path.exists():
        return None
    return Provenance(**json.loads(path.read_text(encoding="utf-8")))


def fetch(
    source: Source,
    work_dir: Path,
    root: Path = Path("."),
    reuse: bool = True,
    opener: Opener = urllib.request.urlopen,
) -> Fetched:
    """Puts the verified file of `source` in `work_dir/sources/<id>/` with its provenance."""
    directory = work_dir / "sources" / source.id
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / source.target_name
    provenance_path = directory / "provenance.json"

    if source.local:
        assert source.path is not None
        origin = root / source.path
        if source.kind == "gtfs" and origin.is_dir():
            gtfs_zip(origin, target)
        else:
            shutil.copyfile(origin, target)
        provenance = _provenance(
            source,
            url=f"depot:{source.path}",
            file_name=target.name,
            sha256=sha256_file(target),
            size_bytes=target.stat().st_size,
            verified_by="fichier_du_depot",
            retrieved_at=_now(),
        )
        provenance_path.write_text(provenance.to_json(), encoding="utf-8")
        return Fetched(target, provenance)

    assert source.url is not None
    previous = _read_provenance(provenance_path)
    if source.sha256:
        if reuse and target.exists() and previous and sha256_file(target) == source.sha256:
            return Fetched(target, previous)
        result = download_file(source.url, target, opener)
        if result["sha256"] != source.sha256:
            target.unlink()
            raise ChecksumMismatchError(
                f"{source.id} : sha256 {result['sha256']} au lieu de {source.sha256} épinglé ;"
                " la source a changé : vérifier puis mettre à jour sources.toml"
            )
        verified_by, md5 = "sha256_epinglee", None
    else:
        assert source.md5_url is not None
        expected = parse_md5(fetch_text(source.md5_url, opener))
        if reuse and target.exists() and previous and previous.md5 == expected:
            return Fetched(target, previous)
        result = download_file(source.url, target, opener)
        if result["md5"] != expected:
            # The extract may have been republished during the download: one retry.
            expected = parse_md5(fetch_text(source.md5_url, opener))
            if result["md5"] != expected:
                result = download_file(source.url, target, opener)
            if result["md5"] != expected:
                target.unlink()
                raise ChecksumMismatchError(
                    f"{source.id} : md5 {result['md5']} différente de celle publiée ({expected})"
                )
        verified_by, md5 = "md5_publiee", expected

    provenance = _provenance(
        source,
        url=source.url,
        file_name=target.name,
        sha256=result["sha256"],
        size_bytes=result["size"],
        verified_by=verified_by,
        retrieved_at=_now(),
        md5=md5,
        last_modified=result["last_modified"],
    )
    provenance_path.write_text(provenance.to_json(), encoding="utf-8")
    return Fetched(target, provenance)

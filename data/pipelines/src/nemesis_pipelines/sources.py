"""Source manifest (data/pipelines/sources.toml): where data comes from, under which licence.

The manifest is the single place where a source URL, its checksum policy, its licence
and its permitted usage are declared (docs/DATA.md). Loading it validates every
entry: a source without a way to verify its file is refused (I0.7).
"""

from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

MANIFEST_PATH = Path("data/pipelines/sources.toml")
_ID = re.compile(r"^[a-z0-9_]+$")
_CITY = re.compile(r"^[a-z0-9-]+$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")

Kind = Literal["osm", "gtfs"]
Usage = Literal["produit", "evaluation"]


class ManifestError(ValueError):
    """Raised when sources.toml is inconsistent."""


@dataclass(frozen=True)
class Source:
    id: str
    kind: Kind
    name: str
    license: str
    usage: Usage
    is_fictional: bool = False
    url: str | None = None
    md5_url: str | None = None
    sha256: str | None = None
    path: str | None = None
    file_name: str | None = None
    page_url: str | None = None
    license_url: str | None = None
    attribution: str | None = None

    @property
    def local(self) -> bool:
        """True for files kept in the repository (fictional data)."""
        return self.path is not None

    @property
    def target_name(self) -> str:
        """Name of the downloaded file in the work directory."""
        if self.file_name:
            return self.file_name
        if self.url:
            return self.url.rsplit("/", 1)[-1].split("?", 1)[0]
        assert self.path is not None
        name = Path(self.path).name
        return f"{name}.zip" if self.kind == "gtfs" else name


@dataclass(frozen=True)
class City:
    code: str
    name: str
    timezone: str
    metric_srid: int
    bbox: tuple[float, float, float, float]
    is_fictional: bool = False


@dataclass(frozen=True)
class Profile:
    name: str
    city: str
    osm: str
    gtfs: str
    promote_places: bool


@dataclass(frozen=True)
class Manifest:
    sources: dict[str, Source]
    cities: dict[str, City]
    profiles: dict[str, Profile]
    tools: dict[str, str]

    def tool(self, name: str) -> str:
        try:
            return self.tools[name]
        except KeyError:
            raise ManifestError(f"outil non déclaré dans [tools] : {name}") from None

    def source(self, source_id: str) -> Source:
        try:
            return self.sources[source_id]
        except KeyError:
            raise ManifestError(f"source inconnue : {source_id}") from None

    def city(self, code: str) -> City:
        try:
            return self.cities[code]
        except KeyError:
            raise ManifestError(f"ville inconnue : {code}") from None

    def profile(self, name: str) -> Profile:
        try:
            return self.profiles[name]
        except KeyError:
            raise ManifestError(f"profil inconnu : {name}") from None


_SOURCE_KEYS = {
    "kind",
    "name",
    "license",
    "usage",
    "is_fictional",
    "url",
    "md5_url",
    "sha256",
    "path",
    "file_name",
    "page_url",
    "license_url",
    "attribution",
}


def _source(source_id: str, raw: dict[str, Any]) -> Source:
    where = f"sources.{source_id}"
    if not _ID.match(source_id):
        raise ManifestError(f"{where} : identifiant invalide (minuscules, chiffres, _)")
    unknown = set(raw) - _SOURCE_KEYS
    if unknown:
        raise ManifestError(f"{where} : clés inconnues {sorted(unknown)}")
    for key in ("kind", "name", "license", "usage"):
        if not raw.get(key):
            raise ManifestError(f"{where} : « {key} » est obligatoire")
    if raw["kind"] not in ("osm", "gtfs"):
        raise ManifestError(f"{where} : kind vaut osm ou gtfs")
    if raw["usage"] not in ("produit", "evaluation"):
        raise ManifestError(f"{where} : usage vaut produit ou evaluation")
    source = Source(id=source_id, **raw)
    if source.local == bool(source.url):
        raise ManifestError(f"{where} : il faut soit « url », soit « path »")
    if source.url:
        if not source.url.startswith("https://"):
            raise ManifestError(f"{where} : seules les URL https sont acceptées")
        if bool(source.sha256) == bool(source.md5_url):
            raise ManifestError(
                f"{where} : fichier non vérifiable ; épingler « sha256 » ou donner « md5_url »"
            )
        if source.sha256 and not _SHA256.match(source.sha256):
            raise ManifestError(f"{where} : sha256 doit faire 64 caractères hexadécimaux")
        if source.is_fictional:
            raise ManifestError(f"{where} : une source fictive est un fichier du dépôt")
        if not source.attribution:
            raise ManifestError(f"{where} : l'attribution exigée par la licence manque")
    elif not source.is_fictional:
        raise ManifestError(f"{where} : un fichier du dépôt ne peut être que fictif (H-007)")
    return source


def _city(code: str, raw: dict[str, Any]) -> City:
    where = f"cities.{code}"
    if not _CITY.match(code):
        raise ManifestError(f"{where} : code invalide")
    bbox = tuple(float(value) for value in raw.get("bbox", ()))
    if len(bbox) != 4 or not (bbox[0] < bbox[2] and bbox[1] < bbox[3]):
        raise ManifestError(f"{where} : bbox = [lon_min, lat_min, lon_max, lat_max]")
    return City(
        code=code,
        name=raw["name"],
        timezone=raw["timezone"],
        metric_srid=int(raw["metric_srid"]),
        bbox=(bbox[0], bbox[1], bbox[2], bbox[3]),
        is_fictional=bool(raw.get("is_fictional", False)),
    )


def parse_manifest(data: dict[str, Any]) -> Manifest:
    sources = {key: _source(key, value) for key, value in data.get("sources", {}).items()}
    cities = {key: _city(key, value) for key, value in data.get("cities", {}).items()}
    profiles = {}
    for name, raw in data.get("profiles", {}).items():
        profile = Profile(
            name=name,
            city=raw["city"],
            osm=raw["osm"],
            gtfs=raw["gtfs"],
            promote_places=bool(raw.get("promote_places", False)),
        )
        where = f"profiles.{name}"
        city = cities.get(profile.city)
        if city is None:
            raise ManifestError(f"{where} : ville inconnue {profile.city}")
        for kind, source_id in (("osm", profile.osm), ("gtfs", profile.gtfs)):
            source = sources.get(source_id)
            if source is None or source.kind != kind:
                raise ManifestError(f"{where} : {source_id} n'est pas une source {kind}")
            if source.is_fictional != city.is_fictional:
                raise ManifestError(f"{where} : {source_id} et {city.code} mêlent fictif et réel")
        profiles[name] = profile
    tools = {str(key): str(value) for key, value in data.get("tools", {}).items()}
    for name, image in tools.items():
        if "/" in image and "@sha256:" not in image:
            raise ManifestError(f"tools.{name} : image à épingler par empreinte (@sha256:…)")
    return Manifest(sources=sources, cities=cities, profiles=profiles, tools=tools)


def load_manifest(path: Path = MANIFEST_PATH) -> Manifest:
    with path.open("rb") as handle:
        return parse_manifest(tomllib.load(handle))

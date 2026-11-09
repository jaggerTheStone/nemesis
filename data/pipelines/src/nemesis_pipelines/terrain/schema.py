"""Field-data schemas: loading and integrity checks.

The TOML files in ``schemas/`` are the single source of truth for the field
datasets (I0.2): the validator, the CSV templates and the data dictionary are
all derived from them. Structure keys are English; column names and codes are
French because field staff type them.
"""

from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass, field
from importlib import resources
from typing import Any

FIELD_TYPES = {"text", "integer", "decimal", "date", "time", "code", "enum", "list"}
RULE_TYPES = {"all_or_none", "ordered", "required_if", "equals", "steps", "at_least_one"}
ENTRY_MODES = {"field", "office", "app"}

# Presentation order (dictionary, CLI): field collection first, then UX tests, then the
# « Éclaireurs » campaign (I0.12).
DATASET_ORDER = (
    "requetes",
    "trajets",
    "reponses",
    "participants",
    "observations",
    "icones",
    "gares",
    "releves_ligne",
    "arrets_releves",
    "prix",
    "comptages",
    "photos",
    "traces",
)

# Column accepted in every dataset (rule 1.3.1): fictional rows carry true.
FICTIONAL_COLUMN = "is_fictional"

_FIELD_KEYS = {
    "name",
    "label",
    "type",
    "required",
    "entry",
    "help",
    "vocabulary",
    "extra_values",
    "pattern",
    "min",
    "max",
    "max_length",
    "min_items",
    "distinct",
}
_SCHEMA_KEYS = {
    "name",
    "title",
    "purpose",
    "protocol",
    "forms",
    "key",
    "fields",
    "rules",
    "references",
}


class SchemaError(Exception):
    """Raised when a schema file is inconsistent."""


@dataclass(frozen=True)
class FieldSpec:
    name: str
    label: str
    type: str
    required: bool
    entry: str = "field"
    help: str = ""
    values: dict[str, str] = field(default_factory=dict)
    vocabulary: str | None = None
    pattern: re.Pattern[str] | None = None
    min: float | None = None
    max: float | None = None
    max_length: int | None = None
    min_items: int | None = None
    distinct: bool = False


@dataclass(frozen=True)
class Reference:
    fields: tuple[str, ...]
    target: str
    target_fields: tuple[str, ...]


@dataclass(frozen=True)
class Schema:
    name: str
    title: str
    purpose: str
    protocol: str
    forms: tuple[str, ...]
    key: tuple[str, ...]
    fields: tuple[FieldSpec, ...]
    rules: tuple[dict[str, Any], ...]
    references: tuple[Reference, ...]

    @property
    def columns(self) -> list[str]:
        return [spec.name for spec in self.fields]

    def field(self, name: str) -> FieldSpec:
        for spec in self.fields:
            if spec.name == name:
                return spec
        raise KeyError(name)


def _read_toml(filename: str) -> dict[str, Any]:
    text = (
        resources.files("nemesis_pipelines.terrain")
        .joinpath("schemas", filename)
        .read_text(encoding="utf-8")
    )
    return tomllib.loads(text)


def load_vocabularies() -> dict[str, dict[str, str]]:
    """Returns the shared vocabularies: name -> {code: label}."""
    return _read_toml("referentiels.toml")


def _build_field(
    schema_name: str, raw: dict[str, Any], vocabularies: dict[str, dict[str, str]]
) -> FieldSpec:
    where = f"{schema_name}.{raw.get('name', '?')}"
    unknown = set(raw) - _FIELD_KEYS
    if unknown:
        raise SchemaError(f"{where}: unknown keys {sorted(unknown)}")
    if raw.get("type") not in FIELD_TYPES:
        raise SchemaError(f"{where}: unknown type {raw.get('type')!r}")
    entry = raw.get("entry", "field")
    if entry not in ENTRY_MODES:
        raise SchemaError(f"{where}: unknown entry mode {entry!r}")

    values: dict[str, str] = {}
    vocabulary = raw.get("vocabulary")
    if vocabulary is not None:
        if vocabulary not in vocabularies:
            raise SchemaError(f"{where}: unknown vocabulary {vocabulary!r}")
        values = {**vocabularies[vocabulary], **raw.get("extra_values", {})}
    if raw["type"] == "enum" and not values:
        raise SchemaError(f"{where}: enum fields need a vocabulary")
    if raw["type"] == "code" and "pattern" not in raw:
        raise SchemaError(f"{where}: code fields need a pattern")
    if raw["type"] == "list" and not values and "pattern" not in raw:
        raise SchemaError(f"{where}: list fields need a vocabulary or a pattern")

    return FieldSpec(
        name=raw["name"],
        label=raw["label"],
        type=raw["type"],
        required=bool(raw["required"]),
        entry=entry,
        help=raw.get("help", ""),
        values=values,
        vocabulary=vocabulary,
        pattern=re.compile(raw["pattern"]) if "pattern" in raw else None,
        min=raw.get("min"),
        max=raw.get("max"),
        max_length=raw.get("max_length"),
        min_items=raw.get("min_items"),
        distinct=bool(raw.get("distinct", False)),
    )


def _check_rule(schema: Schema, rule: dict[str, Any]) -> None:
    rule_type = rule.get("type")
    if rule_type not in RULE_TYPES:
        raise SchemaError(f"{schema.name}: unknown rule type {rule_type!r}")
    names = set(schema.columns)
    referenced: list[str] = list(rule.get("fields", []))
    if "field" in rule:
        referenced.append(rule["field"])
    if "when" in rule:
        referenced.append(rule["when"]["field"])
    if rule_type == "steps":
        for index in range(1, rule["count"] + 1):
            for suffix in [*rule["required_fields"], *rule.get("optional_fields", [])]:
                referenced.append(f"{rule['prefix']}{index}_{suffix}")
    missing = [name for name in referenced if name not in names]
    if missing:
        raise SchemaError(f"{schema.name}: rule {rule_type} uses unknown fields {missing}")


def load_schemas() -> dict[str, Schema]:
    """Loads and cross-checks every dataset schema, keyed by dataset name."""
    vocabularies = load_vocabularies()
    schemas: dict[str, Schema] = {}
    directory = resources.files("nemesis_pipelines.terrain").joinpath("schemas")
    for entry in sorted(directory.iterdir(), key=lambda item: item.name):
        if not entry.name.endswith(".toml") or entry.name == "referentiels.toml":
            continue
        raw = tomllib.loads(entry.read_text(encoding="utf-8"))
        unknown = set(raw) - _SCHEMA_KEYS
        if unknown:
            raise SchemaError(f"{entry.name}: unknown keys {sorted(unknown)}")
        fields = tuple(_build_field(raw["name"], item, vocabularies) for item in raw["fields"])
        schema = Schema(
            name=raw["name"],
            title=raw["title"],
            purpose=raw["purpose"],
            protocol=raw["protocol"],
            forms=tuple(raw["forms"]),
            key=tuple(raw["key"]),
            fields=fields,
            rules=tuple(raw.get("rules", [])),
            references=tuple(
                Reference(tuple(ref["fields"]), ref["target"], tuple(ref["target_fields"]))
                for ref in raw.get("references", [])
            ),
        )
        if entry.name != f"{schema.name}.toml":
            raise SchemaError(f"{entry.name}: name {schema.name!r} does not match the file name")
        if len(set(schema.columns)) != len(schema.columns):
            raise SchemaError(f"{schema.name}: duplicate field names")
        if FICTIONAL_COLUMN in schema.columns:
            raise SchemaError(f"{schema.name}: {FICTIONAL_COLUMN} is implicit, do not declare it")
        for key_field in schema.key:
            if key_field not in schema.columns:
                raise SchemaError(f"{schema.name}: key field {key_field!r} is not declared")
        for rule in schema.rules:
            _check_rule(schema, rule)
        schemas[schema.name] = schema

    for schema in schemas.values():
        for reference in schema.references:
            target = schemas.get(reference.target)
            if target is None or tuple(reference.target_fields) != target.key:
                raise SchemaError(
                    f"{schema.name}: reference must target the key of {reference.target}"
                )
        for rule in schema.rules:
            if rule["type"] == "at_least_one" and rule["within"] not in schemas:
                raise SchemaError(f"{schema.name}: unknown dataset {rule['within']!r}")
    rank = {name: index for index, name in enumerate(DATASET_ORDER)}
    return dict(sorted(schemas.items(), key=lambda item: (rank.get(item[0], len(rank)), item[0])))

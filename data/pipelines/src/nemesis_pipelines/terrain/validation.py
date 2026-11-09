"""Validation of field CSV files against their schemas.

Messages are in French: they are read by the people who enter field data.
A directory holding CSV files is one dataset set ("jeu"): references between
files are resolved inside that directory only.
"""

from __future__ import annotations

import csv
import difflib
import io
import re
import unicodedata
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from nemesis_pipelines.terrain.schema import FICTIONAL_COLUMN, FieldSpec, Schema

LIST_SEPARATOR = "+"
_INTEGER = re.compile(r"-?[0-9]+")
_DECIMAL = re.compile(r"-?[0-9]+(\.[0-9]+)?")
_TIME = re.compile(r"([01][0-9]|2[0-3]):[0-5][0-9]")
_FRENCH_DATE = re.compile(r"([0-9]{1,2})[/.-]([0-9]{1,2})[/.-]([0-9]{4})")
_FRENCH_TIME = re.compile(r"([0-9]{1,2})\s*[hH:]\s*([0-9]{2})?")


@dataclass(frozen=True)
class Issue:
    """One validation error, located as precisely as possible."""

    file: str
    line: int | None
    column: str | None
    message: str

    def __str__(self) -> str:
        location = self.file if self.line is None else f"{self.file}:{self.line}"
        column = f" [{self.column}]" if self.column else ""
        return f"{location}{column} : {self.message}"


@dataclass
class Row:
    file: str
    line: int
    values: dict[str, str]


@dataclass
class Dataset:
    schema: Schema
    files: list[str] = field(default_factory=list)
    rows: list[Row] = field(default_factory=list)


@dataclass
class DirectoryReport:
    directory: Path
    datasets: dict[str, Dataset]
    issues: list[Issue]


def normalise(text: str) -> str:
    """Lowercase, accent-free, underscore-separated form used for suggestions."""
    decomposed = unicodedata.normalize("NFKD", text)
    without_accents = "".join(char for char in decomposed if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", "_", without_accents.lower()).strip("_")


def suggest_code(value: str, values: dict[str, str]) -> str | None:
    """Returns the code the user probably meant, from its label or a close spelling."""
    wanted = normalise(value)
    for code, label in values.items():
        if wanted in (normalise(code), normalise(label)):
            return code
    close = difflib.get_close_matches(wanted, list(values), n=1, cutoff=0.75)
    return close[0] if close else None


def dataset_for(filename: str, schemas: dict[str, Schema]) -> Schema | None:
    """Maps `requetes.csv` or `requetes-2026-11-20-E01.csv` to the `requetes` schema."""
    stem = Path(filename).stem
    for name, schema in schemas.items():
        if stem == name or stem.startswith((f"{name}-", f"{name}_")):
            return schema
    return None


def read_csv(path: Path) -> tuple[list[str], list[tuple[int, list[str]]]]:
    """Reads a UTF-8 CSV (with or without BOM), delimited by ';' or ','."""
    raw = path.read_bytes()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise ValueError(
            "le fichier n'est pas en UTF-8 : l'enregistrer en « CSV UTF-8 » dans le tableur"
        ) from error
    first_line = text.split("\n", 1)[0]
    delimiter = ";" if first_line.count(";") >= first_line.count(",") else ","
    reader = csv.reader(io.StringIO(text, newline=""), delimiter=delimiter)
    rows = list(reader)
    if not rows:
        raise ValueError("le fichier est vide (il faut au moins la ligne d'en-tête)")
    header = [cell.strip() for cell in rows[0]]
    # Physical line numbers are approximated by record index (1 = header); quoted
    # cells spanning several lines are rare in field data.
    body = [(index, cells) for index, cells in enumerate(rows[1:], start=2)]
    return header, body


def _check_value(spec: FieldSpec, value: str) -> str | None:
    """Returns an error message for a non-empty value, or None if it is valid."""
    if spec.type == "text":
        if spec.max_length is not None and len(value) > spec.max_length:
            return f"texte trop long ({len(value)} caractères, maximum {spec.max_length})"
        return None

    if spec.type == "integer":
        if not _INTEGER.fullmatch(value):
            return f"« {value} » n'est pas un nombre entier"
        return _check_range(spec, int(value))

    if spec.type == "decimal":
        candidate = value.replace(",", ".") if value.count(",") == 1 else value
        if not _DECIMAL.fullmatch(candidate):
            return f"« {value} » n'est pas un nombre décimal"
        return _check_range(spec, float(candidate))

    if spec.type == "date":
        try:
            date.fromisoformat(value)
        except ValueError:
            match = _FRENCH_DATE.fullmatch(value)
            if match:
                day, month, year = match.groups()
                iso = f"{year}-{int(month):02d}-{int(day):02d}"
                return f"date au format AAAA-MM-JJ attendue : écrire {iso}"
            return f"« {value} » n'est pas une date valide (format AAAA-MM-JJ)"
        if len(value) != 10:
            return f"« {value} » : format AAAA-MM-JJ attendu"
        return None

    if spec.type == "time":
        if _TIME.fullmatch(value):
            return None
        match = _FRENCH_TIME.fullmatch(value)
        if match and int(match.group(1)) < 24:
            minutes = match.group(2) or "00"
            return f"heure au format HH:MM attendue : écrire {int(match.group(1)):02d}:{minutes}"
        return f"« {value} » n'est pas une heure valide (format HH:MM)"

    if spec.type == "code":
        assert spec.pattern is not None
        if not spec.pattern.fullmatch(value):
            return f"« {value} » ne respecte pas le format {spec.pattern.pattern}"
        return None

    if spec.type == "enum":
        return _check_code(spec, value)

    if spec.type == "list":
        items = [item.strip() for item in value.split(LIST_SEPARATOR)]
        if any(not item for item in items):
            return f"élément vide dans la liste « {value} » (séparateur « {LIST_SEPARATOR} »)"
        for item in items:
            if spec.values:
                message = _check_code(spec, item)
            else:
                assert spec.pattern is not None
                message = (
                    None
                    if spec.pattern.fullmatch(item)
                    else f"« {item} » ne respecte pas le format {spec.pattern.pattern}"
                )
            if message:
                return message
        if spec.distinct and len(set(items)) != len(items):
            return "chaque élément de la liste doit être différent"
        if spec.min_items is not None and len(items) < spec.min_items:
            return f"au moins {spec.min_items} éléments attendus, séparés par « {LIST_SEPARATOR} »"
        return None

    raise AssertionError(spec.type)


def _check_range(spec: FieldSpec, number: float) -> str | None:
    if spec.min is not None and number < spec.min:
        return f"valeur {number:g} inférieure au minimum {spec.min:g}"
    if spec.max is not None and number > spec.max:
        return f"valeur {number:g} supérieure au maximum {spec.max:g}"
    return None


def _check_code(spec: FieldSpec, value: str) -> str | None:
    if value in spec.values:
        return None
    suggestion = suggest_code(value, spec.values)
    hint = f" ; vouliez-vous « {suggestion} » ?" if suggestion else ""
    return f"valeur « {value} » inconnue{hint} (voir le dictionnaire des champs)"


def _check_header(schema: Schema, file: str, header: list[str]) -> list[Issue]:
    issues: list[Issue] = []
    allowed = {*schema.columns, FICTIONAL_COLUMN}
    seen: set[str] = set()
    for column in header:
        if column in seen:
            issues.append(Issue(file, 1, column, "colonne en double"))
        seen.add(column)
        if column not in allowed:
            close = difflib.get_close_matches(column, sorted(allowed), n=1, cutoff=0.7)
            hint = f" ; vouliez-vous « {close[0]} » ?" if close else ""
            issues.append(Issue(file, 1, column, f"colonne inconnue{hint}"))
    for spec in schema.fields:
        if spec.required and spec.name not in seen:
            issues.append(Issue(file, 1, spec.name, "colonne obligatoire absente"))
    return issues


def _check_row(schema: Schema, row: Row, fictional: bool) -> list[Issue]:
    issues: list[Issue] = []
    values = row.values

    def issue(column: str | None, message: str) -> None:
        issues.append(Issue(row.file, row.line, column, message))

    for spec in schema.fields:
        value = values.get(spec.name, "")
        if not value:
            if spec.required:
                issue(spec.name, "valeur obligatoire manquante")
            continue
        message = _check_value(spec, value)
        if message:
            issue(spec.name, message)

    flag = values.get(FICTIONAL_COLUMN, "")
    if flag not in ("", "true", "false"):
        issue(FICTIONAL_COLUMN, "valeur attendue : true ou false")
    elif fictional and flag != "true":
        issue(FICTIONAL_COLUMN, "jeu fictif : chaque ligne doit porter is_fictional = true")
    elif not fictional and flag == "true":
        issue(
            FICTIONAL_COLUMN,
            "ligne fictive dans un jeu réel : la déplacer dans data/fixtures_fictives",
        )

    for rule in schema.rules:
        rule_type = rule["type"]
        if rule_type == "all_or_none":
            filled = [name for name in rule["fields"] if values.get(name)]
            if filled and len(filled) != len(rule["fields"]):
                issue(None, f"renseigner ensemble ou laisser vides : {', '.join(rule['fields'])}")
        elif rule_type == "ordered":
            low_name, high_name = rule["fields"]
            low, high = values.get(low_name, ""), values.get(high_name, "")
            numbers = _DECIMAL.fullmatch(low) and _DECIMAL.fullmatch(high)
            # Times HH:MM of the same day compare as text.
            times = _TIME.fullmatch(low) and _TIME.fullmatch(high)
            if (numbers and float(low) > float(high)) or (times and low > high):
                issue(high_name, f"{high_name} doit être supérieur ou égal à {low_name}")
        elif rule_type == "required_if":
            when = rule["when"]
            if values.get(when["field"]) == when["value"]:
                for name in rule["fields"]:
                    if not values.get(name):
                        issue(name, f"obligatoire quand {when['field']} = {when['value']}")
        elif rule_type == "equals":
            value = values.get(rule["field"], "")
            if value and value != rule["value"]:
                issue(rule["field"], rule.get("message", f"valeur attendue : {rule['value']}"))
        elif rule_type == "steps":
            issues.extend(_check_steps(rule, row))
    return issues


def _check_steps(rule: dict, row: Row) -> list[Issue]:
    issues: list[Issue] = []
    prefix, count = rule["prefix"], rule["count"]
    suffixes = [*rule["required_fields"], *rule.get("optional_fields", [])]
    present = []
    for index in range(1, count + 1):
        names = [f"{prefix}{index}_{suffix}" for suffix in suffixes]
        is_present = any(row.values.get(name) for name in names)
        present.append(is_present)
        if is_present:
            for suffix in rule["required_fields"]:
                name = f"{prefix}{index}_{suffix}"
                if not row.values.get(name):
                    issues.append(Issue(row.file, row.line, name, f"étape {index} incomplète"))
            if index > 1 and not present[index - 2]:
                issues.append(
                    Issue(
                        row.file,
                        row.line,
                        names[0],
                        f"étape {index} remplie sans l'étape {index - 1}",
                    )
                )
    if not present[0]:
        issues.append(
            Issue(row.file, row.line, f"{prefix}1_mode", "au moins une étape en véhicule attendue")
        )
    return issues


def _key_of(row: Row, names: tuple[str, ...] | list[str]) -> tuple[str, ...]:
    return tuple(row.values.get(name, "") for name in names)


def _check_dataset(dataset: Dataset) -> list[Issue]:
    issues: list[Issue] = []
    seen: dict[tuple[str, ...], Row] = {}
    for row in dataset.rows:
        key = _key_of(row, dataset.schema.key)
        if not all(key):
            continue
        if key in seen:
            first = seen[key]
            issues.append(
                Issue(
                    row.file,
                    row.line,
                    ", ".join(dataset.schema.key),
                    f"identifiant {' / '.join(key)} déjà utilisé ({first.file}:{first.line})",
                )
            )
        else:
            seen[key] = row
    return issues


def _check_links(datasets: dict[str, Dataset]) -> list[Issue]:
    issues: list[Issue] = []
    for dataset in datasets.values():
        for reference in dataset.schema.references:
            target = datasets.get(reference.target)
            if target is None:
                issues.append(
                    Issue(
                        dataset.files[0],
                        None,
                        None,
                        f"fichier {reference.target}.csv attendu dans le même dossier",
                    )
                )
                continue
            known = {_key_of(row, reference.target_fields) for row in target.rows}
            for row in dataset.rows:
                key = _key_of(row, reference.fields)
                if all(key) and key not in known:
                    issues.append(
                        Issue(
                            row.file,
                            row.line,
                            ", ".join(reference.fields),
                            f"{' / '.join(key)} absent de {reference.target}",
                        )
                    )
        for rule in dataset.schema.rules:
            if rule["type"] != "at_least_one":
                continue
            within = datasets.get(rule["within"])
            wanted = rule.get("filter")
            matches: set[tuple[str, ...]] = set()
            if within is not None:
                for row in within.rows:
                    if wanted is None or row.values.get(wanted["field"]) == wanted["value"]:
                        matches.add(_key_of(row, rule["target_fields"]))
            for row in dataset.rows:
                key = _key_of(row, rule["fields"])
                if all(key) and key not in matches:
                    issues.append(Issue(row.file, row.line, None, rule["message"]))
    return issues


def validate_directory(
    directory: Path, schemas: dict[str, Schema], fictional: bool
) -> DirectoryReport:
    """Validates every CSV file directly inside `directory` as one dataset set."""
    datasets: dict[str, Dataset] = {}
    issues: list[Issue] = []
    for path in sorted(directory.glob("*.csv")):
        file = str(path)
        schema = dataset_for(path.name, schemas)
        if schema is None:
            known = ", ".join(f"{name}.csv" for name in schemas)
            issues.append(Issue(file, None, None, f"nom de fichier inconnu (attendus : {known})"))
            continue
        try:
            header, body = read_csv(path)
        except ValueError as error:
            issues.append(Issue(file, None, None, str(error)))
            continue
        header_issues = _check_header(schema, file, header)
        issues.extend(header_issues)
        dataset = datasets.setdefault(schema.name, Dataset(schema))
        dataset.files.append(file)
        if header_issues:
            continue
        for line, cells in body:
            values = {column: cell.strip() for column, cell in zip(header, cells, strict=False)}
            if not any(values.values()):
                continue
            if len(cells) > len(header):
                issues.append(Issue(file, line, None, "plus de cellules que de colonnes"))
            row = Row(file, line, values)
            dataset.rows.append(row)
            issues.extend(_check_row(schema, row, fictional))
    for dataset in datasets.values():
        issues.extend(_check_dataset(dataset))
    issues.extend(_check_links(datasets))
    return DirectoryReport(directory, datasets, issues)


def validate_tree(root: Path, schemas: dict[str, Schema], fictional: bool) -> list[DirectoryReport]:
    """Validates `root` and each of its subdirectories that contains CSV files."""
    directories = sorted({path.parent for path in root.rglob("*.csv")})
    return [validate_directory(directory, schemas, fictional) for directory in directories]


def group_by_file(issues: list[Issue]) -> dict[str, list[Issue]]:
    grouped: dict[str, list[Issue]] = defaultdict(list)
    for issue in issues:
        grouped[issue.file].append(issue)
    return grouped

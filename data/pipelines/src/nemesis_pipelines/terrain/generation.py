"""Files derived from the schemas: CSV templates and the data dictionary."""

from __future__ import annotations

from pathlib import Path

from nemesis_pipelines.terrain.schema import FICTIONAL_COLUMN, FieldSpec, Schema
from nemesis_pipelines.terrain.validation import LIST_SEPARATOR

TEMPLATES_DIR = Path("data/terrain/modeles")
DICTIONARY_PATH = Path("docs/TERRAIN/DICTIONNAIRE.md")

# Templates open directly in a French-locale spreadsheet: ';' and a UTF-8 BOM.
TEMPLATE_DELIMITER = ";"
_BOM = "\ufeff"

_TYPE_LABELS = {
    "text": "texte",
    "integer": "nombre entier",
    "decimal": "nombre décimal",
    "date": "date AAAA-MM-JJ",
    "time": "heure HH:MM",
    "code": "code",
    "enum": "valeur de liste",
    "list": f"liste séparée par « {LIST_SEPARATOR} »",
}


def template_csv(schema: Schema) -> str:
    """Header-only CSV template for one dataset."""
    return _BOM + TEMPLATE_DELIMITER.join(schema.columns) + "\n"


def _constraints(spec: FieldSpec, vocabularies: dict[str, dict[str, str]]) -> str:
    parts: list[str] = []
    if spec.pattern is not None:
        parts.append(f"format `{spec.pattern.pattern}`")
    if spec.vocabulary:
        parts.append(f"codes : [{spec.vocabulary}](#referentiel-{spec.vocabulary})")
        extra = [code for code in spec.values if code not in vocabularies[spec.vocabulary]]
        if extra:
            parts.append("ou " + ", ".join(f"`{code}`" for code in extra))
    if spec.min is not None or spec.max is not None:
        parts.append(f"de {spec.min:g} à {spec.max:g}")
    if spec.max_length is not None:
        parts.append(f"{spec.max_length} caractères au plus")
    if spec.min_items:
        parts.append(f"au moins {spec.min_items} éléments")
    if spec.distinct:
        parts.append("éléments distincts")
    return " ; ".join(parts)


def _cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


def _rule_text(rule: dict) -> str:
    rule_type = rule["type"]
    if rule_type == "all_or_none":
        return (
            "Renseigner ensemble ou laisser vides : "
            + ", ".join(f"`{n}`" for n in rule["fields"])
            + "."
        )
    if rule_type == "ordered":
        low, high = rule["fields"]
        return f"`{low}` ≤ `{high}`."
    if rule_type == "required_if":
        names = ", ".join(f"`{n}`" for n in rule["fields"])
        when = rule["when"]
        return f"{names} obligatoires quand `{when['field']}` = `{when['value']}`."
    if rule_type == "equals":
        return f"`{rule['field']}` doit valoir `{rule['value']}` : {rule.get('message', '')}."
    if rule_type == "steps":
        required = ", ".join(rule["required_fields"])
        return (
            f"Étapes `{rule['prefix']}1` à `{rule['prefix']}{rule['count']}` : "
            "la première est obligatoire, elles se suivent sans trou, "
            f"et chaque étape remplie a {required}."
        )
    if rule_type == "at_least_one":
        return rule["message"][0].upper() + rule["message"][1:] + "."
    raise AssertionError(rule_type)


_COMMON_RULES = (
    "- CSV en UTF-8, séparateur « ; » (celui des modèles) ou « , ».",
    "- Saisir les **codes** (sans accent), jamais les libellés ; "
    "le validateur propose le bon code en cas d'erreur.",
    f"- Plusieurs valeurs dans une cellule : séparées par « {LIST_SEPARATOR} ».",
    "- Dates au format AAAA-MM-JJ, heures au format HH:MM.",
    f"- Colonne facultative `{FICTIONAL_COLUMN}` : `true` uniquement dans "
    "`data/fixtures_fictives`.",
    "- Un fichier par jeu et par lot est permis : `requetes-2026-11-20-E01.csv` "
    "appartient au jeu `requetes`.",
    "- Colonne « Saisie » : *terrain* = noté sur la fiche papier ; *bureau* = ajouté à la saisie.",
)


def dictionary_markdown(schemas: dict[str, Schema], vocabularies: dict[str, dict[str, str]]) -> str:
    """Human-readable dictionary of every field dataset, generated from the schemas."""
    lines = [
        "# Dictionnaire des données de terrain",
        "",
        "<!-- Fichier généré par `uv run nemesis-terrain generer` à partir des schémas de",
        "     data/pipelines/src/nemesis_pipelines/terrain/schemas/ : "
        "ne pas le modifier à la main. -->",
        "",
        "Règles communes à tous les fichiers :",
        "",
        *_COMMON_RULES,
        "",
        "Vérification : `uv run nemesis-terrain valider data/terrain/collecte`.",
        "",
    ]
    for schema in schemas.values():
        lines += [
            f"## {schema.title} (`{schema.name}.csv`)",
            "",
            schema.purpose,
            "",
            f"- Protocole : [{Path(schema.protocol).name}](../../{schema.protocol})",
            "- Fiches papier : "
            + (
                ", ".join(f"[{Path(form).name}](../../{form})" for form in schema.forms)
                or "aucune, données produites par l'appli en mode relevé"
            ),
            f"- Modèle : [{schema.name}.csv](../../{TEMPLATES_DIR / (schema.name + '.csv')})",
            f"- Identifiant unique : {' + '.join(f'`{name}`' for name in schema.key)}",
        ]
        for reference in schema.references:
            fields = " + ".join(f"`{name}`" for name in reference.fields)
            lines.append(
                f"- {fields} doit exister dans `{reference.target}.csv`, dans le même dossier"
            )
        lines += [
            "",
            "| Colonne | Libellé | Type | Obligatoire | Saisie | Contraintes | Aide |",
            "|---------|---------|------|-------------|--------|-------------|------|",
        ]
        for spec in schema.fields:
            required = "oui" if spec.required else "non"
            entry = {"office": "bureau", "app": "appli"}.get(spec.entry, "terrain")
            lines.append(
                f"| `{spec.name}` | {_cell(spec.label)} | {_TYPE_LABELS[spec.type]} | "
                f"{required} | {entry} | "
                f"{_cell(_constraints(spec, vocabularies))} | {_cell(spec.help)} |"
            )
        if schema.rules:
            lines += ["", "Règles :", ""]
            lines += [f"- {_rule_text(rule)}" for rule in schema.rules]
        lines.append("")

    lines += ["## Référentiels", ""]
    for name, values in vocabularies.items():
        lines += [
            f'<a id="referentiel-{name}"></a>',
            "",
            f"### {name}",
            "",
            "| Code | Libellé |",
            "|------|---------|",
        ]
        lines += [f"| `{code}` | {_cell(label)} |" for code, label in values.items()]
        lines.append("")
    return "\n".join(lines)


def generated_files(
    schemas: dict[str, Schema], vocabularies: dict[str, dict[str, str]]
) -> dict[Path, str]:
    """Every derived file, keyed by path relative to the repository root."""
    files = {
        TEMPLATES_DIR / f"{name}.csv": template_csv(schema) for name, schema in schemas.items()
    }
    files[DICTIONARY_PATH] = dictionary_markdown(schemas, vocabularies)
    return files

"""BDA schema management."""

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

from documentai_api.config.constants import BDA_PROJECT_KEY_ALL, DictionaryBlueprintField
from documentai_api.config.env import get_aws_config
from documentai_api.logging import get_logger
from documentai_api.services.bda import get_blueprint, get_data_automation_project

logger = get_logger(__name__)

SCHEMAS_FILE = Path(__file__).resolve().parent.parent / "config" / "blueprint_schemas.json"


@dataclass
class SchemaField:
    name: str
    type: str
    description: str = ""


@dataclass
class DocumentSchema:
    document_type: str
    description: str
    fields: list[SchemaField] = field(default_factory=list)
    category: str = ""


def fetch_schemas_from_bda(
    on_category: Callable[[str, dict[str, DocumentSchema]], None] | None = None,
) -> dict[str, DocumentSchema]:
    """Fetch schemas from all BDA category projects.

    Only used offline, by cli/pull_blueprint_schemas.py, to build the static
    file get_all_schemas() reads at runtime - see get_all_schemas() docstring.

    on_category, if given, is called after each category's projects are fetched,
    with the category name and the schemas fetched for it (empty on failure) -
    lets the CLI report progress without duplicating the "all" skip logic below.
    """
    logger.info("Fetching schemas from BDA")

    project_arns = get_aws_config().get_bda_project_arns()

    # "all" is a superset of every category project's blueprints, so it's
    # skipped here - the union of the category projects covers all blueprints
    # without creating duplicate entries
    categories = {c: arn for c, arn in project_arns.items() if c != BDA_PROJECT_KEY_ALL}

    schemas: dict[str, DocumentSchema] = {}
    for category, project_arn in categories.items():
        category_schemas = _fetch_project_schemas(category, project_arn)
        schemas.update(category_schemas)
        if on_category:
            on_category(category, category_schemas)

    logger.info(f"Fetched {len(schemas)} schemas from {len(project_arns)} BDA projects")
    return schemas


def _fetch_project_schemas(category: str, project_arn: str) -> dict[str, DocumentSchema]:
    """Fetch blueprint schemas from one BDA project, tagged with `category`."""
    schemas: dict[str, DocumentSchema] = {}
    try:
        project_response = get_data_automation_project(project_arn)
        blueprints = (
            project_response.get("project", {})
            .get("customOutputConfiguration", {})
            .get("blueprints", [])
        )

        for blueprint_config in blueprints:
            blueprint_arn = blueprint_config.get("blueprintArn")
            if not blueprint_arn:
                continue

            blueprint_response = get_blueprint(blueprint_arn)
            blueprint = blueprint_response.get("blueprint", {})
            schema_str = blueprint.get("schema", "{}")
            schema = json.loads(schema_str)
            document_type = schema.get("class", blueprint.get("blueprintName", "Unknown"))

            schemas[document_type] = DocumentSchema(
                document_type=document_type,
                description=schema.get("description", blueprint.get("description", "")),
                fields=extract_fields(schema),
                category=category,
            )

    except Exception as e:
        logger.error(f"Failed to fetch schemas from BDA project {category}: {e}")

    return schemas


def extract_fields(schema: dict[str, Any]) -> list[SchemaField]:
    """Extract field list from schema."""
    fields: list[SchemaField] = []
    properties = schema.get("properties", {})
    definitions = schema.get("definitions", {})

    for field_name, field_spec in properties.items():
        if "$ref" in field_spec:
            ref_name = field_spec["$ref"].split("/")[-1]
            nested_def = definitions.get(ref_name, {})
            nested_props = nested_def.get("properties", {})

            for nested_field, nested_spec in nested_props.items():
                full_name = f"{field_name}.{nested_field}"
                fields.append(
                    SchemaField(
                        name=full_name,
                        type=nested_spec.get("type", "string"),
                        description=nested_spec.get("instruction", ""),
                    )
                )
        elif field_spec.get("type") == "array":
            items = field_spec.get("items", {})
            if "$ref" in items:
                ref_name = items["$ref"].split("/")[-1]
                nested_def = definitions.get(ref_name, {})
                nested_props = nested_def.get("properties", {})

                for nested_field, nested_spec in nested_props.items():
                    full_name = f"{field_name}.{nested_field}"
                    fields.append(
                        SchemaField(
                            name=full_name,
                            type=nested_spec.get("type", "string"),
                            description=nested_spec.get("instruction", ""),
                        )
                    )
            else:
                fields.append(
                    SchemaField(
                        name=field_name,
                        type="array",
                        description=field_spec.get("instruction", ""),
                    )
                )
        else:
            fields.append(
                SchemaField(
                    name=field_name,
                    type=field_spec.get("type", "string"),
                    description=field_spec.get("instruction", ""),
                )
            )

    return fields


@lru_cache(maxsize=1)
def get_all_schemas() -> dict[str, DocumentSchema]:
    """Get all document schemas from the preloaded static file.

    Blueprint schemas rarely change, and calling BDA's GetDataAutomationProject/
    GetBlueprint at request time throttles under load - see cli/pull_blueprint_schemas.py,
    which fetches them from BDA offline and writes the static file this reads.
    Re-run that CLI and redeploy whenever blueprints change (e.g. a new document type,
    or an edited custom blueprint) - this doesn't apply to tenant-authored blueprints,
    which are fetched dynamically instead.
    """
    if not SCHEMAS_FILE.exists():
        logger.warning(f"Blueprint schemas file not found: {SCHEMAS_FILE}")
        return {}

    raw = json.loads(SCHEMAS_FILE.read_text())
    return {
        doc_type: DocumentSchema(
            document_type=entry["document_type"],
            description=entry["description"],
            fields=[SchemaField(**f) for f in entry["fields"]],
            category=entry["category"],
        )
        for doc_type, entry in raw.items()
    }


def get_document_schema(document_type: str) -> DocumentSchema | None:
    """Get schema for specific document type."""
    schemas = get_all_schemas()
    return schemas.get(document_type)


def get_all_fields() -> list[dict[str, Any]]:
    schemas = get_all_schemas()
    data: list[dict[str, Any]] = []
    for doc_type, schema in schemas.items():
        data.extend(
            {
                DictionaryBlueprintField.DOCUMENT_TYPE: doc_type,
                DictionaryBlueprintField.NAME: f.name,
                DictionaryBlueprintField.TYPE: f.type,
                DictionaryBlueprintField.DESCRIPTION: f.description,
            }
            for f in schema.fields
        )

    data.sort(key=lambda f: f[DictionaryBlueprintField.DOCUMENT_TYPE])
    return data

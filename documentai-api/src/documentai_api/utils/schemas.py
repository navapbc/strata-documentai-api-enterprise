"""BDA schema management."""

import json
from typing import Any, cast

from documentai_api.config.constants import (
    Cache,
    DictionaryBlueprintField,
    DictionaryBlueprintSchema,
)
from documentai_api.config.env import EnvVars, get_required_env
from documentai_api.logging import get_logger
from documentai_api.services.bda import get_blueprint, get_data_automation_project
from documentai_api.utils.cache import get_cache

logger = get_logger(__name__)


def _fetch_schemas_from_bda() -> dict[str, Any]:
    """Fetch schemas from all BDA projects."""
    import os

    logger.info("Fetching schemas from BDA")

    # Try multi-project map first, fall back to single project ARN
    project_arns_json = os.getenv("BDA_PROJECT_ARNS")
    if project_arns_json:
        project_arns = json.loads(project_arns_json)
    else:
        project_arn = get_required_env(EnvVars.BDA_PROJECT_ARN_ALL)
        project_arns = {"default": project_arn}

    schemas: dict[str, Any] = {}

    for category, project_arn in project_arns.items():
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

                fields = _extract_fields(schema)

                schemas[document_type] = {
                    "documentType": document_type,
                    "fields": fields,
                    "category": category,
                    "blueprintArn": blueprint_arn,
                }

        except Exception as e:
            logger.error(f"Failed to fetch schemas from BDA project {category}: {e}")

    logger.info(f"Fetched {len(schemas)} schemas from {len(project_arns)} BDA projects")
    return schemas


def _extract_fields(schema: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract field list from schema."""
    fields = []
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
                    {
                        "name": full_name,
                        "type": nested_spec.get("type", "string"),
                        "description": nested_spec.get("instruction", ""),
                    }
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
                        {
                            "name": full_name,
                            "type": nested_spec.get("type", "string"),
                            "description": nested_spec.get("instruction", ""),
                        }
                    )
            else:
                fields.append(
                    {
                        "name": field_name,
                        "type": "array",
                        "description": field_spec.get("instruction", ""),
                    }
                )
        else:
            fields.append(
                {
                    "name": field_name,
                    "type": field_spec.get("type", "string"),
                    "description": field_spec.get("instruction", ""),
                }
            )

    return fields


def get_all_schemas() -> dict[str, Any]:
    """Get all document schemas."""
    cache = get_cache()

    # try cache first
    schemas = cache.get(Cache.KEY_BLUEPRINT_SCHEMAS)
    if schemas is not None:
        return cast(dict[str, Any], schemas)

    # fetch from BDA and cache
    schemas = _fetch_schemas_from_bda()
    if schemas:
        cache.add(
            Cache.KEY_BLUEPRINT_SCHEMAS, schemas, ttl_minutes=Cache.TTL_BLUEPRINT_SCHEMAS_MINUTES
        )

    return schemas


def get_document_schema(document_type: str) -> dict[str, Any] | None:
    """Get schema for specific document type."""
    schemas = get_all_schemas()
    return schemas.get(document_type)


def get_all_fields() -> list[dict[str, Any]]:
    schemas = get_all_schemas()
    data: list[dict[str, Any]] = []
    for doc_type, schema in schemas.items():
        data.extend(
            {DictionaryBlueprintField.DOCUMENT_TYPE: doc_type, **field}
            for field in schema[DictionaryBlueprintSchema.FIELDS]
        )

    data.sort(key=lambda f: f[DictionaryBlueprintField.DOCUMENT_TYPE])
    return data


def invalidate_schema_cache() -> None:
    """Force refresh of schema cache."""
    cache = get_cache()
    cache.invalidate(Cache.KEY_BLUEPRINT_SCHEMAS)

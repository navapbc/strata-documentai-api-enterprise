"""Build Pydantic models from blueprint schemas for instructor-based LLM extraction."""

from typing import Any

from pydantic import BaseModel, Field

from documentai_api.utils.schemas import DocumentSchema


def build_blueprint_model(schema: DocumentSchema) -> tuple[type[BaseModel], dict[str, str]]:
    """Dynamically build a Pydantic response model from a DocumentSchema.

    Each field becomes an Optional inner model with `value` and `text_citation`
    so instructor can populate both the extracted value and the source span.

    Pydantic attribute names can't contain dots, so nested field names (e.g.
    "CompanyAddress.City") are mangled to underscores for the model itself.
    Returns (model, field_name_map), where field_name_map maps each mangled
    name back to the schema's dotted field name.
    """
    field_models: dict[str, type[BaseModel]] = {}
    model_fields: dict[str, Any] = {}
    field_name_map: dict[str, str] = {}

    for schema_field in schema.fields:
        field_name_underscored = schema_field.name.replace(".", "_")
        field_name_map[field_name_underscored] = schema_field.name

        inner = type(
            f"_{field_name_underscored}",
            (BaseModel,),
            {
                "__annotations__": {"value": str | None, "text_citation": str | None},
                "value": Field(default=None, description=schema_field.description),
                "text_citation": Field(
                    default=None,
                    description="Verbatim text from the document that supports this value",
                ),
            },
        )
        field_models[field_name_underscored] = inner
        model_fields[field_name_underscored] = (inner | None, Field(default=None))

    model = type(
        f"{schema.document_type.replace('-', '_')}Model",
        (BaseModel,),
        {
            "__annotations__": {k: v[0] for k, v in model_fields.items()},
            **{k: v[1] for k, v in model_fields.items()},
        },
    )
    return model, field_name_map

"""Build Pydantic models from blueprint schemas for instructor-based LLM extraction."""

from typing import Any

from pydantic import BaseModel, Field

from documentai_api.utils.schemas import DocumentSchema


def build_blueprint_model(schema: DocumentSchema) -> type[BaseModel]:
    """Dynamically build a Pydantic response model from a DocumentSchema.

    Each field becomes an Optional inner model with `value` and `text_citation`
    so instructor can populate both the extracted value and the source span.
    """
    field_models: dict[str, type[BaseModel]] = {}
    model_fields: dict[str, Any] = {}

    for schema_field in schema.fields:
        safe_name = schema_field.name.replace(".", "_")

        inner = type(
            f"_{safe_name}",
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
        field_models[safe_name] = inner
        model_fields[safe_name] = (inner | None, Field(default=None))

    return type(
        f"{schema.document_type.replace('-', '_')}Model",
        (BaseModel,),
        {
            "__annotations__": {k: v[0] for k, v in model_fields.items()},
            **{k: v[1] for k, v in model_fields.items()},
        },
    )

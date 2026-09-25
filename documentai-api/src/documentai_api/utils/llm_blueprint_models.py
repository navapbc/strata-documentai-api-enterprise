"""Build Pydantic models from blueprint schemas for instructor-based LLM extraction."""

from typing import Any

from pydantic import BaseModel, Field

from documentai_api.utils.schemas import DocumentSchema

# AWS Bedrock blueprint descriptions are sometimes too generic to disambiguate
# similarly-named field groups (e.g. CompanyAddress vs EmployeeAddress both
# describe themselves as just "the address"). Since blueprint_schemas.json is
# pulled from Bedrock and can't be edited directly, clarifications are appended
# here instead, scoped to the LLM extraction path only.
_DESCRIPTION_CLARIFICATIONS: dict[str, str] = {
    "CompanyAddress.Line1": "This is the employer/company's business address (as shown in the letterhead), not the employee's home address.",
    "CompanyAddress.Line2": "This is the employer/company's business address (as shown in the letterhead), not the employee's home address.",
    "CompanyAddress.City": "This is the employer/company's business address (as shown in the letterhead), not the employee's home address.",
    "CompanyAddress.State": "This is the employer/company's business address (as shown in the letterhead), not the employee's home address.",
    "CompanyAddress.ZipCode": "This is the employer/company's business address (as shown in the letterhead), not the employee's home address.",
    "EmployeeAddress.Line1": "This is the employee's personal home address, only if printed separately from the employer's address.",
    "EmployeeAddress.Line2": "This is the employee's personal home address, only if printed separately from the employer's address.",
    "EmployeeAddress.City": "This is the employee's personal home address, only if printed separately from the employer's address.",
    "EmployeeAddress.State": "This is the employee's personal home address, only if printed separately from the employer's address.",
    "EmployeeAddress.ZipCode": "This is the employee's personal home address, only if printed separately from the employer's address.",
}


def _field_description(schema_field: Any) -> str:
    clarification = _DESCRIPTION_CLARIFICATIONS.get(schema_field.name)
    if not clarification:
        return str(schema_field.description)
    return f"{schema_field.description} {clarification}".strip()


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
                "value": Field(default=None, description=_field_description(schema_field)),
                "text_citation": Field(
                    default=None,
                    description="The shortest exact verbatim substring from the document that supports only this field's value. Must be a direct quote; do not include text from adjacent fields. Leave null if the field is absent.",
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

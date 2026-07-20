"""Textract AnalyzeID field and document class mappings."""

from documentai_api.mappings.textract.document_classes import TEXTRACT_ID_TYPE_TO_DOCUMENT_CLASS
from documentai_api.mappings.textract.us_drivers_licenses import FIELD_MAP as US_DL_FIELD_MAP
from documentai_api.mappings.textract.us_drivers_licenses import (
    NON_NORMALIZED_ANALYZE_ID_FIELDS as US_DL_SUPPLEMENTAL_FIELDS,
)
from documentai_api.mappings.textract.us_drivers_licenses import (
    NOVA_SUPPLEMENTAL_PROMPT as US_DL_SUPPLEMENTAL_PROMPT,
)
from documentai_api.mappings.textract.us_passports import FIELD_MAP as US_PASSPORT_FIELD_MAP
from documentai_api.mappings.textract.us_passports import (
    NON_NORMALIZED_ANALYZE_ID_FIELDS as US_PASSPORT_SUPPLEMENTAL_FIELDS,
)
from documentai_api.mappings.textract.us_passports import (
    NOVA_SUPPLEMENTAL_PROMPT as US_PASSPORT_SUPPLEMENTAL_PROMPT,
)

_FIELD_MAPS = {
    "US-passports": US_PASSPORT_FIELD_MAP,
    "US-drivers-licenses": US_DL_FIELD_MAP,
}

_SUPPLEMENTAL_CONFIG: dict[str, tuple[dict[str, str], str]] = {
    "US-drivers-licenses": (US_DL_SUPPLEMENTAL_FIELDS, US_DL_SUPPLEMENTAL_PROMPT),
    "US-passports": (US_PASSPORT_SUPPLEMENTAL_FIELDS, US_PASSPORT_SUPPLEMENTAL_PROMPT),
}


def get_document_class(textract_id_type: str | None) -> str | None:
    """Map Textract ID_TYPE value to a document class name."""
    if not textract_id_type:
        return None
    return TEXTRACT_ID_TYPE_TO_DOCUMENT_CLASS.get(textract_id_type)


def get_bda_field_map(document_class: str) -> dict[str, str]:
    """Get the Textract field type -> BDA field name map for a document class."""
    return _FIELD_MAPS.get(document_class, {})


def get_supplemental_config(document_class: str) -> tuple[dict[str, str], str] | None:
    """Get supplemental fields and prompt for a document class, or None if not configured."""
    return _SUPPLEMENTAL_CONFIG.get(document_class)


__all__ = [
    "get_bda_field_map",
    "get_document_class",
    "get_supplemental_config",
]

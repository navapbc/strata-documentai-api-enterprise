"""Tests for utils/schemas.py."""

import json
from unittest.mock import patch

import pytest

from documentai_api.config.env import EnvVars
from documentai_api.utils import schemas
from documentai_api.utils.schemas import DocumentSchema, SchemaField


@pytest.fixture(autouse=True)
def mock_env(monkeypatch):
    monkeypatch.setenv(EnvVars.BDA_PROJECT_ARN_ALL, "arn:aws:bedrock:us-east-1:123:project/test")


@pytest.fixture(autouse=True)
def _clear_schemas_cache():
    """get_all_schemas() is lru_cache'd - clear it so tests don't leak into each other."""
    schemas.get_all_schemas.cache_clear()
    yield
    schemas.get_all_schemas.cache_clear()


@pytest.fixture
def schemas_file(tmp_path, monkeypatch):
    """Point SCHEMAS_FILE at a temp file for get_all_schemas() to read."""
    path = tmp_path / "blueprint_schemas.json"
    monkeypatch.setattr(schemas, "SCHEMAS_FILE", path)
    return path


@pytest.fixture
def mock_bda_services():
    """Mock BDA service calls."""
    with (
        patch("documentai_api.utils.schemas.get_data_automation_project") as mock_bda_project,
        patch("documentai_api.utils.schemas.get_blueprint") as mock_bda_blueprint,
    ):
        yield {"project": mock_bda_project, "blueprint": mock_bda_blueprint}


def test_extract_fields():
    """Extract basic fields from schema."""
    schema = {
        "properties": {
            "name": {"type": "string", "instruction": "Customer name"},
            "age": {"type": "number", "instruction": "Customer age"},
        }
    }

    fields = schemas.extract_fields(schema)

    assert len(fields) == 2
    assert fields[0].name == "name"
    assert fields[0].type == "string"
    assert fields[1].name == "age"


def test_extract_fields_with_ref():
    """Extract nested fields with $ref."""
    schema = {
        "properties": {"address": {"$ref": "#/definitions/Address"}},
        "definitions": {
            "Address": {
                "properties": {
                    "street": {"type": "string", "instruction": "Street name"},
                    "city": {"type": "string", "instruction": "City name"},
                }
            }
        },
    }

    fields = schemas.extract_fields(schema)

    assert len(fields) == 2
    assert fields[0].name == "address.street"
    assert fields[1].name == "address.city"


def test_extract_fields_array_with_ref():
    """Extract array fields with $ref."""
    schema = {
        "properties": {"items": {"type": "array", "items": {"$ref": "#/definitions/Item"}}},
        "definitions": {
            "Item": {
                "properties": {
                    "name": {"type": "string", "instruction": "Item name"},
                    "price": {"type": "number", "instruction": "Item price"},
                }
            }
        },
    }

    fields = schemas.extract_fields(schema)

    assert len(fields) == 2
    assert fields[0].name == "items.name"
    assert fields[1].name == "items.price"


def test_extract_fields_array_without_ref():
    """Extract simple array fields."""
    schema = {"properties": {"tags": {"type": "array", "instruction": "List of tags"}}}

    fields = schemas.extract_fields(schema)

    assert len(fields) == 1
    assert fields[0].name == "tags"
    assert fields[0].type == "array"


def test_fetch_schemas_from_bda(mock_bda_services):
    """Fetch schemas from BDA per-category projects."""
    mock_bda_services["project"].return_value = {
        "project": {
            "customOutputConfiguration": {
                "blueprints": [{"blueprintArn": "arn:aws:bedrock:us-east-1:123:blueprint/invoice"}]
            }
        }
    }
    mock_bda_services["blueprint"].return_value = {
        "blueprint": {"schema": '{"class": "Invoice", "properties": {}}'}
    }

    with patch("documentai_api.utils.schemas.get_aws_config") as mock_cfg:
        mock_cfg.return_value.get_bda_project_arns.return_value = {
            "invoices": "arn:aws:bedrock:us-east-1:123:project/invoices",
        }
        result = schemas.fetch_schemas_from_bda()

    assert "Invoice" in result
    assert result["Invoice"].category == "invoices"


def test_fetch_schemas_skips_all_project(mock_bda_services):
    """'all' is a superset of every category project, so it's skipped.

    The union of the category projects covers everything without duplicate
    entries or a fake "all" category tag.
    """
    mock_bda_services["project"].return_value = {
        "project": {
            "customOutputConfiguration": {
                "blueprints": [{"blueprintArn": "arn:aws:bedrock:us-east-1:123:blueprint/w2"}]
            }
        }
    }
    mock_bda_services["blueprint"].return_value = {
        "blueprint": {"schema": '{"class": "W2", "properties": {}}'}
    }

    with patch("documentai_api.utils.schemas.get_aws_config") as mock_cfg:
        mock_cfg.return_value.get_bda_project_arns.return_value = {
            "employer_income": "arn:aws:bedrock:us-east-1:123:project/employer",
            "all": "arn:aws:bedrock:us-east-1:123:project/all",
        }
        result = schemas.fetch_schemas_from_bda()

    assert result["W2"].category == "employer_income"
    # project was fetched exactly once - for employer_income, not for 'all'
    mock_bda_services["project"].assert_called_once_with(
        "arn:aws:bedrock:us-east-1:123:project/employer"
    )


def test_get_all_schemas_reads_from_static_file(schemas_file):
    """get_all_schemas() reads the preloaded static file, not BDA."""
    schemas_file.write_text(
        json.dumps(
            {
                "Invoice": {
                    "document_type": "Invoice",
                    "description": "An invoice",
                    "category": "invoices",
                    "fields": [{"name": "total", "type": "number", "description": "Total"}],
                }
            }
        )
    )

    result = schemas.get_all_schemas()

    assert result["Invoice"] == DocumentSchema(
        document_type="Invoice",
        description="An invoice",
        category="invoices",
        fields=[SchemaField(name="total", type="number", description="Total")],
    )


def test_get_all_schemas_missing_file_returns_empty(schemas_file):
    """get_all_schemas() returns {} when the static file hasn't been generated yet."""
    assert not schemas_file.exists()

    assert schemas.get_all_schemas() == {}


def test_get_document_schema_found(schemas_file):
    """Get specific document schema."""
    schemas_file.write_text(
        json.dumps(
            {
                "Invoice": {
                    "document_type": "Invoice",
                    "description": "",
                    "category": "",
                    "fields": [],
                }
            }
        )
    )

    result = schemas.get_document_schema("Invoice")

    assert result.document_type == "Invoice"


def test_get_document_schema_not_found(schemas_file):
    """Return None when document type not found."""
    schemas_file.write_text(
        json.dumps(
            {
                "Invoice": {
                    "document_type": "Invoice",
                    "description": "",
                    "category": "",
                    "fields": [],
                }
            }
        )
    )

    result = schemas.get_document_schema("Unknown")

    assert result is None


def test_get_all_fields_flattens_schemas():
    """get_all_fields() returns flat dict records, keyed by camelCase names."""
    mock_schemas = {
        "Invoice": DocumentSchema(
            document_type="Invoice",
            description="An invoice",
            category="invoices",
            fields=[SchemaField(name="total", type="number", description="Total amount")],
        ),
    }

    with patch("documentai_api.utils.schemas.get_all_schemas", return_value=mock_schemas):
        result = schemas.get_all_fields()

    assert result == [
        {
            "documentType": "Invoice",
            "name": "total",
            "type": "number",
            "description": "Total amount",
        }
    ]

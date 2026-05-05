from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from documentai_api.app import (
    app,
    verify_api_key,
)

client = TestClient(app)


MOCK_SCHEMAS = {
    "W2": {
        "fields": [
            {"name": "ssn", "type": "string", "description": "Social security number"},
            {"name": "wages", "type": "number", "description": "Total wages"},
        ]
    },
    "Payslip": {
        "fields": [
            {"name": "gross_pay", "type": "number", "description": "Gross pay amount"},
            {"name": "ssn", "type": "string", "description": "Employee SSN"},
        ]
    },
}


@pytest.fixture(autouse=True)
def disable_auth():
    app.dependency_overrides[verify_api_key] = lambda: None
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def mock_schemas():
    with (
        patch("documentai_api.app.get_all_schemas", return_value=MOCK_SCHEMAS),
        patch("documentai_api.utils.schemas.get_all_schemas", return_value=MOCK_SCHEMAS),
    ):
        yield


# ==============================================================================
# schema list
# ==============================================================================


def test_schemas_list(mock_schemas):
    """Test listing all schemas."""
    response = client.get("/v1/dictionary/schemas")

    assert response.status_code == 200
    assert response.json()["schemas"] == ["Payslip", "W2"]


def test_schema_all_returns_404(mock_schemas):
    """Test that 'all' is no longer a magic path param."""
    response = client.get("/v1/dictionary/schemas/all")
    assert response.status_code == 404


# ==============================================================================
# single schema
# ==============================================================================


def test_schema_single(mock_schemas):
    """Test getting single schema."""
    response = client.get("/v1/dictionary/schemas/W2")
    assert response.status_code == 200
    assert len(response.json()["fields"]) == 2


def test_schema_not_found():
    """Test 404 for unknown schema."""
    with patch("documentai_api.app.get_document_schema", return_value=None):
        response = client.get("/v1/dictionary/schemas/Unknown")

    assert response.status_code == 404


# ==============================================================================
# fields
# ==============================================================================


def test_all_json(mock_schemas):
    """Test getting all fields as JSON."""
    response = client.get("/v1/dictionary/fields")

    fields = response.json()["fields"]
    assert len(fields) == 4
    assert fields[0]["documentType"] == "Payslip"
    assert fields[-1]["documentType"] == "W2"


def test_all_csv(mock_schemas):
    """Test getting all fields as CSV."""
    response = client.get("/v1/dictionary/fields?format=csv")

    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    assert "W2" in response.text
    assert "Payslip" in response.text


# ==============================================================================
# search
# ==============================================================================


def test_search_no_query(mock_schemas):
    """Search with no query returns all fields."""
    response = client.get("/v1/dictionary/search")

    assert response.status_code == 200
    assert len(response.json()["fields"]) == 4


def test_search_by_name(mock_schemas):
    """Search filtered to name field."""
    response = client.get("/v1/dictionary/search?q=ssn&field=name")

    fields = response.json()["fields"]
    assert len(fields) == 2
    assert all(f["name"] == "ssn" for f in fields)


def test_search_by_description(mock_schemas):
    """Search filtered to description field."""
    response = client.get("/v1/dictionary/search?q=social&field=description")

    fields = response.json()["fields"]
    assert len(fields) == 1
    assert fields[0]["documentType"] == "W2"


def test_search_by_document_type(mock_schemas):
    """Search filtered to documentType field."""
    response = client.get("/v1/dictionary/search?q=payslip&field=documentType")

    fields = response.json()["fields"]
    assert len(fields) == 2
    assert all(f["documentType"] == "Payslip" for f in fields)


def test_search_all_columns(mock_schemas):
    """Search with no field searches all columns."""
    response = client.get("/v1/dictionary/search?q=gross")

    fields = response.json()["fields"]
    assert len(fields) == 1
    assert fields[0]["name"] == "gross_pay"


def test_search_case_insensitive(mock_schemas):
    """Search is case-insensitive."""
    response = client.get("/v1/dictionary/search?q=SSN&field=name")

    assert len(response.json()["fields"]) == 2


def test_search_no_results(mock_schemas):
    """Search with no matches returns empty list."""
    response = client.get("/v1/dictionary/search?q=nonexistent")

    assert len(response.json()["fields"]) == 0


def test_search_csv(mock_schemas):
    """Search with CSV format."""
    response = client.get("/v1/dictionary/search?q=ssn&field=name&format=csv")

    assert "text/csv" in response.headers["content-type"]
    assert "W2" in response.text
    assert "Payslip" in response.text


def test_search_sorted(mock_schemas):
    """Results are sorted by documentType."""
    response = client.get("/v1/dictionary/search?q=ssn&field=name")

    fields = response.json()["fields"]
    assert fields[0]["documentType"] == "Payslip"
    assert fields[1]["documentType"] == "W2"


# ==============================================================================
# other
# ==============================================================================
def test_response_codes():
    response = client.get("/v1/dictionary/response-codes")
    assert response.status_code == 200
    assert "responseCodes" in response.json()
    assert len(response.json()["responseCodes"]) > 0
    assert "code" in response.json()["responseCodes"][0]
    assert "message" in response.json()["responseCodes"][0]


def test_document_categories():
    response = client.get("/v1/dictionary/document-categories")
    assert response.status_code == 200
    assert "documentCategories" in response.json()
    assert len(response.json()["documentCategories"]) > 0


# ==============================================================================
# csv
# ==============================================================================


def test_csv_value_with_quotes():
    """Test CSV escaping for values containing quotes."""
    schemas = {
        "W2": {
            "fields": [
                {"name": "field1", "type": "string", "description": 'Contains "quotes"'},
            ]
        },
    }
    with patch("documentai_api.utils.schemas.get_all_schemas", return_value=schemas):
        response = client.get("/v1/dictionary/fields?format=csv")

    assert response.status_code == 200
    assert '""quotes""' in response.text


def test_csv_value_with_commas():
    """Test CSV escaping for values containing commas."""
    schemas = {
        "W2": {
            "fields": [
                {"name": "field1", "type": "string", "description": "Has, commas"},
            ]
        },
    }
    with patch("documentai_api.utils.schemas.get_all_schemas", return_value=schemas):
        response = client.get("/v1/dictionary/fields?format=csv")

    assert response.status_code == 200
    assert '"Has, commas"' in response.text


def test_csv_empty_data():
    """Test CSV with no data returns empty body."""
    with patch("documentai_api.utils.schemas.get_all_schemas", return_value={}):
        response = client.get("/v1/dictionary/fields?format=csv")

    assert response.status_code == 200
    assert response.text == ""


def test_csv_value_with_newline():
    """Test CSV escaping for values containing newlines."""
    schemas = {
        "W2": {
            "fields": [
                {"name": "field1", "type": "string", "description": "Line1\nLine2"},
            ]
        },
    }
    with patch("documentai_api.utils.schemas.get_all_schemas", return_value=schemas):
        response = client.get("/v1/dictionary/fields?format=csv")

    assert response.status_code == 200
    assert '"Line1\nLine2"' in response.text


def test_csv_value_with_none():
    """Test CSV handles None values."""
    schemas = {
        "W2": {
            "fields": [
                {"name": "field1", "type": "string", "description": None},
            ]
        },
    }
    with patch("documentai_api.utils.schemas.get_all_schemas", return_value=schemas):
        response = client.get("/v1/dictionary/fields?format=csv")

    assert response.status_code == 200
    assert "None" not in response.text


def test_response_codes_csv():
    response = client.get("/v1/dictionary/response-codes?format=csv")
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]


def test_document_categories_csv():
    response = client.get("/v1/dictionary/document-categories?format=csv")
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]

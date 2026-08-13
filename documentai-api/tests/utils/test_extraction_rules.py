import boto3
import pytest
from moto import mock_aws

from documentai_api.config.env import EnvVars
from documentai_api.utils.extraction_rules import (
    apply_extraction_rules,
    delete_rule,
    get_missing_required_fields,
    get_rules,
    upsert_rule,
)


@pytest.fixture
def extraction_rules_table(aws_credentials, monkeypatch):
    with mock_aws():
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        table = dynamodb.create_table(
            TableName="extraction-rules",
            KeySchema=[
                {"AttributeName": "tenantId", "KeyType": "HASH"},
                {"AttributeName": "documentType", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "tenantId", "AttributeType": "S"},
                {"AttributeName": "documentType", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        monkeypatch.setenv(EnvVars.EXTRACTION_RULES_TABLE_NAME, table.name)
        yield table


def test_get_rules_by_tenant(extraction_rules_table):
    extraction_rules_table.put_item(
        Item={"tenantId": "t1", "documentType": "W2", "fields": ["ssn"]}
    )
    extraction_rules_table.put_item(
        Item={"tenantId": "t1", "documentType": "Payslip", "fields": ["gross_pay"]}
    )

    result = get_rules("t1")

    assert len(result) == 2


def test_get_rules_by_tenant_and_document_type(extraction_rules_table):
    extraction_rules_table.put_item(
        Item={"tenantId": "t1", "documentType": "W2", "fields": ["ssn"]}
    )

    result = get_rules("t1", "W2")

    assert len(result) == 1
    assert result[0]["documentType"] == "W2"


def test_get_rules_not_found(extraction_rules_table):
    result = get_rules("t1", "W2")

    assert result == []


def test_upsert_rule_new(extraction_rules_table):
    result = upsert_rule("t1", "W2", ["ssn", "wages"], ["employer_name"])

    assert result["tenantId"] == "t1"
    assert result["requiredFields"] == ["ssn", "wages"]
    assert result["optionalFields"] == ["employer_name"]
    assert "createdAt" in result

    item = extraction_rules_table.get_item(Key={"tenantId": "t1", "documentType": "W2"})["Item"]
    assert item["requiredFields"] == ["ssn", "wages"]
    assert item["optionalFields"] == ["employer_name"]


def test_upsert_rule_existing_preserves_created_at(extraction_rules_table):
    extraction_rules_table.put_item(
        Item={
            "tenantId": "t1",
            "documentType": "W2",
            "requiredFields": ["ssn"],
            "optionalFields": [],
            "createdAt": "2026-01-01",
        }
    )

    result = upsert_rule("t1", "W2", ["ssn", "wages"], ["employer_name"])

    assert result["createdAt"] == "2026-01-01"
    assert result["requiredFields"] == ["ssn", "wages"]
    assert result["optionalFields"] == ["employer_name"]


def test_delete_rule(extraction_rules_table):
    extraction_rules_table.put_item(
        Item={"tenantId": "t1", "documentType": "W2", "fields": ["ssn"]}
    )

    delete_rule("t1", "W2")

    item = extraction_rules_table.get_item(Key={"tenantId": "t1", "documentType": "W2"}).get("Item")
    assert item is None


def test_apply_extraction_rules_filters_fields(extraction_rules_table):
    extraction_rules_table.put_item(
        Item={
            "tenantId": "t1",
            "documentType": "W2",
            "requiredFields": ["ssn", "wages"],
            "optionalFields": ["employer_name"],
            "createdAt": "2026-01-01",
            "updatedAt": "2026-01-01",
        }
    )

    fields = {"ssn": "123", "wages": "50000", "employer_name": "Acme", "extra_field": "ignored"}
    result = apply_extraction_rules("t1", "W2", fields)

    assert result.fields == {"ssn": "123", "wages": "50000", "employer_name": "Acme"}
    assert result.missing_required_field_list == []


def test_apply_extraction_rules_missing_required(extraction_rules_table):
    extraction_rules_table.put_item(
        Item={
            "tenantId": "t1",
            "documentType": "W2",
            "requiredFields": ["ssn", "wages", "federal_tax"],
            "optionalFields": [],
            "createdAt": "2026-01-01",
            "updatedAt": "2026-01-01",
        }
    )

    fields = {"ssn": "123", "wages": "50000"}
    result = apply_extraction_rules("t1", "W2", fields)

    assert result.fields == {"ssn": "123", "wages": "50000"}
    assert result.missing_required_field_list == ["federal_tax"]


def test_apply_extraction_rules_no_rules(extraction_rules_table):
    fields = {"ssn": "123", "wages": "50000", "extra": "value"}
    result = apply_extraction_rules("t1", "W2", fields)

    assert result.fields == fields
    assert result.missing_required_field_list == []


@pytest.mark.parametrize(
    ("missing_fields", "expected_missing_required", "excluded_from_result"),
    [
        # Required fields flagged as missing -> removed and reported
        (
            ["PayPeriodStartDate", "YTDGrossPay"],
            ["PayPeriodStartDate", "YTDGrossPay"],
            ["PayPeriodStartDate", "YTDGrossPay"],
        ),
        # Optional field flagged -> kept in response, not reported
        (["EmployerName"], [], []),
        # None -> legacy noop
        (None, [], []),
    ],
)
def test_apply_extraction_rules_missing_fields(
    extraction_rules_table, missing_fields, expected_missing_required, excluded_from_result
):
    extraction_rules_table.put_item(
        Item={
            "tenantId": "t1",
            "documentType": "Payslip",
            "requiredFields": ["GrossPay", "PayPeriodStartDate", "YTDGrossPay"],
            "optionalFields": ["EmployerName"],
            "createdAt": "2026-01-01",
            "updatedAt": "2026-01-01",
        }
    )

    fields = {
        "GrossPay": "5000",
        "PayPeriodStartDate": "2025-01-01",
        "YTDGrossPay": "",
        "EmployerName": "Acme",
    }
    result = apply_extraction_rules("t1", "Payslip", fields, missing_fields=missing_fields)

    for f in excluded_from_result:
        assert f not in result.fields
    assert sorted(result.missing_required_field_list) == sorted(expected_missing_required)


def test_get_missing_required_fields_one_empty(extraction_rules_table):
    """A required field that came back empty is reported as missing."""
    extraction_rules_table.put_item(
        Item={
            "tenantId": "t1",
            "documentType": "W2",
            "requiredFields": ["ssn", "wages"],
            "optionalFields": [],
            "createdAt": "2026-01-01",
            "updatedAt": "2026-01-01",
        }
    )
    missing, required = get_missing_required_fields(
        "t1", "W2", empty_fields=["ssn"], fields_missing_geometry=[]
    )
    assert missing == ["ssn"]
    assert required == ["ssn", "wages"]


def test_get_missing_required_fields_all_present(extraction_rules_table):
    """No empty or geometry-missing fields → missing list is empty."""
    extraction_rules_table.put_item(
        Item={
            "tenantId": "t1",
            "documentType": "W2",
            "requiredFields": ["ssn", "wages"],
            "optionalFields": [],
            "createdAt": "2026-01-01",
            "updatedAt": "2026-01-01",
        }
    )
    missing, required = get_missing_required_fields(
        "t1", "W2", empty_fields=[], fields_missing_geometry=[]
    )
    assert missing == []
    assert required == ["ssn", "wages"]

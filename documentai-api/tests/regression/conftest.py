"""Fixtures for the document-type regression suite.

Seeds a canned BDA result at the S3-JSON boundary and runs it through the
real `documentai_api.pipeline.bda.run_bda_result_pipeline`.

See docs/documentai-api/qa-and-troubleshooting.md for how to triage a
failure and re-test after a blueprint/configuration change.
"""

import json
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

from documentai_api.config.env_var_names_generated import EnvVarNames

MANIFEST_PATH = Path(__file__).parent / "document_type_manifest.json"
# tests/regression/conftest.py -> tests -> documentai-api -> repo root
INFRA_DOCUMENT_TYPES_DIR = Path(__file__).resolve().parents[3] / "infra" / "document-types"
REGRESSION_TENANT_ID = "regression-test-tenant"

# Populated by each test via the `regression_report` fixture, written to disk
# once at the end of the session for QA triage (make test-regression prints
# the path). Module-level so it survives across the whole pytest session
# regardless of how tests are parametrized/collected.
_report_results: list[dict[str, Any]] = []

REPORT_PATH = Path(__file__).parent / ".regression_report.json"


@dataclass
class RegressionCase:
    category: str
    blueprint: str
    document_class: str
    fields: dict[str, dict[str, Any]]
    required_fields: list[str] = field(default_factory=list)
    optional_fields: list[str] = field(default_factory=list)
    expected_missing_required_fields: list[str] = field(default_factory=list)
    expected_response_code: str = "000"
    notes: list[str] | None = None


def load_regression_cases() -> list[RegressionCase]:
    manifest = json.loads(MANIFEST_PATH.read_text())
    return [
        RegressionCase(
            category=case["category"],
            blueprint=case["blueprint"],
            document_class=case["document_class"],
            fields=case["fields"],
            required_fields=case.get("required_fields", []),
            optional_fields=case.get("optional_fields", []),
            expected_missing_required_fields=case.get("expected_missing_required_fields", []),
            expected_response_code=case.get("expected_response_code", "000"),
            notes=case.get("notes"),
        )
        for case in manifest["cases"]
    ]


def _is_leaf(field_data: Any) -> bool:
    """Whether a canned field spec is a leaf (has a value/confidence).

    Anything else is a nested object, matching how BDA nests composite
    fields (e.g. a driver's license's NAME_DETAILS.FIRST_NAME).
    """
    return isinstance(field_data, dict) and ("value" in field_data or "confidence" in field_data)


def build_explainability_info(fields: dict[str, Any]) -> dict[str, Any]:
    """Recursively build a canned explainability_info payload from RegressionCase.fields.

    Preserves nesting and per-field type so the suite exercises the same
    recursive/nested BDA reader path (`readers/bda.py::_extract_fields_recursive`)
    production traffic does.
    """
    result: dict[str, Any] = {}
    for field_name, field_data in fields.items():
        if _is_leaf(field_data):
            result[field_name] = {
                "confidence": field_data["confidence"],
                "value": field_data["value"],
                "type": field_data.get("type", "string"),
            }
        else:
            result[field_name] = build_explainability_info(field_data)
    return result


def flatten_expected_fields(fields: dict[str, Any], prefix: str = "") -> dict[str, float]:
    """Flatten RegressionCase.fields into {dotted.path: confidence}.

    Matches the dotted field names `_extract_fields_recursive` produces for
    nested fields (e.g. {"recipient_name": {"first_name": {...}}} ->
    "recipient_name.first_name").
    """
    flat: dict[str, float] = {}
    for field_name, field_data in fields.items():
        full_name = f"{prefix}.{field_name}" if prefix else field_name
        if _is_leaf(field_data):
            flat[full_name] = field_data["confidence"]
        else:
            flat.update(flatten_expected_fields(field_data, full_name))
    return flat


def flatten_expected_field_types(fields: dict[str, Any], prefix: str = "") -> dict[str, str]:
    """Flatten RegressionCase.fields into {dotted.path: type}.

    Defaults a leaf's type to "string" - the same default `build_explainability_info`
    applies - so a manifest leaf with no explicit "type" is checked against the
    schema as a string field.
    """
    flat: dict[str, str] = {}
    for field_name, field_data in fields.items():
        full_name = f"{prefix}.{field_name}" if prefix else field_name
        if _is_leaf(field_data):
            flat[full_name] = field_data.get("type", "string")
        else:
            flat.update(flatten_expected_field_types(field_data, full_name))
    return flat


def get_registered_blueprint_names(category: str) -> set[str]:
    """Blueprint names registered under infra/document-types/<category>/.

    This is the configuration production actually deploys against (see
    infra/document-types/README.md), independent of blueprint_schemas.json -
    a manifest case's canned BDA result is manufactured directly from
    `case.blueprint`/`case.document_class` and never consults this
    configuration, so a renamed/removed/miscategorized blueprint would
    otherwise still "match" and pass here.

    Managed blueprint names come from managed_blueprints.json's "name" field
    (the identifier used to request the blueprint); custom blueprint names
    are inferred from each category's custom-<blueprint-name>.json files.
    """
    category_dir = INFRA_DOCUMENT_TYPES_DIR / category
    assert category_dir.is_dir(), f"no infra/document-types/{category} directory"

    names: set[str] = set()
    managed_file = category_dir / "managed_blueprints.json"
    if managed_file.exists():
        names.update(entry["name"] for entry in json.loads(managed_file.read_text()))
    names.update(f.stem.removeprefix("custom-") for f in category_dir.glob("custom-*.json"))
    return names


@pytest.fixture
def regression_env(
    monkeypatch,
    s3_bucket,
    ddb_doc_metadata_table,
    extraction_rules_table,
    tenants_table,
):
    """Mock AWS environment (moto S3 + DynamoDB) for a regression case.

    Repoints DOCUMENTAI_OUTPUT_LOCATION at the moto S3 bucket created by
    `s3_bucket` (`ddb_doc_metadata_table` defaults it to a differently-named
    bucket) so `get_bda_result_json`'s output-bucket check passes.
    """
    monkeypatch.setenv(EnvVarNames.DOCUMENTAI_OUTPUT_LOCATION, f"s3://{s3_bucket.name}/output")
    return {
        "bucket": s3_bucket,
        "metadata_table": ddb_doc_metadata_table,
        "extraction_rules_table": extraction_rules_table,
    }


@pytest.fixture
def seed_bda_case(regression_env):
    """Factory to seed a canned BDA result + DDB record for a regression case.

    Returns (bucket_name, job_metadata_key, file_name) - the args
    `run_bda_result_pipeline` expects, plus the DDB key to look up the result.
    """
    bucket = regression_env["bucket"]

    def _seed(
        case: RegressionCase, *, tenant_id: str = REGRESSION_TENANT_ID
    ) -> tuple[str, str, str]:
        from documentai_api.utils.extraction_rules import upsert_rule

        if case.required_fields or case.optional_fields:
            upsert_rule(tenant_id, case.document_class, case.required_fields, case.optional_fields)

        invocation_id = str(uuid.uuid4())
        file_name = f"input/{tenant_id}/{case.blueprint}.pdf"

        result_key = (
            f"output/{tenant_id}/{case.blueprint}/{invocation_id}/0/custom_output/0/result.json"
        )
        job_metadata_key = (
            f"output/{tenant_id}/{case.blueprint}/{invocation_id}/0/custom_output/job_metadata.json"
        )

        explainability_info = build_explainability_info(case.fields)

        result_json = {
            "matched_blueprint": {"name": case.blueprint, "confidence": "0.97"},
            "document_class": {"type": case.document_class},
            "explainability_info": [explainability_info],
        }
        bucket.put_object(Key=result_key, Body=json.dumps(result_json).encode())

        job_metadata_json = {
            "output_metadata": [
                {"segment_metadata": [{"custom_output_path": f"s3://{bucket.name}/{result_key}"}]}
            ]
        }
        bucket.put_object(Key=job_metadata_key, Body=json.dumps(job_metadata_json).encode())

        regression_env["metadata_table"].put_item(
            Item={
                "fileName": file_name,
                "tenantId": tenant_id,
                "bdaInvocationId": invocation_id,
            }
        )

        return bucket.name, job_metadata_key, file_name

    return _seed


@pytest.fixture
def regression_report():
    """Record a case's outcome for the end-of-session triage report."""

    def _record(case: RegressionCase, *, passed: bool, details: dict[str, Any]) -> None:
        _report_results.append(
            {
                "category": case.category,
                "blueprint": case.blueprint,
                "document_class": case.document_class,
                "passed": passed,
                "details": details,
            }
        )

    return _record


def pytest_sessionfinish(session, exitstatus):
    """Write the collected regression results to disk for QA triage.

    Only writes a report if this session actually ran regression cases -
    leaves any previous report untouched otherwise (e.g. running an unrelated
    subset of the suite shouldn't blank out the last real regression run).
    """
    if not _report_results:
        return

    REPORT_PATH.write_text(json.dumps(_report_results, indent=2, sort_keys=True))
    failed = [r for r in _report_results if not r["passed"]]
    print(f"\nregression report written to {REPORT_PATH}")
    print(f"{len(_report_results)} case(s), {len(failed)} unexpected result(s)")
    for r in failed:
        print(f"  UNEXPECTED: {r['category']}/{r['blueprint']} - {r['details']}")

"""E2E tests for preclassification-based BDA project routing.

These tests enable the `preclassification-based-routing` feature flag for the
session, upload documents that are known to match a specific category blueprint,
and assert that:

  1. `preclassificationBlueprintMatchCategory` is written to DDB.
  2. Its value is a valid PreclassificationCategory slug (not "all").

This guards the regression where the 'all' project overwrote per-category tags
in _fetch_schemas_from_bda, causing routing to always fall back to the 'all' ARN.
"""

from pathlib import Path

import pytest

from documentai_api.config.constants import BDA_PROJECT_KEY_ALL, FeatureFlags
from documentai_api.config.constants_preclassification_category_generated import (
    PreclassificationCategory,
)
from documentai_api.schemas.document_metadata import DocumentMetadata

TEST_DOCS_DIR = Path(__file__).parent.parent / "helpers" / "fixtures" / "test-documents"

# Documents with stable BDA blueprint matches and known categories.
# File -> expected preclassificationBlueprintMatchCategory value.
ROUTING_CASES = [
    pytest.param(
        TEST_DOCS_DIR / "synthetic-public-benefits-income-proof-pay-stub.jpg",
        PreclassificationCategory.EMPLOYER_INCOME,
        id="pay-stub -> employer_income",
    ),
    pytest.param(
        TEST_DOCS_DIR / "synthetic-snap-income-proof-employment-wage-verification-letter-photo.png",
        PreclassificationCategory.EMPLOYMENT_RECORDS,
        id="wage-verification-letter -> employment_records",
    ),
    pytest.param(
        TEST_DOCS_DIR / "synthetic-public-benefits-identity-proof-state-photo-id.jpg",
        PreclassificationCategory.IDENTITY,
        id="state-id -> identity",
    ),
]


@pytest.fixture(scope="module", autouse=True)
def _enable_preclassification_routing(reset_env, monkeypatch_session):
    """Enable the preclassification-based-routing flag for this module's session.

    Restores the original value (or removes the parameter if it didn't exist)
    after the module finishes.
    """
    for k in (
        "SSM_PREFIX",
        "AWS_REGION",
        "AWS_PROFILE",
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "AWS_SESSION_TOKEN",
        "BDA_PROJECT_ARN_ALL",
    ):
        if v := reset_env.get(k):
            monkeypatch_session.setenv(k, v)

    for k, v in reset_env.items():
        if k.startswith("BDA_PROJECT_ID_"):
            monkeypatch_session.setenv(k, v)

    from documentai_api.config.env import get_aws_config

    get_aws_config.cache_clear()

    from documentai_api.services import ssm as ssm_service
    from documentai_api.utils.cache import get_cache

    config = get_aws_config()
    if not config.ssm_prefix:
        pytest.skip("SSM prefix not configured — skipping routing e2e tests")

    arns = config.get_bda_project_arns()
    per_category = {k: v for k, v in arns.items() if k != BDA_PROJECT_KEY_ALL}

    if not per_category:
        pytest.skip("No per-category BDA project IDs configured — skipping routing e2e tests")

    routing_param = (
        f"{config.ssm_prefix}/feature-flags/{FeatureFlags.PRECLASSIFICATION_BASED_ROUTING}"
    )
    textract_param = f"{config.ssm_prefix}/feature-flags/{FeatureFlags.TEXTRACT_IDENTITY_ENABLED}"

    try:
        original_routing = ssm_service.get_parameter(routing_param)
    except Exception:
        original_routing = None

    try:
        original_textract = ssm_service.get_parameter(textract_param)
    except Exception:
        original_textract = None

    ssm_service.put_parameter(routing_param, "true")
    ssm_service.put_parameter(textract_param, "false")
    get_cache().invalidate(f"ssm:{routing_param}")
    get_cache().invalidate(f"ssm:{textract_param}")

    yield

    if original_routing is not None:
        ssm_service.put_parameter(routing_param, original_routing)
    else:
        from documentai_api.utils.aws_client_factory import AWSClientFactory

        AWSClientFactory.get_ssm_client().delete_parameter(Name=routing_param)

    if original_textract is not None:
        ssm_service.put_parameter(textract_param, original_textract)
    else:
        AWSClientFactory.get_ssm_client().delete_parameter(Name=textract_param)

    get_cache().invalidate(f"ssm:{routing_param}")
    get_cache().invalidate(f"ssm:{textract_param}")


@pytest.mark.parametrize(("file_path", "expected_category"), ROUTING_CASES)
def test_routing_writes_per_category_match(file_path, expected_category, base_url, api_key):
    """Blueprint match category is a per-category slug, never 'all'."""
    from documentai_api.config.env import get_aws_config
    from documentai_api.services import ddb as ddb_service
    from tests.e2e.test_app_documents import _upload_and_wait

    body = _upload_and_wait(base_url, api_key, file_path)
    job_id = body["jobId"]

    cfg = get_aws_config()
    items = ddb_service.query_by_key(
        cfg.documentai_document_metadata_table_name,
        cfg.documentai_document_metadata_job_id_index_name,
        DocumentMetadata.JOB_ID,
        job_id,
    )
    assert items, f"expected a DDB record for jobId {job_id}"
    assert len(items) == 1, f"expected exactly 1 DDB record for jobId {job_id}, got {len(items)}"
    record = items[0]

    routing_category = record.get(DocumentMetadata.PRECLASSIFICATION_BLUEPRINT_MATCH_CATEGORY)

    assert routing_category is not None, (
        f"preclassificationBlueprintMatchCategory not written to DDB for {file_path.name}"
    )
    assert routing_category != BDA_PROJECT_KEY_ALL, (
        f"routing category should be a per-category slug, got '{BDA_PROJECT_KEY_ALL}'"
    )
    assert routing_category in {c.value for c in PreclassificationCategory}, (
        f"routing category '{routing_category}' is not a known PreclassificationCategory"
    )
    assert routing_category == expected_category.value, (
        f"expected routing category '{expected_category.value}' but got '{routing_category}'"
    )

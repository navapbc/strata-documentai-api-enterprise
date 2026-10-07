"""E2E tests for preclassification-based BDA project routing.

These tests upload documents that are known to match a specific category
blueprint, and assert that:

  1. `preclassificationBlueprintMatchCategory` is written to DDB.
  2. Its value is a valid PreclassificationCategory slug.

Routing to a category-specific BDA project is mandatory (there is no default/
catch-all project) - this guards the regression where a matched category has
no per-category BDA project ARN configured.
"""

from pathlib import Path

import pytest

from documentai_api.config.constants import FeatureFlags
from documentai_api.config.constants_preclassification_category_generated import (
    PreclassificationCategory,
)
from documentai_api.schemas.document_metadata import DocumentMetadata

TEST_DOCS_DIR = Path(__file__).parent.parent / "helpers" / "fixtures" / "test-documents"
TEST_DOCS_DIR_HAPPY_PATH = TEST_DOCS_DIR / "happy-path"

# Documents with stable BDA blueprint matches and known categories.
# File -> expected preclassificationBlueprintMatchCategory value.
ROUTING_CASES = [
    pytest.param(
        TEST_DOCS_DIR_HAPPY_PATH / "synthetic-public-benefits-income-proof-pay-stub.jpg",
        PreclassificationCategory.INCOME,
        id="pay-stub -> income",
    ),
    pytest.param(
        TEST_DOCS_DIR_HAPPY_PATH
        / "synthetic-snap-income-proof-employment-wage-verification-letter-photo.png",
        PreclassificationCategory.INCOME,
        id="wage-verification-letter -> income",
    ),
    pytest.param(
        TEST_DOCS_DIR_HAPPY_PATH / "synthetic-public-benefits-identity-proof-state-photo-id.jpg",
        PreclassificationCategory.IDENTITY,
        id="state-id -> identity",
    ),
]


@pytest.fixture(scope="module", autouse=True)
def _enable_preclassification_routing(reset_env, monkeypatch_session):
    """Ensure blueprint matching is enabled and per-category BDA projects are configured.

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
        "BDA_PROJECT_ARN",
    ):
        if v := reset_env.get(k):
            monkeypatch_session.setenv(k, v)

    for k, v in reset_env.items():
        if k.startswith("BDA_PROJECT_ID_"):
            monkeypatch_session.setenv(k, v)

    from documentai_api.config.env import get_env_config

    get_env_config.cache_clear()

    from documentai_api.services import ssm as ssm_service
    from documentai_api.utils.cache import get_cache

    config = get_env_config()
    if not config.ssm_prefix:
        pytest.skip("SSM prefix not configured - skipping routing e2e tests")

    per_category = config.get_bda_project_arns()

    if not per_category:
        pytest.skip("No per-category BDA project IDs configured - skipping routing e2e tests")

    matching_param = f"{config.ssm_prefix}/feature-flags/{FeatureFlags.ENABLE_PRECLASSIFICATION_BLUEPRINT_MATCHING}"
    textract_param = f"{config.ssm_prefix}/feature-flags/{FeatureFlags.TEXTRACT_IDENTITY_ENABLED}"

    try:
        original_matching = ssm_service.get_parameter(matching_param)
    except Exception:
        original_matching = None

    try:
        original_textract = ssm_service.get_parameter(textract_param)
    except Exception:
        original_textract = None

    ssm_service.put_parameter(matching_param, "true")
    ssm_service.put_parameter(textract_param, "false")
    get_cache().invalidate(f"ssm:{matching_param}")
    get_cache().invalidate(f"ssm:{textract_param}")

    yield

    if original_matching is not None:
        ssm_service.put_parameter(matching_param, original_matching)
    else:
        from documentai_api.services.aws_client_factory import AWSClientFactory

        AWSClientFactory.get_ssm_client().delete_parameter(Name=matching_param)

    if original_textract is not None:
        ssm_service.put_parameter(textract_param, original_textract)
    else:
        AWSClientFactory.get_ssm_client().delete_parameter(Name=textract_param)

    get_cache().invalidate(f"ssm:{matching_param}")
    get_cache().invalidate(f"ssm:{textract_param}")


@pytest.mark.parametrize(("file_path", "expected_category"), ROUTING_CASES)
def test_routing_writes_per_category_match(file_path, expected_category, base_url, api_key):
    """Blueprint match category is a per-category slug."""
    from documentai_api.config.env import get_env_config
    from documentai_api.services import ddb as ddb_service
    from tests.e2e.test_app_documents import _upload_and_wait

    body = _upload_and_wait(base_url, api_key, file_path)
    job_id = body["jobId"]

    cfg = get_env_config()
    items = ddb_service.query_by_key(
        cfg.documentai_document_metadata_table_name or "",
        cfg.documentai_document_metadata_job_id_index_name or "",
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
    assert routing_category in {c.value for c in PreclassificationCategory}, (
        f"routing category '{routing_category}' is not a known PreclassificationCategory"
    )
    assert routing_category == expected_category.value, (
        f"expected routing category '{expected_category.value}' but got '{routing_category}'"
    )

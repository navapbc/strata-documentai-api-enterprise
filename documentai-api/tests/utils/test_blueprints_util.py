"""Tests for utils/blueprints.py."""

import botocore.exceptions
import pytest

from documentai_api.config.constants import BdaBlueprintStage, BlueprintStatus
from documentai_api.schemas.blueprints import BlueprintRecord
from documentai_api.utils import blueprints as blueprints_util

TENANT_ID = "test-tenant-id"
PROJECT_ARN = "arn:aws:bedrock:us-east-1:123:data-automation-project/proj"
BLUEPRINT_ARN = "arn:aws:bedrock:us-east-1:123:blueprint/bp"


@pytest.fixture
def mock_bda(mocker):
    mock = mocker.MagicMock()
    mocker.patch(
        "documentai_api.utils.blueprints.AWSClientFactory.get_bda_client",
        return_value=mock,
    )
    mock.create_data_automation_project.return_value = {"projectArn": PROJECT_ARN}
    mock.create_blueprint.return_value = {"blueprint": {"blueprintArn": BLUEPRINT_ARN}}
    return mock


@pytest.fixture
def draft_blueprint(blueprints_table):
    return blueprints_util.create_blueprint_draft(
        tenant_id=TENANT_ID,
        description="A test blueprint",
        document_type="w2",
        fields=[{"name": "employer", "type": "string"}],
    )


@pytest.fixture
def tenant_record(tenants_table):
    from documentai_api.utils.tenants import create_tenant

    return create_tenant(TENANT_ID, display_name=TENANT_ID)


@pytest.fixture
def published_blueprint(blueprints_table, tenant_record, mock_bda):
    draft = blueprints_util.create_blueprint_draft(
        tenant_id=TENANT_ID,
        description="A test blueprint",
        document_type="w2",
        fields=[{"name": "employer", "type": "string"}],
    )
    return blueprints_util.publish_blueprint(TENANT_ID, draft[BlueprintRecord.BLUEPRINT_ID])


# =============================================================================
# create_blueprint_draft
# =============================================================================


def test_create_blueprint_draft_returns_record(draft_blueprint):
    assert draft_blueprint[BlueprintRecord.TENANT_ID] == TENANT_ID
    assert draft_blueprint[BlueprintRecord.STATUS] == BlueprintStatus.DRAFT


# =============================================================================
# publish_blueprint
# =============================================================================


def test_publish_blueprint_persists_blueprint_and_project_arn(published_blueprint):
    assert published_blueprint[BlueprintRecord.BLUEPRINT_ARN] == BLUEPRINT_ARN
    assert published_blueprint[BlueprintRecord.PROJECT_ARN] == PROJECT_ARN
    assert published_blueprint[BlueprintRecord.STATUS] == BlueprintStatus.PUBLISHED


def test_publish_blueprint_raises_for_unknown_blueprint(blueprints_table, tenant_record, mock_bda):
    with pytest.raises(ValueError, match="Blueprint not found"):
        blueprints_util.publish_blueprint(TENANT_ID, "nonexistent-id")


# =============================================================================
# update_blueprint_draft
# =============================================================================


def test_update_draft_updates_description(draft_blueprint):
    bp_id = draft_blueprint[BlueprintRecord.BLUEPRINT_ID]
    updated = blueprints_util.update_blueprint_draft(TENANT_ID, bp_id, description="Updated desc")
    assert updated[BlueprintRecord.DESCRIPTION] == "Updated desc"


def test_update_draft_syncs_schema_to_bda_when_description_changed(published_blueprint, mock_bda):
    bp_id = published_blueprint[BlueprintRecord.BLUEPRINT_ID]
    blueprints_util.update_blueprint_draft(TENANT_ID, bp_id, description="New desc")
    mock_bda.update_blueprint.assert_called_once()


def test_update_draft_does_not_call_bda_for_draft(draft_blueprint, mock_bda):
    bp_id = draft_blueprint[BlueprintRecord.BLUEPRINT_ID]
    blueprints_util.update_blueprint_draft(TENANT_ID, bp_id, description="Renamed")
    mock_bda.update_blueprint.assert_not_called()


def test_update_live_blueprint_raises(published_blueprint):
    bp_id = published_blueprint[BlueprintRecord.BLUEPRINT_ID]
    blueprints_util._blueprints_table.update(TENANT_ID, bp_id, blueprintStatus=BlueprintStatus.LIVE)
    with pytest.raises(ValueError, match="take it offline first"):
        blueprints_util.update_blueprint_draft(TENANT_ID, bp_id, description="New desc")


# =============================================================================
# delete_blueprint
# =============================================================================


def test_delete_draft_soft_deletes_record(draft_blueprint):
    bp_id = draft_blueprint[BlueprintRecord.BLUEPRINT_ID]
    result = blueprints_util.delete_blueprint(TENANT_ID, bp_id)
    assert result is True
    record = blueprints_util.get_blueprint(TENANT_ID, bp_id)
    assert record is not None
    assert record[BlueprintRecord.IS_ACTIVE] is False


def test_delete_published_blueprint_calls_bda_delete(published_blueprint, mock_bda):
    bp_id = published_blueprint[BlueprintRecord.BLUEPRINT_ID]
    blueprints_util.delete_blueprint(TENANT_ID, bp_id)
    mock_bda.delete_blueprint.assert_called_once_with(blueprintArn=BLUEPRINT_ARN)
    mock_bda.update_data_automation_project.assert_called()


def test_delete_live_blueprint_raises(published_blueprint):
    bp_id = published_blueprint[BlueprintRecord.BLUEPRINT_ID]
    blueprints_util._blueprints_table.update(TENANT_ID, bp_id, blueprintStatus=BlueprintStatus.LIVE)
    with pytest.raises(ValueError, match="take it offline first"):
        blueprints_util.delete_blueprint(TENANT_ID, bp_id)


def test_delete_nonexistent_blueprint_returns_false(blueprints_table):
    assert blueprints_util.delete_blueprint(TENANT_ID, "nonexistent-id") is False


# =============================================================================
# get_live_blueprint_project_arn
# =============================================================================


def test_get_live_blueprint_project_arn_returns_arn(published_blueprint):
    bp_id = published_blueprint[BlueprintRecord.BLUEPRINT_ID]
    blueprints_util._blueprints_table.update(TENANT_ID, bp_id, blueprintStatus=BlueprintStatus.LIVE)
    assert blueprints_util.get_live_blueprint_project_arn(TENANT_ID, "w2") == PROJECT_ARN


def test_get_live_blueprint_project_arn_returns_none_when_only_published(published_blueprint):
    assert blueprints_util.get_live_blueprint_project_arn(TENANT_ID, "w2") is None


def test_get_live_blueprint_project_arn_returns_none_for_unknown_tenant(blueprints_table):
    assert blueprints_util.get_live_blueprint_project_arn("unknown-tenant", "w2") is None


# =============================================================================
# Integration tests - full lifecycle against real BDA
# =============================================================================
#
# Requires real AWS credentials and a live BDA endpoint:
#
#     uv run pytest tests/utils/test_blueprints_util.py -m integration
#


@pytest.fixture
def bda_env(reset_env, monkeypatch):
    """Restore BDA_REGION needed for real BDA calls."""
    region = reset_env.get("BDA_REGION") or reset_env.get("AWS_DEFAULT_REGION")
    if not region:
        pytest.skip("BDA_REGION not set in environment")
    monkeypatch.setenv("BDA_REGION", region)


@pytest.fixture
def real_table_env(reset_env, monkeypatch):
    """Restore the real (deployed) table-name env vars - no moto mocking here.

    Unlike blueprints_table/tenant_record, this points the app at whatever
    tables are actually deployed in the target AWS account so calls made
    during the test (including Bedrock calls) hit real AWS, not a mock.
    """
    required = {
        "TENANT_AUTHORED_BLUEPRINTS_TABLE_NAME": None,
        "BLUEPRINTS_DOCUMENT_TYPE_INDEX_NAME": None,
        "TENANTS_TABLE_NAME": None,
    }
    for key in required:
        value = reset_env.get(key)
        if not value:
            pytest.skip(f"{key} not set in environment")
        monkeypatch.setenv(key, value)


@pytest.fixture
def integration_tenant_id():
    """A disposable tenant id scoped to this test run, cleaned up afterward."""
    import uuid

    from documentai_api.utils.tenants import _table as tenants_table
    from documentai_api.utils.tenants import create_tenant

    tenant_id = f"blueprint-integration-{uuid.uuid4()}"
    create_tenant(tenant_id, display_name=tenant_id)
    yield tenant_id
    tenants_table.delete(tenant_id)


@pytest.mark.integration
def test_blueprint_full_lifecycle(
    real_aws_credentials, bda_env, real_table_env, integration_tenant_id
):
    """Draft -> publish -> enable -> [second blueprint + routing check] -> disable -> update -> delete against real AWS.

    Asserts status at each transition, verifies AWS resources are created
    and cleaned up correctly.
    """
    from documentai_api.utils import bda_invoker
    from documentai_api.utils.aws_client_factory import AWSClientFactory

    tenant_id = integration_tenant_id
    bp_id = None
    bp_id_1099 = None

    try:
        # -- 1. Draft ------------------------------------------------------------
        draft = blueprints_util.create_blueprint_draft(
            tenant_id=tenant_id,
            description="Extracts employer name and EIN from a W-2",
            document_type="w2-integration",
            fields=[
                {"name": "employer_name", "type": "string"},
                {"name": "employer_ein", "type": "string"},
            ],
        )
        bp_id = draft[BlueprintRecord.BLUEPRINT_ID]

        assert draft[BlueprintRecord.STATUS] == BlueprintStatus.DRAFT
        assert (
            BlueprintRecord.BLUEPRINT_ARN not in draft
            or draft.get(BlueprintRecord.BLUEPRINT_ARN) is None
        )

        # -- 2. Publish ------------------------------------------------------------
        published = blueprints_util.publish_blueprint(tenant_id, bp_id)

        assert published[BlueprintRecord.STATUS] == BlueprintStatus.PUBLISHED
        blueprint_arn = published[BlueprintRecord.BLUEPRINT_ARN]
        project_arn = published[BlueprintRecord.PROJECT_ARN]
        assert blueprint_arn
        assert blueprint_arn.startswith("arn:aws:bedrock:")
        assert project_arn
        assert project_arn.startswith("arn:aws:bedrock:")

        # Verify BDA blueprint actually exists
        bda = AWSClientFactory.get_bda_client()
        bp_response = bda.get_blueprint(
            blueprintArn=blueprint_arn, blueprintStage=BdaBlueprintStage.LIVE
        )
        assert bp_response["blueprint"]["blueprintArn"] == blueprint_arn

        # -- 3. Enable (go live) ---------------------------------------------------
        live_response = blueprints_util.enable_blueprint(tenant_id, bp_id)

        assert live_response.blueprint_id == bp_id
        live_record = blueprints_util.get_blueprint(tenant_id, bp_id)
        assert live_record[BlueprintRecord.STATUS] == BlueprintStatus.LIVE

        # Routing lookup must resolve to the project ARN
        resolved_arn = blueprints_util.get_live_blueprint_project_arn(tenant_id, "w2-integration")
        assert resolved_arn == project_arn

        # -- 4. Second blueprint (1099) - multi-blueprint project merge -----------
        draft_1099 = blueprints_util.create_blueprint_draft(
            tenant_id=tenant_id,
            description="Extracts payer name and amount from a 1099",
            document_type="1099-integration",
            fields=[{"name": "payer_name", "type": "string"}, {"name": "amount", "type": "string"}],
        )
        bp_id_1099 = draft_1099[BlueprintRecord.BLUEPRINT_ID]
        published_1099 = blueprints_util.publish_blueprint(tenant_id, bp_id_1099)
        blueprint_arn_1099 = published_1099[BlueprintRecord.BLUEPRINT_ARN]

        # Both ARNs must be registered on the shared project
        project_detail = bda.get_data_automation_project(projectArn=project_arn)
        registered_arns = {
            b["blueprintArn"]
            for b in project_detail["project"]["customOutputConfiguration"]["blueprints"]
        }
        assert blueprint_arn in registered_arns
        assert blueprint_arn_1099 in registered_arns

        # resolve_project_arn must route w2-integration to the tenant custom project
        bda_invoker._project_arns_cache = {
            "all": "arn:aws:bedrock:us-east-1:000:data-automation-project/shared"
        }
        assert bda_invoker.resolve_project_arn(None, tenant_id, "w2-integration") == project_arn

        # unknown document type falls back to shared project
        assert (
            bda_invoker.resolve_project_arn(None, tenant_id, "unknown-type")
            == "arn:aws:bedrock:us-east-1:000:data-automation-project/shared"
        )

        bda_invoker._project_arns_cache = None  # reset cache

        # -- 5. Disable (take offline) ---------------------------------------------
        offline_response = blueprints_util.disable_blueprint(tenant_id, bp_id)

        assert offline_response.blueprint_id == bp_id
        offline_record = blueprints_util.get_blueprint(tenant_id, bp_id)
        assert offline_record[BlueprintRecord.STATUS] == BlueprintStatus.PUBLISHED

        # Routing lookup must return None - no live blueprint
        assert blueprints_util.get_live_blueprint_project_arn(tenant_id, "w2-integration") is None

        # -- 5. Update (syncs schema to BDA) --------------------------------------
        updated = blueprints_util.update_blueprint_draft(
            tenant_id,
            bp_id,
            description="Extracts employer name, EIN, and wages from a W-2",
            blueprintFields=[
                {"name": "employer_name", "type": "string"},
                {"name": "employer_ein", "type": "string"},
                {"name": "wages", "type": "number"},
            ],
        )

        assert "wages" in str(updated[BlueprintRecord.FIELDS])

        # Verify BDA schema was updated
        updated_bp = bda.get_blueprint(
            blueprintArn=blueprint_arn, blueprintStage=BdaBlueprintStage.LIVE
        )
        assert "wages" in updated_bp["blueprint"]["schema"]

        # -- 6. Delete (cleans up BDA) ---------------------------------------------
        deleted = blueprints_util.delete_blueprint(tenant_id, bp_id)

        assert deleted is True
        soft_deleted = blueprints_util.get_blueprint(tenant_id, bp_id)
        assert soft_deleted[BlueprintRecord.IS_ACTIVE] is False

        with pytest.raises(botocore.exceptions.ClientError) as exc_info:
            bda.get_blueprint(blueprintArn=blueprint_arn, blueprintStage=BdaBlueprintStage.LIVE)
        assert exc_info.value.response["Error"]["Code"] in (
            "ResourceNotFoundException",
            "ValidationException",
        )
    finally:
        bda = AWSClientFactory.get_bda_client()
        import contextlib

        if bp_id is not None:
            record = blueprints_util._blueprints_table.get(tenant_id, bp_id)
            if record and (arn := record.get(BlueprintRecord.BLUEPRINT_ARN)):
                with contextlib.suppress(Exception):
                    bda.delete_blueprint(blueprintArn=arn)
            blueprints_util._blueprints_table.delete(tenant_id, bp_id)
        if bp_id_1099 is not None:
            record_1099 = blueprints_util._blueprints_table.get(tenant_id, bp_id_1099)
            if record_1099 and (arn_1099 := record_1099.get(BlueprintRecord.BLUEPRINT_ARN)):
                with contextlib.suppress(Exception):
                    bda.delete_blueprint(blueprintArn=arn_1099)
            blueprints_util._blueprints_table.delete(tenant_id, bp_id_1099)

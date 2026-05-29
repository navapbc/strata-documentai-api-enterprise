# tests/e2e/conftest.py
import os
import secrets
from pathlib import Path

import pytest

from documentai_api.logging import get_logger
from documentai_api.utils.auth import _hash_key, deactivate_api_key, generate_api_key

E2E_TENANT_BASE = "e2e-test-tenant"
logger = get_logger(__name__)


_E2E_DIR = Path(__file__).parent


@pytest.fixture(scope="session")
def e2e_tenant_id(worker_id):
    """Per-worker tenant so parallel xdist workers don't wipe each other's data.

    `worker_id` is "master" for a serial run, or "gw0"/"gw1"/... under `-n`.
    Each worker creates its key + documents under this tenant and wipes only it.
    """
    return f"{E2E_TENANT_BASE}-{worker_id}"


def pytest_collection_modifyitems(items):
    """Mark tests under tests/e2e/ as e2e so the default suite skips them.

    This hook receives every collected item in the session, so scope it to
    files under this directory rather than marking the whole suite.
    """
    for item in items:
        if _E2E_DIR in Path(item.fspath).parents:
            item.add_marker(pytest.mark.e2e)


@pytest.fixture(scope="session")
def monkeypatch_session():
    from _pytest.monkeypatch import MonkeyPatch

    mp = MonkeyPatch()
    yield mp
    mp.undo()


@pytest.fixture(scope="session")
def api_key(reset_env, monkeypatch_session, e2e_tenant_id):
    # generate_api_key reads API_KEYS_TABLE_NAME from app config — must be set
    for k in (
        "API_KEYS_TABLE_NAME",
        "AWS_REGION",
        "AWS_PROFILE",
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "AWS_SESSION_TOKEN",
        "DOCUMENTAI_DOCUMENT_METADATA_TABLE_NAME",
        "DOCUMENTAI_DOCUMENT_METADATA_JOB_ID_INDEX_NAME",
        "DOCUMENTAI_DOCUMENT_METADATA_TENANT_INDEX_NAME",
        "DOCUMENTAI_INPUT_LOCATION",
        "DOCUMENTAI_OUTPUT_LOCATION",
    ):
        if v := reset_env.get(k):
            monkeypatch_session.setenv(k, v)

    from documentai_api.config.env import get_aws_config

    get_aws_config.cache_clear()  # ensure config picks up monkeypatch changes

    raw_key, _ = generate_api_key(
        api_key_name=f"e2e-{secrets.token_hex(4)}",
        environment="dev",
        tenant_id=e2e_tenant_id,
        created_by="e2e-suite",
    )
    key_hash = _hash_key(raw_key)

    try:
        yield raw_key
    finally:
        deactivate_api_key(key_hash)


@pytest.fixture(scope="session")
def base_url(reset_env):
    return reset_env.get("BASE_URL", "http://localhost:8000")


def _wipe_e2e_tenant(tenant_id: str) -> None:
    """Delete every document and S3 object owned by the given e2e tenant.

    Best-effort: logs warnings on individual failures rather than raising,
    so a partial cleanup doesn't break the test session.
    """
    if not os.environ.get("E2E_WIPE_TENANT"):
        logger.info("e2e wipe skipped — E2E_WIPE_TENANT not set")
        return

    import boto3

    from documentai_api.config.env import get_aws_config
    from documentai_api.schemas.document_metadata import DocumentMetadata
    from documentai_api.services import ddb as ddb_service
    from documentai_api.utils.s3 import parse_s3_uri

    cfg = get_aws_config()
    table_name = cfg.documentai_document_metadata_table_name
    tenant_index_name = cfg.documentai_document_metadata_tenant_index_name
    input_location = cfg.documentai_input_location

    if not (table_name and tenant_index_name and input_location):
        logger.warning("e2e wipe skipped — required AWS config missing")
        return

    bucket, prefix = parse_s3_uri(input_location)
    s3 = boto3.client("s3")
    deleted_docs = 0
    deleted_objects = 0

    items = ddb_service.query_by_key(
        table_name, tenant_index_name, DocumentMetadata.TENANT_ID, tenant_id
    )

    for record in items:
        object_key = record.get(DocumentMetadata.FILE_NAME) or record.get("objectKey")
        if object_key:
            # Objects are stored under the tenant prefix; FILE_NAME is the bare key.
            tenant_object_key = f"{tenant_id}/{object_key}"
            s3_key = f"{prefix}/{tenant_object_key}" if prefix else tenant_object_key
            try:
                s3.delete_object(Bucket=bucket, Key=s3_key)
                deleted_objects += 1
            except Exception as e:
                logger.warning(f"e2e wipe: failed to delete s3://{bucket}/{s3_key}: {e}")

        try:
            ddb_service.delete_item(
                table_name,
                {DocumentMetadata.FILE_NAME: record[DocumentMetadata.FILE_NAME]},
            )
            deleted_docs += 1
        except Exception as e:
            logger.warning(
                f"e2e wipe: failed to delete doc {record.get(DocumentMetadata.FILE_NAME)}: {e}"
            )

    logger.info(f"e2e wipe: deleted {deleted_docs} doc records, {deleted_objects} s3 objects")


@pytest.fixture(scope="session", autouse=True)
def _sweep_stale_e2e_documents(_sweep_stale_e2e_keys, e2e_tenant_id):
    """Wipe this worker's e2e tenant before the run starts.

    Belt-and-suspenders — `cleanup_e2e_tenant` handles the happy path; this
    handles 'previous run crashed and left documents behind.'
    """
    _wipe_e2e_tenant(e2e_tenant_id)
    return


@pytest.fixture(scope="session", autouse=True)
def cleanup_e2e_tenant(api_key, e2e_tenant_id):
    """Delete every document this worker created in its e2e tenant.

    Runs after api_key teardown — depends on it so the key still exists if
    we ever want to use the API for cleanup instead of going direct to DDB/S3.
    """
    yield
    _wipe_e2e_tenant(e2e_tenant_id)


@pytest.fixture(scope="session", autouse=True)
def _sweep_stale_e2e_keys():
    """Delete e2e api keys orphaned by prior crashed runs.

    Runs once before any tests. Looks for keys named 'e2e-*' older than 1 hour.
    """
    from datetime import UTC, datetime, timedelta

    from documentai_api.config.env import get_aws_config
    from documentai_api.schemas.api_key import ApiKeyRecord
    from documentai_api.services import ddb as ddb_service

    table_name = get_aws_config().api_keys_table_name
    if not table_name:
        return

    cutoff = (datetime.now(UTC) - timedelta(hours=1)).isoformat()
    swept = 0

    # API keys table is small — full scan is fine; no GSI on api_key_name
    start_key = None
    while True:
        kwargs = {}
        if start_key:
            kwargs["ExclusiveStartKey"] = start_key
        items, start_key = ddb_service.scan(table_name, **kwargs)

        for record in items:
            name = record.get(ApiKeyRecord.API_KEY_NAME, "")
            created = record.get(ApiKeyRecord.CREATED_AT, "")
            if name.startswith("e2e-") and created and created < cutoff:
                ddb_service.delete_item(
                    table_name,
                    {ApiKeyRecord.KEY_HASH: record[ApiKeyRecord.KEY_HASH]},
                )
                swept += 1

        if not start_key:
            break

    if swept:
        logger.info(f"e2e: swept {swept} orphaned api keys")

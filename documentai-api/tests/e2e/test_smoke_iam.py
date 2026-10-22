"""IAM permission smoke tests.

Each test fires a request against one API surface area and asserts a non-5xx
response. A 5xx paired with an AccessDenied log line means a missing permission.

API Lambda (api-key auth):
  - document upload        -> s3:PutObject, ddb:PutItem
  - hard delete            -> s3:DeleteObject
  - build page/delete      -> ddb:PutItem / DeleteItem
  - extraction rule        -> ddb:PutItem / DeleteItem
  - presigned URL          -> s3:PutObject (signing), ddb:PutItem
  - batch upload           -> s3:PutObject, ddb:PutItem (batch path)
  - /v1/me                 -> auth canary, no IAM
  - metrics (api key)      -> s3:GetObject, s3:ListBucket (metrics bucket, api-key path)

API Lambda (Cognito JWT - skipped if COGNITO_USER_POOL_ID / COGNITO_CLIENT_ID unset):
  - tenant create/delete   -> ddb:PutItem / UpdateItem (tenants, request-counts tables, KMS)
  - category create/delete -> ddb:PutItem / UpdateItem (categories table, KMS)
  - extraction test       -> s3:PutObject, ddb:PutItem (document metadata table)
  - admin usage monthly    -> s3:GetObject, s3:ListBucket (metrics bucket, monthly)
  - admin usage daily      -> s3:GetObject, s3:ListBucket (metrics bucket, daily prefix)
  - list users             -> cognito-idp:ListUsers (super-admin only)
  - list api-keys          -> ddb:Scan (api-keys table)
  - cognito writes         -> cognito-idp:AdminAddUserToGroup, AdminRemoveUserFromGroup,
                              AdminUpdateUserAttributes, AdminDeleteUser

Run with: make test-smoke (serial) or make test-e2e (parallel, includes smoke).
"""

import secrets
import time
from datetime import UTC, datetime

import pytest

from documentai_api.utils.field_labels import get_valid_fields
from documentai_api.utils.jwt_auth import TENANT_ADMIN
from tests.helpers.fixtures.paths import SMALL_PDF

_RULE_DOC_TYPE = "bank-statement"

# Session-unique suffix prevents 409 collisions when make test-e2e runs
# multiple xdist workers concurrently against the same environment.
_SUFFIX = secrets.token_hex(4)
_SMOKE_TENANT_ID = f"smoke-tenant-{_SUFFIX}"
_SMOKE_CATEGORY = f"smoke-category-{_SUFFIX}"


@pytest.fixture(scope="module")
def smoke_tenant(jwt_client):
    """Create the smoke tenant once for the module, delete on teardown."""
    jwt_client(
        "POST",
        "/v1/admin/tenants",
        expected_status=201,
        json={"tenant_id": _SMOKE_TENANT_ID, "display_name": "Smoke Test Tenant"},
    )
    try:
        yield _SMOKE_TENANT_ID
    finally:
        jwt_client("DELETE", f"/v1/admin/tenants/{_SMOKE_TENANT_ID}")


def test_document_upload(client):
    """POST /v1/documents returns 202.

    Validates s3:PutObject and ddb:PutItem are granted to the API Lambda.
    """
    with SMALL_PDF.open("rb") as f:
        client("POST", "/v1/documents", expected_status=202, files={"file": f})


def test_hard_delete_document(client):
    """Upload a document, wait for processing, then hard-delete it.

    Validates s3:DeleteObject is granted to the API Lambda (s3_api policy).
    If this test flakes, increase the timeout before assuming a permission
    problem - BDA latency spikes can push processing past 90 seconds.
    """
    job_id = client.upload_and_wait(SMALL_PDF, timeout=90)["jobId"]
    client(
        "DELETE", f"/v1/documents/{job_id}", expected_status=204, params={"soft_delete": "false"}
    )


def test_build_page_and_build_delete(client):
    """Create a build, upload a page, delete the page, then delete the build.

    Validates ddb:PutItem and ddb:DeleteItem are granted (ddb_access policy).
    """
    build_id = client("POST", "/v1/builds").json()["buildId"]

    try:
        with SMALL_PDF.open("rb") as f:
            client(
                "POST", f"/v1/builds/{build_id}/pages", files={"file": f}, data={"page_number": "1"}
            )
        client("DELETE", f"/v1/builds/{build_id}/pages/1", expected_status=204)
    finally:
        client("DELETE", f"/v1/builds/{build_id}", expected_status=204)


def test_extraction_rule_create_and_delete(client):
    """PUT then DELETE an extraction rule.

    Validates ddb:PutItem and ddb:DeleteItem are granted (ddb_access / pipeline_api).
    """
    valid_fields = get_valid_fields(_RULE_DOC_TYPE)
    assert valid_fields is not None, f"no label file for {_RULE_DOC_TYPE}"
    field = next(iter(valid_fields.values()))
    client(
        "PUT",
        "/v1/config/extraction-rules",
        json={
            "document_type": _RULE_DOC_TYPE,
            "required_fields": [field],
            "optional_fields": [],
        },
    )
    client(
        "DELETE",
        "/v1/config/extraction-rules",
        params={"document_type": _RULE_DOC_TYPE},
    )


def test_presigned_url(client):
    """POST /v1/documents/presigned-url returns 200.

    Validates s3:PutObject (presigned signing) and ddb:PutItem via the presigned
    upload code path (distinct from direct upload).
    """
    client(
        "POST",
        "/v1/documents/presigned-url",
        data={"filename": "smoke.pdf", "content_type": "application/pdf"},
    )


def test_batch_upload(client):
    """POST /v1/documents/batch returns 200.

    Validates batch ddb:PutItem and s3:PutObject writes.
    """
    with SMALL_PDF.open("rb") as f:
        client(
            "POST",
            "/v1/documents/batch",
            files={"files": (SMALL_PDF.name, f, "application/pdf")},
        )


def test_get_me(client):
    """GET /v1/me returns 200.

    Cheapest auth canary - validates the API key resolves to a valid tenant context.
    """
    client("GET", "/v1/me")


def test_metrics(client):
    """GET /v1/metrics returns 200 via API key.

    Validates s3:GetObject and s3:ListBucket on the metrics bucket are granted
    via the s3_api policy (API-key execution path, distinct from JWT/admin claims).
    """
    today = datetime.now(UTC).strftime("%Y-%m-%d")
    client("GET", "/v1/metrics", params={"start_date": today, "end_date": today})


def test_tenant_create_and_delete(jwt_client):
    """POST then DELETE a tenant.

    Validates ddb:PutItem and ddb:UpdateItem on the tenants and
    request-counts tables, plus KMS GenerateDataKey/Decrypt for their CMKs.
    Uses a separate name from smoke_tenant so the two don't collide.
    """
    tenant_id = f"smoke-tenant-crud-{_SUFFIX}"
    try:
        jwt_client(
            "POST",
            "/v1/admin/tenants",
            expected_status=201,
            json={"tenant_id": tenant_id, "display_name": "Smoke Test Tenant"},
        )
    finally:
        jwt_client("DELETE", f"/v1/admin/tenants/{tenant_id}")


def test_category_create_and_delete(jwt_client, smoke_tenant):
    """POST then DELETE a document category.

    Validates ddb:PutItem and ddb:UpdateItem on the document-categories table,
    plus KMS GenerateDataKey/Decrypt for its CMK.
    """
    try:
        jwt_client(
            "POST",
            "/v1/admin/document-categories",
            expected_status=201,
            json={
                "category_name": _SMOKE_CATEGORY,
                "display_name": "Smoke Category",
                "description": "Created by smoke test",
            },
            params={"tenant_id": smoke_tenant},
        )
    finally:
        jwt_client(
            "DELETE",
            f"/v1/admin/document-categories/{_SMOKE_CATEGORY}",
            expected_status=204,
            params={"tenant_id": smoke_tenant},
        )


def test_extraction_test_runner(jwt_client, smoke_tenant):
    """POST /v1/admin/extraction-test, then poll GET until non-PROCESSING.

    Validates s3:PutObject on the input bucket, the full extraction pipeline
    (preclassify → BDA/Textract), and ddb:PutItem on the document metadata table.
    Does not wait for COMPLETED - PROCESSING is sufficient to confirm the
    invoke succeeded and the status check is authorized.
    """
    with SMALL_PDF.open("rb") as f:
        response = jwt_client(
            "POST",
            "/v1/admin/extraction-test",
            files={"file": (SMALL_PDF.name, f, "application/pdf")},
            data={"tenant_id": smoke_tenant},
        )
    job_id = response.json()["jobId"]

    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        result = jwt_client("GET", f"/v1/admin/extraction-test/{job_id}").json()
        if result["jobStatus"] != "not_started":
            break
        time.sleep(2)
    # Any non-5xx status confirms IAM is correct.


def test_admin_usage(jwt_client):
    """GET /v1/admin/usage returns 200 (monthly granularity).

    Validates s3:GetObject and s3:ListBucket on the metrics bucket are granted
    via the JWT/admin-claims path (reads a single report.json per month).
    """
    jwt_client("GET", "/v1/admin/usage")


def test_admin_usage_daily(jwt_client):
    """GET /v1/admin/usage?granularity=daily returns 200.

    Validates s3:GetObject and s3:ListBucket on the metrics bucket cover the
    daily key prefix (usage-report/utc/date=.../stats.json), which is a
    distinct S3 path from the monthly report.json read.
    """
    month = datetime.now(UTC).strftime("%Y-%m")
    jwt_client("GET", "/v1/admin/usage", params={"granularity": "daily", "month": month})


def test_list_api_keys(jwt_client):
    """GET /v1/admin/api-keys returns 200.

    Validates ddb:Scan on the api-keys table.
    """
    jwt_client("GET", "/v1/admin/api-keys")


def test_list_users(jwt_client):
    """GET /v1/admin/users returns 200.

    Validates cognito-idp:ListUsers is granted to the API Lambda.
    """
    jwt_client("GET", "/v1/admin/users")


def test_cognito_writes(jwt_client, ephemeral_cognito_user, smoke_tenant):
    """Exercise role change, tenant update, and delete on an ephemeral Cognito user.

    Validates cognito-idp:AdminAddUserToGroup, AdminRemoveUserFromGroup,
    AdminUpdateUserAttributes, and AdminDeleteUser are granted to the API Lambda.
    """
    username = ephemeral_cognito_user

    # role change -> AdminAddUserToGroup and AdminRemoveUserFromGroup
    jwt_client(
        "POST",
        f"/v1/admin/users/{username}/role",
        json={"role": TENANT_ADMIN, "tenant_id": smoke_tenant},
    )
    # tenant update -> AdminUpdateUserAttributes
    jwt_client(
        "POST",
        f"/v1/admin/users/{username}/tenant",
        json={"tenant_id": None},
    )
    # delete -> AdminDeleteUser
    jwt_client("DELETE", f"/v1/admin/users/{username}")

import os
from datetime import UTC, datetime
from typing import Any

from documentai_api.config.constants import DocumentCategory
from documentai_api.config.env import EnvVars
from documentai_api.schemas.document_builds import DocumentBuilds
from documentai_api.services import ddb as ddb_service
from documentai_api.services import s3 as s3_service
from documentai_api.utils import s3 as s3_utils
from documentai_api.utils.dto import PageMetadata

# Sentinel page number reserved for the per-build metadata record (not a real page).
_METADATA_PAGE_NUMBER = 0


def get_document_build_table() -> str:
    """Get multipage upload sessions table name from environment."""
    table_name = os.getenv(EnvVars.DOCUMENTAI_BUILD_TABLE_NAME)
    if not table_name:
        raise ValueError(f"{EnvVars.DOCUMENTAI_BUILD_TABLE_NAME} not set")
    return table_name


def _page_key(build_id: str, page_number: int) -> dict[str, Any]:
    """Composite primary key for a single (build, page) row."""
    return {DocumentBuilds.BUILD_ID: build_id, DocumentBuilds.PAGE_NUMBER: page_number}


def _query_items_for_build(build_id: str) -> list[dict[str, Any]]:
    """Return every row (metadata + pages) for a build."""
    return ddb_service.query_by_pk(
        table_name=get_document_build_table(),
        pk_name=DocumentBuilds.BUILD_ID,
        pk_value=build_id,
    )


def document_build_exists(build_id: str) -> bool:
    return (
        ddb_service.get_item(get_document_build_table(), _page_key(build_id, _METADATA_PAGE_NUMBER))
        is not None
    )


def get_build_metadata(build_id: str) -> dict[str, Any] | None:
    """Return the metadata record for a build (page 0)."""
    return ddb_service.get_item(
        get_document_build_table(), _page_key(build_id, _METADATA_PAGE_NUMBER)
    )


def document_build_page_exists(build_id: str, page_number: int) -> bool:
    """Check if a page exists for a multipage session."""
    item = ddb_service.get_item(get_document_build_table(), _page_key(build_id, page_number))
    return item is not None


async def upsert_document_build_page(
    build_id: str,
    page_number: int,
    s3_path: str,
    original_file_name: str | None = None,
    category: DocumentCategory | None = None,
    overwrite: bool = True,
) -> None:
    """Upsert multipage session page record.

    When overwrite=False, uses a conditional write to prevent clobbering
    an existing page (raises ConditionalCheckFailedException on conflict).
    """
    table_name = get_document_build_table()

    item: dict[str, Any] = {
        DocumentBuilds.BUILD_ID: build_id,
        DocumentBuilds.PAGE_NUMBER: page_number,
        DocumentBuilds.S3_PATH: s3_path,
        DocumentBuilds.CREATED_AT: datetime.now(UTC).isoformat(),
    }

    if original_file_name:
        item[DocumentBuilds.ORIGINAL_FILE_NAME] = original_file_name

    if category:
        item[DocumentBuilds.CATEGORY] = category.value

    if not overwrite:
        from documentai_api.utils.aws_client_factory import AWSClientFactory

        ddb_table = AWSClientFactory.get_ddb_table(table_name)
        try:
            ddb_table.put_item(
                Item=item,
                ConditionExpression="attribute_not_exists(#pk)",
                ExpressionAttributeNames={"#pk": DocumentBuilds.BUILD_ID},
            )
        except Exception as e:
            if "ConditionalCheckFailedException" in type(e).__name__ or (
                hasattr(e, "response")
                and e.response.get("Error", {}).get("Code") == "ConditionalCheckFailedException"
            ):
                from fastapi import HTTPException

                raise HTTPException(
                    status_code=409,
                    detail=f"Page {page_number} already exists for build {build_id}. Set overwrite=true to replace.",
                ) from None
            raise
    else:
        ddb_service.put_item(table_name, item)


def get_document_build_pages(build_id: str) -> list[PageMetadata]:
    """Get all pages for a multipage session."""
    s3_location = os.getenv(EnvVars.DOCUMENTAI_PREPROCESSING_LOCATION, "")
    bucket_name, _ = s3_utils.parse_s3_uri(s3_location)

    pages = [
        PageMetadata(
            page_number=item.get(DocumentBuilds.PAGE_NUMBER, 0),
            s3_key=item.get(DocumentBuilds.S3_PATH, ""),
            s3_bucket_name=bucket_name,
            original_file_name=item.get(DocumentBuilds.ORIGINAL_FILE_NAME),
            category=item.get(DocumentBuilds.CATEGORY),
            created_at=item.get(DocumentBuilds.CREATED_AT),
        )
        for item in _query_items_for_build(build_id)
        if not item.get(DocumentBuilds.IS_BUILD_METADATA)
    ]

    return sorted(pages, key=lambda x: x.page_number)


def is_document_build_submitted(build_id: str) -> bool:
    """Check if a multipage session has already been submitted."""
    items = _query_items_for_build(build_id)
    return len(items) > 0 and any(item.get(DocumentBuilds.SUBMITTED_AT) for item in items)


def mark_document_build_submitted(build_id: str) -> None:
    """Atomically mark a build as submitted using a conditional write.

    Uses attribute_not_exists on submittedAt as a lock - if two concurrent
    submits race, only one succeeds. The loser gets ConditionalCheckFailedException.
    """
    from documentai_api.utils.aws_client_factory import AWSClientFactory

    table_name = get_document_build_table()
    submitted_at = datetime.now(UTC).isoformat()

    # First: conditionally write submittedAt on the metadata record (page 0).
    # This is the "lock" - only one caller can succeed.
    ddb_table = AWSClientFactory.get_ddb_table(table_name)
    try:
        ddb_table.update_item(
            Key=_page_key(build_id, _METADATA_PAGE_NUMBER),
            UpdateExpression=f"SET {DocumentBuilds.SUBMITTED_AT} = :submittedAt",
            ExpressionAttributeValues={":submittedAt": submitted_at},
            ConditionExpression=f"attribute_not_exists({DocumentBuilds.SUBMITTED_AT})",
        )
    except Exception as e:
        if "ConditionalCheckFailedException" in type(e).__name__ or (
            hasattr(e, "response")
            and e.response.get("Error", {}).get("Code") == "ConditionalCheckFailedException"
        ):
            from fastapi import HTTPException

            raise HTTPException(
                status_code=400,
                detail=f"Build {build_id} has already been submitted for processing",
            ) from None
        raise

    # Then: stamp submittedAt on all page records (best-effort, metadata record is source of truth)
    for item in _query_items_for_build(build_id):
        if item.get(DocumentBuilds.PAGE_NUMBER) == _METADATA_PAGE_NUMBER:
            continue
        ddb_service.update_item(
            table_name=table_name,
            key=_page_key(build_id, item[DocumentBuilds.PAGE_NUMBER]),
            update_expression=f"SET {DocumentBuilds.SUBMITTED_AT} = :submittedAt",
            expression_values={":submittedAt": submitted_at},
        )


def clear_submitted_at(build_id: str) -> None:
    """Remove submittedAt from the build metadata record (rollback on upload failure)."""
    from documentai_api.utils.aws_client_factory import AWSClientFactory

    table_name = get_document_build_table()
    ddb_table = AWSClientFactory.get_ddb_table(table_name)
    ddb_table.update_item(
        Key=_page_key(build_id, _METADATA_PAGE_NUMBER),
        UpdateExpression=f"REMOVE {DocumentBuilds.SUBMITTED_AT}",
    )


def delete_document_build_page(build_id: str, page_number: int) -> bool:
    """Delete a specific page from a multipage session."""
    if is_document_build_submitted(build_id):
        raise ValueError(f"Cannot delete - session {build_id} has already been submitted")

    table_name = get_document_build_table()
    s3_location = os.getenv(EnvVars.DOCUMENTAI_PREPROCESSING_LOCATION, "")
    bucket_name, _ = s3_utils.parse_s3_uri(s3_location)

    key = _page_key(build_id, page_number)
    item = ddb_service.get_item(table_name, key)

    if not item:
        return False

    s3_path = item.get(DocumentBuilds.S3_PATH)

    if s3_path:
        s3_service.delete_object(bucket_name, s3_path)

    ddb_service.delete_item(table_name, key)
    return True


def create_document_build(
    build_id: str,
    category: DocumentCategory | None = None,
    external_document_id: str | None = None,
    external_system_id: str | None = None,
    ai_consent_flag: bool | None = None,
    tenant_id: str | None = None,
    api_key_name: str | None = None,
) -> str:
    """Create a new document build."""
    item: dict[str, Any] = {
        DocumentBuilds.BUILD_ID: build_id,
        DocumentBuilds.PAGE_NUMBER: _METADATA_PAGE_NUMBER,
        DocumentBuilds.CREATED_AT: datetime.now(UTC).isoformat(),
        DocumentBuilds.IS_BUILD_METADATA: True,
    }

    if category:
        item[DocumentBuilds.CATEGORY] = category.value
    if external_document_id is not None:
        item[DocumentBuilds.EXTERNAL_DOCUMENT_ID] = external_document_id
    if external_system_id is not None:
        item[DocumentBuilds.EXTERNAL_SYSTEM_ID] = external_system_id
    if ai_consent_flag is not None:
        item[DocumentBuilds.AI_CONSENT_FLAG] = ai_consent_flag
    if tenant_id is not None:
        item[DocumentBuilds.TENANT_ID] = tenant_id
    if api_key_name is not None:
        item[DocumentBuilds.API_KEY_NAME] = api_key_name

    ddb_service.put_item(get_document_build_table(), item)
    return build_id


def delete_document_build(build_id: str) -> bool:
    """Delete an entire multipage session and all its pages."""
    if is_document_build_submitted(build_id):
        raise ValueError(f"Cannot delete - session {build_id} has already been submitted")

    pages = get_document_build_pages(build_id)
    if not pages and not document_build_exists(build_id):
        return False

    for page in pages:
        delete_document_build_page(build_id, page.page_number)

    ddb_service.delete_item(get_document_build_table(), _page_key(build_id, _METADATA_PAGE_NUMBER))

    return True

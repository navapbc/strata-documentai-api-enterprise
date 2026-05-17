import os
from datetime import UTC, datetime
from typing import Any

from documentai_api.config.constants import DocumentCategory
from documentai_api.config.env import EnvVars
from documentai_api.schemas.document_builds import DocumentBuilds
from documentai_api.services import ddb as ddb_service
from documentai_api.services import s3 as s3_service
from documentai_api.utils import s3 as s3_utils
from documentai_api.utils.models import PageMetadata

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
) -> None:
    """Upsert multipage session page record."""
    table_name = get_document_build_table()

    item = {
        DocumentBuilds.BUILD_ID: build_id,
        DocumentBuilds.PAGE_NUMBER: page_number,
        DocumentBuilds.S3_PATH: s3_path,
        DocumentBuilds.CREATED_AT: datetime.now(UTC).isoformat(),
    }

    if original_file_name:
        item[DocumentBuilds.ORIGINAL_FILE_NAME] = original_file_name

    if category:
        item[DocumentBuilds.CATEGORY] = category.value

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
    """Mark all pages in a multipage session as submitted."""
    table_name = get_document_build_table()
    submitted_at = datetime.now(UTC).isoformat()
    for item in _query_items_for_build(build_id):
        ddb_service.update_item(
            table_name=table_name,
            key=_page_key(build_id, item[DocumentBuilds.PAGE_NUMBER]),
            update_expression=f"SET {DocumentBuilds.SUBMITTED_AT} = :{DocumentBuilds.SUBMITTED_AT}",
            expression_values={f":{DocumentBuilds.SUBMITTED_AT}": submitted_at},
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


def create_document_build(build_id: str, category: DocumentCategory | None = None) -> str:
    """Create a new document build."""
    item: dict[str, Any] = {
        DocumentBuilds.BUILD_ID: build_id,
        DocumentBuilds.PAGE_NUMBER: _METADATA_PAGE_NUMBER,
        DocumentBuilds.CREATED_AT: datetime.now(UTC).isoformat(),
        DocumentBuilds.IS_BUILD_METADATA: True,
    }

    if category:
        item[DocumentBuilds.CATEGORY] = category.value

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

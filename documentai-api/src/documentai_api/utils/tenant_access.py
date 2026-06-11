"""Tenant validation dependencies."""

from typing import Annotated, Any

from fastapi import Depends, HTTPException

from documentai_api.schemas.document_batches import DocumentBatches
from documentai_api.schemas.document_builds import DocumentBuilds
from documentai_api.schemas.document_metadata import DocumentMetadata
from documentai_api.utils.auth import UserContext, get_user_context_from_api_key
from documentai_api.utils.batch_operations import get_batch
from documentai_api.utils.document_build import get_build_metadata

# TODO: Have validate_batch_tenant_access and validate_build_tenant_access return the
# fetched record to avoid duplicate DDB reads in the endpoint body.


def validate_document_tenant_access(
    ddb_record: dict[str, Any] | None, tenant_id: str, job_id: str
) -> None:
    """Raise 404 if record doesn't exist or tenant doesn't match."""
    if not ddb_record or ddb_record.get(DocumentMetadata.TENANT_ID) != tenant_id:
        raise HTTPException(status_code=404, detail=f"Job ID {job_id} not found")


def validate_batch_tenant_access(
    batch_id: str, auth: Annotated[UserContext, Depends(get_user_context_from_api_key)]
) -> None:
    """Dependency: raise 404 if batch doesn't exist or tenant doesn't match."""
    batch = get_batch(batch_id)
    if not batch or batch.get(DocumentBatches.TENANT_ID) != auth.tenant_id:
        raise HTTPException(status_code=404, detail=f"Batch {batch_id} not found")


def validate_build_tenant_access(
    build_id: str, auth: Annotated[UserContext, Depends(get_user_context_from_api_key)]
) -> None:
    """Dependency: raise 404 if build doesn't exist or tenant doesn't match."""
    metadata = get_build_metadata(build_id)
    if not metadata or metadata.get(DocumentBuilds.TENANT_ID) != auth.tenant_id:
        raise HTTPException(status_code=404, detail=f"Build {build_id} not found")

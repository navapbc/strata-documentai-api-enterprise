"""Document build endpoints for multi-page upload + submission."""

import os
import uuid
from io import BytesIO
from typing import Annotated

from fastapi import APIRouter, Depends, Form, Header, HTTPException, Request, Response, UploadFile

from documentai_api.config.constants import (
    DocumentBuildStatus,
    DocumentCategory,
    ProcessStatus,
)
from documentai_api.config.env import EnvVars, get_aws_config
from documentai_api.logging import get_logger
from documentai_api.models.api_responses import (
    BuildCreatedResponse,
    BuildDetailsResponse,
    BuildPageBatchItem,
    BuildPageItem,
    BuildPagesBatchResponse,
    BuildPageUploadResponse,
    BuildSubmitAsyncResponse,
    JobStatusResponse,
)
from documentai_api.utils.auth import verify_api_key
from documentai_api.utils.document_build import (
    create_document_build,
    delete_document_build,
    delete_document_build_page,
    document_build_exists,
    document_build_page_exists,
    get_document_build_pages,
    is_document_build_submitted,
    mark_document_build_submitted,
    upsert_document_build_page,
)
from documentai_api.utils.pdf import merge_pages_to_pdf
from documentai_api.utils.s3 import parse_s3_uri
from documentai_api.utils.uploads import (
    upload_document_for_processing,
    validate_file_type,
)

logger = get_logger(__name__)

router = APIRouter()


async def add_page_to_build(
    file: UploadFile,
    build_id: str,
    page_number: int,
    category: DocumentCategory | None = None,
    trace_id: str | None = None,
) -> BuildPageBatchItem:
    """Upload one page's bytes to S3 and upsert its DDB record."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    actual_content_type = await validate_file_type(file)
    logger.info(
        f"Adding page to build {build_id}; page {page_number}; "
        f"filename: {file.filename}; category: {category}; content-type: {actual_content_type}"
    )

    file.file.seek(0)
    file_extension = file.filename.split(".")[-1]
    unique_file_name = f"{build_id}/page-{page_number}.{file_extension}"

    s3_location = os.getenv(EnvVars.DOCUMENTAI_PREPROCESSING_LOCATION, "")
    dest_path = f"{s3_location}/{unique_file_name}"

    await upload_document_for_processing(
        src_file=file.file,
        dest_path=dest_path,
        original_file_name=file.filename,
        content_type=actual_content_type,
        user_provided_document_category=category,
        trace_id=trace_id,
        build_id=build_id,
    )

    _, prefix = parse_s3_uri(s3_location)
    s3_path = f"{prefix}/{unique_file_name}" if prefix else unique_file_name

    await upsert_document_build_page(
        build_id=build_id,
        page_number=page_number,
        s3_path=s3_path,
        original_file_name=file.filename,
        category=category,
    )

    return BuildPageBatchItem(page_number=page_number, file_name=file.filename)


@router.post(
    "/v1/builds",
    name="postDocumentBuild",
    dependencies=[Depends(verify_api_key)],
)
async def create_build(
    response: Response,
    category: Annotated[
        DocumentCategory | None, Form(description="Type of document being uploaded")
    ] = None,
    trace_id: Annotated[str | None, Header(alias="X-Trace-ID")] = None,
) -> BuildCreatedResponse:
    """Create a new document build for multi-page upload."""
    if not trace_id:
        trace_id = str(uuid.uuid4())

    build_id = str(uuid.uuid4())
    create_document_build(build_id, category)

    response.headers["X-Trace-ID"] = trace_id
    return BuildCreatedResponse(
        build_id=build_id,
        message="Build created successfully",
    )


@router.post(
    "/v1/builds/{build_id}/pages",
    name="postDocumentBuildPage",
    dependencies=[Depends(verify_api_key)],
)
async def upload_document_build_page(
    request: Request,
    response: Response,
    file: UploadFile,
    build_id: str,
    page_number: Annotated[int | None, Form(description="Page number (1-indexed)")] = None,
    overwrite: Annotated[bool, Form(description="Allow overwriting existing page")] = False,
    category: Annotated[
        DocumentCategory | None, Form(description="Type of document being uploaded")
    ] = None,
    trace_id: Annotated[str | None, Header(alias="X-Trace-ID")] = None,
) -> BuildPageUploadResponse:
    """Upload a single page for multi-page document processing."""
    try:
        if not trace_id:
            trace_id = str(uuid.uuid4())

        if page_number is None:
            pages = get_document_build_pages(build_id)
            page_number = max((p.page_number for p in pages), default=0) + 1

        if document_build_page_exists(build_id, page_number) and not overwrite:
            raise HTTPException(
                status_code=409,
                detail=f"Page {page_number} already exists for build {build_id}. Set overwrite=true to replace.",
            )

        result = await add_page_to_build(file, build_id, page_number, category, trace_id)

        response.headers["X-Trace-ID"] = trace_id
        return BuildPageUploadResponse(
            build_id=build_id,
            page_number=result.page_number,
            file_name=result.file_name,
            message="Page uploaded successfully",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading document build page {page_number} for build {build_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to upload page") from e


@router.post(
    "/v1/builds/{build_id}/pages/batch",
    name="postDocumentBuildPageBatch",
    dependencies=[Depends(verify_api_key)],
)
async def upload_document_build_pages_batch(
    request: Request,
    response: Response,
    files: list[UploadFile],
    build_id: str,
    category: Annotated[
        DocumentCategory | None, Form(description="Type of document being uploaded")
    ] = None,
    trace_id: Annotated[str | None, Header(alias="X-Trace-ID")] = None,
) -> BuildPagesBatchResponse:
    """Upload multiple pages to a document build in one request."""
    try:
        if not trace_id:
            trace_id = str(uuid.uuid4())

        # Validate every file up front so a bad file doesn't leave partial uploads behind.
        for file in files:
            logger.debug(f"Validating file {file.filename} in batch upload for build {build_id}")
            await validate_file_type(file)

        existing_pages = get_document_build_pages(build_id)
        next_page_number = max((p.page_number for p in existing_pages), default=0) + 1

        results: list[BuildPageBatchItem] = []
        for file in files:
            result = await add_page_to_build(file, build_id, next_page_number, category, trace_id)
            results.append(result)
            next_page_number += 1

        response.headers["X-Trace-ID"] = trace_id
        page_word = "page" if len(results) == 1 else "pages"
        return BuildPagesBatchResponse(
            build_id=build_id,
            pages_added=len(results),
            pages=results,
            message=f"{len(results)} {page_word} uploaded successfully",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading batch pages for build {build_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to upload pages") from e


@router.post(
    "/v1/builds/{build_id}/submit",
    name="postDocumentBuildSubmit",
    dependencies=[Depends(verify_api_key)],
    response_model=BuildSubmitAsyncResponse | JobStatusResponse,
)
async def submit_document_build(
    request: Request,
    response: Response,
    build_id: str,
    trace_id: Annotated[str | None, Header(alias="X-Trace-ID")] = None,
    wait: bool = False,
    timeout: int = 120,
) -> BuildSubmitAsyncResponse | JobStatusResponse:
    """Submit a multi-page build for processing."""
    try:
        if is_document_build_submitted(build_id):
            raise HTTPException(
                status_code=400,
                detail=f"Build {build_id} has already been submitted for processing",
            )

        pages = get_document_build_pages(build_id)

        if not pages:
            raise HTTPException(status_code=404, detail=f"Build {build_id} not found")

        merged_pdf_bytes = merge_pages_to_pdf(pages)

        if not trace_id:
            trace_id = str(uuid.uuid4())

        job_id = str(uuid.uuid4())
        unique_file_name = f"document-build-{build_id}-{uuid.uuid4()}.pdf"
        category_str = pages[0].category
        category = DocumentCategory(category_str) if category_str else None

        input_location = get_aws_config().documentai_input_location
        if not input_location:
            raise HTTPException(
                status_code=500, detail="DOCUMENTAI_INPUT_LOCATION environment variable not set"
            )

        await upload_document_for_processing(
            src_file=BytesIO(merged_pdf_bytes),
            dest_path=f"{input_location}/{unique_file_name}",
            original_file_name=unique_file_name,
            content_type="application/pdf",
            user_provided_document_category=category,
            job_id=job_id,
            trace_id=trace_id,
            build_id=build_id,
        )

        mark_document_build_submitted(build_id)

        response.headers["X-Trace-ID"] = trace_id

        if not wait:
            return BuildSubmitAsyncResponse(
                job_id=job_id,
                build_id=build_id,
                job_status=ProcessStatus.NOT_STARTED.value,
                message="Document build submitted successfully",
                page_count=len(pages),
            )
        else:
            # Lazy import: app.py imports this module's router, so avoid a top-level cycle.
            from documentai_api.app import get_v1_document_processing_results

            return await get_v1_document_processing_results(job_id, timeout)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error submitting document build {build_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to submit document build") from e


@router.get(
    "/v1/builds/{build_id}",
    name="getDocumentBuildStatus",
    dependencies=[Depends(verify_api_key)],
)
async def get_document_build(build_id: str) -> BuildDetailsResponse:
    """Get document build details including all uploaded pages."""
    try:
        if not document_build_exists(build_id):
            raise HTTPException(status_code=404, detail=f"Build {build_id} not found")

        pages = get_document_build_pages(build_id)
        build_status = (
            DocumentBuildStatus.SUBMITTED
            if is_document_build_submitted(build_id)
            else DocumentBuildStatus.NOT_SUBMITTED
        )

        return BuildDetailsResponse(
            build_id=build_id,
            build_status=build_status.value,
            page_count=len(pages),
            pages=[
                BuildPageItem(
                    page_number=page.page_number,
                    original_file_name=page.original_file_name,
                    created_at=page.created_at,
                    category=page.category,
                )
                for page in pages
            ],
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving build {build_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve build") from e


@router.delete(
    "/v1/builds/{build_id}/pages/{page_number}",
    name="deleteDocumentBuildPage",
    dependencies=[Depends(verify_api_key)],
)
async def delete_document_build_page_endpoint(build_id: str, page_number: int) -> Response:
    """Delete a specific page from a document build."""
    try:
        deleted = delete_document_build_page(build_id, page_number)

        if not deleted:
            raise HTTPException(
                status_code=404,
                detail=f"Page {page_number} not found in build {build_id}",
            )

        return Response(status_code=204)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting page {page_number} from build {build_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete page") from e


@router.delete(
    "/v1/builds/{build_id}",
    name="deleteDocumentBuild",
    dependencies=[Depends(verify_api_key)],
)
async def delete_document_build_endpoint(build_id: str) -> Response:
    """Delete an entire document build and all its pages."""
    try:
        deleted = delete_document_build(build_id)

        if not deleted:
            raise HTTPException(status_code=404, detail=f"Build {build_id} not found")

        return Response(status_code=204)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting build {build_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete build") from e

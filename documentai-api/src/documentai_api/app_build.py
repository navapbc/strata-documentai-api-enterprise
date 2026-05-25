"""Document build endpoints for multi-page upload + submission."""

import asyncio
import os
import uuid
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    Form,
    Header,
    HTTPException,
    Query,
    Request,
    Response,
    UploadFile,
    status,
)

from documentai_api.config.constants import (
    MAX_PAGES_PER_BUILD,
    ApiVisualizationTag,
    ConfigDefaults,
    DocumentBuildStatus,
    DocumentCategory,
    FileValidation,
    ProcessStatus,
    UploadMethod,
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
from documentai_api.models.document_record import DocumentRecord
from documentai_api.schemas.document_builds import DocumentBuilds
from documentai_api.utils.auth import UserContext, get_user_context_from_api_key
from documentai_api.utils.ddb import (
    classify_as_ai_consent_declined,
    insert_minimal_ddb_record,
)
from documentai_api.utils.document_build import (
    clear_submitted_at,
    create_document_build,
    delete_document_build,
    delete_document_build_page,
    get_build_metadata,
    get_document_build_pages,
    is_document_build_submitted,
    mark_document_build_submitted,
    upsert_document_build_page,
)
from documentai_api.utils.pdf import merge_pages_to_pdf
from documentai_api.utils.s3 import parse_s3_uri
from documentai_api.utils.tenant_access import validate_build_tenant_access
from documentai_api.utils.uploads import (
    ImageConversionError,
    upload_document_for_processing,
    validate_file_type,
)

logger = get_logger(__name__)

router = APIRouter(dependencies=[Depends(get_user_context_from_api_key)])

MAX_FILE_SIZE_BYTES = ConfigDefaults.BDA_MAX_DOCUMENT_FILE_SIZE_BYTES


async def add_page_to_build(
    file: UploadFile,
    build_id: str,
    page_number: int,
    content_type: str,
    category: DocumentCategory | None = None,
    trace_id: str | None = None,
    overwrite: bool = True,
) -> BuildPageBatchItem:
    """Upload one page's bytes to S3 and upsert its DDB record."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    logger.info(
        f"Adding page to build {build_id}; page {page_number}; "
        f"filename: {file.filename}; category: {category}; content-type: {content_type}"
    )

    file.file.seek(0)
    file_extension = FileValidation.get_extension(content_type)
    unique_file_name = f"{build_id}/page-{page_number}.{file_extension}"

    s3_location = os.getenv(EnvVars.DOCUMENTAI_PREPROCESSING_LOCATION, "")
    dest_path = f"{s3_location}/{unique_file_name}"

    await upload_document_for_processing(
        src_file=file.file,
        dest_path=dest_path,
        original_file_name=file.filename,
        content_type=content_type,
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
        overwrite=overwrite,
    )

    return BuildPageBatchItem(page_number=page_number, file_name=file.filename)


@router.post(
    "/v1/builds",
    name="postDocumentBuild",
    tags=[ApiVisualizationTag.BUILDS_LIFECYCLE],
)
async def create_build(
    response: Response,
    auth: Annotated[UserContext, Depends(get_user_context_from_api_key)],
    category: Annotated[
        DocumentCategory | None, Form(description="Type of document being uploaded")
    ] = None,
    trace_id: Annotated[str | None, Header(alias="X-Trace-ID")] = None,
    external_document_id: Annotated[
        str | None, Form(description="External document identifier")
    ] = None,
    external_system_id: Annotated[
        str | None, Form(description="External system identifier")
    ] = None,
    ai_consent_flag: Annotated[bool | None, Form(description="AI consent flag")] = None,
) -> BuildCreatedResponse:
    """Create a new document build for multi-page upload."""
    if not trace_id:
        trace_id = str(uuid.uuid4())

    build_id = str(uuid.uuid4())
    create_document_build(
        build_id,
        category,
        external_document_id=external_document_id,
        external_system_id=external_system_id,
        ai_consent_flag=ai_consent_flag,
        tenant_id=auth.tenant_id,
        api_key_name=auth.api_key_name,
    )

    response.headers["X-Trace-ID"] = trace_id
    return BuildCreatedResponse(
        build_id=build_id,
        message="Build created successfully",
    )


@router.post(
    "/v1/builds/{build_id}/pages",
    name="postDocumentBuildPage",
    dependencies=[Depends(validate_build_tenant_access)],
    tags=[ApiVisualizationTag.BUILDS_PAGES],
)
async def upload_document_build_page(
    response: Response,
    file: UploadFile,
    build_id: str,
    page_number: Annotated[int | None, Form(description="Page number (1-indexed)", ge=1)] = None,
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

        content_type = await validate_file_type(file)

        if file.size and file.size > MAX_FILE_SIZE_BYTES:
            raise HTTPException(
                status_code=400,
                detail=f"File size exceeds maximum of {MAX_FILE_SIZE_BYTES} bytes",
            )

        pages = await asyncio.to_thread(get_document_build_pages, build_id)

        if len(pages) >= MAX_PAGES_PER_BUILD:
            raise HTTPException(
                status_code=400,
                detail=f"Build exceeds maximum of {MAX_PAGES_PER_BUILD} pages",
            )

        if page_number is None:
            page_number = max((p.page_number for p in pages), default=0) + 1

        # Use conditional write to prevent race on page_number allocation.
        # If overwrite=False and page exists, upsert_document_build_page will raise.
        result = await add_page_to_build(
            file, build_id, page_number, content_type, category, trace_id, overwrite=overwrite
        )

        response.headers["X-Trace-ID"] = trace_id
        return BuildPageUploadResponse(
            build_id=build_id,
            page_number=result.page_number,
            file_name=result.file_name,
            message="Page uploaded successfully",
        )
    except HTTPException:
        raise
    except ImageConversionError as e:
        raise HTTPException(status_code=400, detail=f"Image conversion failed: {e}") from e
    except Exception as e:
        logger.error(f"Error uploading document build page {page_number} for build {build_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to upload page") from e


@router.post(
    "/v1/builds/{build_id}/pages/batch",
    name="postDocumentBuildPageBatch",
    dependencies=[Depends(validate_build_tenant_access)],
    tags=[ApiVisualizationTag.BUILDS_PAGES],
)
async def upload_document_build_pages_batch(
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

        # Cheap pre-check before reading/validating all files
        if len(files) > MAX_PAGES_PER_BUILD:
            raise HTTPException(
                status_code=400,
                detail=f"Batch exceeds maximum of {MAX_PAGES_PER_BUILD} pages",
            )

        # Validate all files up front - cache content types to avoid double I/O
        content_types: list[str] = []
        for file in files:
            ct = await validate_file_type(file)
            if file.size and file.size > MAX_FILE_SIZE_BYTES:
                raise HTTPException(
                    status_code=400,
                    detail=f"File '{file.filename}' exceeds maximum size of {MAX_FILE_SIZE_BYTES} bytes",
                )
            content_types.append(ct)

        existing_pages = await asyncio.to_thread(get_document_build_pages, build_id)
        next_page_number = max((p.page_number for p in existing_pages), default=0) + 1

        if len(existing_pages) + len(files) > MAX_PAGES_PER_BUILD:
            raise HTTPException(
                status_code=400,
                detail=f"Build would exceed maximum of {MAX_PAGES_PER_BUILD} pages",
            )

        # Upload pages concurrently with bounded concurrency.
        # overwrite=False prevents concurrent batch requests from clobbering each other.
        # TaskGroup cancels siblings on first failure (unlike asyncio.gather).
        semaphore = asyncio.Semaphore(5)

        async def _upload_one(idx: int, file: UploadFile, ct: str) -> BuildPageBatchItem:
            async with semaphore:
                return await add_page_to_build(
                    file,
                    build_id,
                    next_page_number + idx,
                    ct,
                    category,
                    trace_id,
                    overwrite=False,
                )

        try:
            async with asyncio.TaskGroup() as tg:
                tasks = [
                    tg.create_task(_upload_one(i, f, ct))
                    for i, (f, ct) in enumerate(zip(files, content_types, strict=True))
                ]
            results = [t.result() for t in tasks]
        except* HTTPException as eg:
            raise eg.exceptions[0] from None
        except* ImageConversionError as eg:
            raise HTTPException(
                status_code=400, detail=f"Image conversion failed: {eg.exceptions[0]}"
            ) from None

        response.headers["X-Trace-ID"] = trace_id
        page_word = "page" if len(results) == 1 else "pages"
        return BuildPagesBatchResponse(
            build_id=build_id,
            pages_added=len(results),
            pages=list(results),
            message=f"{len(results)} {page_word} uploaded successfully",
        )
    except HTTPException:
        raise
    except ImageConversionError as e:
        raise HTTPException(status_code=400, detail=f"Image conversion failed: {e}") from e
    except Exception as e:
        logger.error(f"Error uploading batch pages for build {build_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to upload pages") from e


class _SubmitResult:
    """Result of _submit_build."""

    __slots__ = ("job_id", "job_status", "message", "page_count")

    def __init__(self, job_id: str, job_status: str, message: str, page_count: int) -> None:
        self.job_id = job_id
        self.job_status = job_status
        self.message = message
        self.page_count = page_count


async def _submit_build(response: Response, build_id: str, trace_id: str | None) -> _SubmitResult:
    """Shared submit logic. Validates, merges, uploads. Returns _SubmitResult."""
    if not trace_id:
        trace_id = str(uuid.uuid4())
    response.headers["X-Trace-ID"] = trace_id

    # Check AI consent before any heavy work
    build_metadata = await asyncio.to_thread(get_build_metadata, build_id)
    if build_metadata and build_metadata.get(DocumentBuilds.AI_CONSENT_FLAG) is False:
        job_id = str(uuid.uuid4())
        ddb_key = f"document-build-{build_id}-{job_id}.pdf"
        category_str = build_metadata.get(DocumentBuilds.CATEGORY)
        category = DocumentCategory(category_str) if category_str else None

        record = DocumentRecord(
            ddb_key=ddb_key,
            original_file_name=f"build-{build_id}.pdf",
            job_id=job_id,
            category=category,
            trace_id=trace_id,
            content_type="application/pdf",
            external_document_id=build_metadata.get(DocumentBuilds.EXTERNAL_DOCUMENT_ID),
            external_system_id=build_metadata.get(DocumentBuilds.EXTERNAL_SYSTEM_ID),
            ai_consent_flag=False,
            upload_method=UploadMethod.BUILD,
            tenant_id=build_metadata[DocumentBuilds.TENANT_ID],
            api_key_name=build_metadata[DocumentBuilds.API_KEY_NAME],
        )
        await asyncio.to_thread(insert_minimal_ddb_record, record)
        await asyncio.to_thread(classify_as_ai_consent_declined, object_key=ddb_key)

        pages = await asyncio.to_thread(get_document_build_pages, build_id)
        return _SubmitResult(
            job_id=job_id,
            job_status=ProcessStatus.AI_CONSENT_DECLINED.value,
            message="Document not processed - AI consent not provided",
            page_count=len(pages),
        )

    pages = await asyncio.to_thread(get_document_build_pages, build_id)

    if not pages:
        raise HTTPException(status_code=400, detail=f"Build {build_id} has no pages to submit")

    input_location = get_aws_config().documentai_input_location
    if not input_location:
        raise HTTPException(
            status_code=500, detail="DOCUMENTAI_INPUT_LOCATION environment variable not set"
        )

    # Validate category consistency - reject mixed categories
    categories = {p.category for p in pages}
    non_none_categories = {c for c in categories if c is not None}
    if len(non_none_categories) > 1:
        raise HTTPException(
            status_code=400,
            detail=f"Mixed categories in build: {', '.join(non_none_categories)}. All pages must use the same category.",
        )

    # Atomic lock: marks build as submitted via conditional write.
    # Raises 400 if already submitted (prevents duplicate processing).
    # All cheap validation must happen above this line.
    await asyncio.to_thread(mark_document_build_submitted, build_id)

    try:
        merged_pdf = await asyncio.to_thread(merge_pages_to_pdf, pages)

        job_id = str(uuid.uuid4())
        unique_file_name = f"document-build-{build_id}-{uuid.uuid4()}.pdf"
        category_str = next((p.category for p in pages if p.category), None)
        category = DocumentCategory(category_str) if category_str else None

        await upload_document_for_processing(
            src_file=merged_pdf,
            dest_path=f"{input_location}/{unique_file_name}",
            original_file_name=unique_file_name,
            content_type="application/pdf",
            user_provided_document_category=category,
            job_id=job_id,
            trace_id=trace_id,
            build_id=build_id,
        )

        return _SubmitResult(
            job_id=job_id,
            job_status=ProcessStatus.NOT_STARTED.value,
            message="Document build submitted successfully",
            page_count=len(pages),
        )
    except HTTPException:
        raise
    except Exception as e:
        # Upload failed after lock acquired - clear submittedAt so user can retry
        try:
            await asyncio.to_thread(clear_submitted_at, build_id)
        except Exception as rollback_err:
            logger.warning(f"Failed to rollback submittedAt for build {build_id}: {rollback_err}")
        logger.error(f"Error submitting document build {build_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to submit document build") from e


@router.post(
    "/v1/builds/{build_id}/submit",
    name="postDocumentBuildSubmit",
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(validate_build_tenant_access)],
    tags=[ApiVisualizationTag.BUILDS_LIFECYCLE],
)
async def submit_document_build(
    response: Response,
    build_id: str,
    trace_id: Annotated[str | None, Header(alias="X-Trace-ID")] = None,
) -> BuildSubmitAsyncResponse:
    """Submit a multi-page build for processing (fire-and-forget)."""
    result = await _submit_build(response, build_id, trace_id)
    return BuildSubmitAsyncResponse(
        job_id=result.job_id,
        build_id=build_id,
        job_status=result.job_status,
        message=result.message,
        page_count=result.page_count,
    )


@router.post(
    "/v1/builds/{build_id}/submit/wait",
    name="postDocumentBuildSubmitWait",
    dependencies=[Depends(validate_build_tenant_access)],
    tags=[ApiVisualizationTag.BUILDS_LIFECYCLE],
)
async def submit_document_build_wait(
    request: Request,
    response: Response,
    build_id: str,
    trace_id: Annotated[str | None, Header(alias="X-Trace-ID")] = None,
    include_extracted_data: bool = False,
    timeout: Annotated[int, Query(ge=1)] = ConfigDefaults.MAX_WAIT_SECONDS
    - ConfigDefaults.ALB_TIMEOUT_BUFFER_SECONDS,
) -> JobStatusResponse:
    """Submit a multi-page build and poll until processing completes or timeout."""
    from documentai_api.utils.jobs import poll_for_completion

    result = await _submit_build(response, build_id, trace_id)
    if ProcessStatus.is_classified(result.job_status):
        return JobStatusResponse(
            job_id=result.job_id,
            job_status=result.job_status,
            message=result.message,
        )
    safe_timeout = min(
        timeout, ConfigDefaults.MAX_WAIT_SECONDS - ConfigDefaults.ALB_TIMEOUT_BUFFER_SECONDS
    )
    return await poll_for_completion(
        result.job_id, safe_timeout, request=request, include_extracted_data=include_extracted_data
    )


@router.get(
    "/v1/builds/{build_id}",
    name="getDocumentBuildStatus",
    dependencies=[Depends(validate_build_tenant_access)],
    tags=[ApiVisualizationTag.BUILDS_STATUS],
)
async def get_document_build(
    build_id: str,
) -> BuildDetailsResponse:
    """Get document build details including all uploaded pages."""
    try:
        pages = await asyncio.to_thread(get_document_build_pages, build_id)
        build_status = (
            DocumentBuildStatus.SUBMITTED
            if await asyncio.to_thread(is_document_build_submitted, build_id)
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
    dependencies=[Depends(validate_build_tenant_access)],
    tags=[ApiVisualizationTag.BUILDS_PAGES],
)
async def delete_document_build_page_endpoint(build_id: str, page_number: int) -> Response:
    """Delete a specific page from a document build."""
    try:
        deleted = await asyncio.to_thread(delete_document_build_page, build_id, page_number)

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
    dependencies=[Depends(validate_build_tenant_access)],
    tags=[ApiVisualizationTag.BUILDS_LIFECYCLE],
)
async def delete_document_build_endpoint(
    build_id: str,
) -> Response:
    """Delete an entire document build and all its pages."""
    try:
        deleted = await asyncio.to_thread(delete_document_build, build_id)

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

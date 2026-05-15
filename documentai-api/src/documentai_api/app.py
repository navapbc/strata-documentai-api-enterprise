import asyncio
import json
import os
import uuid
from dataclasses import dataclass
from typing import Annotated, Any, BinaryIO

import filetype  # type: ignore[import-untyped]
from fastapi import (
    Depends,
    FastAPI,
    Form,
    Header,
    HTTPException,
    Request,
    Response,
    UploadFile,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRoute
from mangum import Mangum

from documentai_api.config.constants import (
    API_VERSION,
    SUPPORTED_CONTENT_TYPES,
    APIConfig,
    DictionaryBlueprintField,
    DictionaryBlueprintSchema,
    DictionaryFormatType,
    DocumentCategory,
    FileValidation,
    ProcessStatus,
    S3MetadataKeys,
)
from documentai_api.config.env import get_app_env_config, get_aws_config
from documentai_api.logging import get_logger
from documentai_api.models.api_responses import (
    ConfigResponse,
    DictionaryDocumentCategoriesResponse,
    DictionaryFieldsResponse,
    DictionaryResponseCodesResponse,
    DictionarySchemaDetailResponse,
    DictionarySchemaListResponse,
    DictionarySearchResponse,
    ExtractionRuleDeleteResponse,
    ExtractionRuleItem,
    ExtractionRulesListResponse,
    HealthResponse,
    JobStatusResponse,
    UploadAsyncResponse,
)
from documentai_api.schemas.document_metadata import DocumentMetadata
from documentai_api.services import s3 as s3_service
from documentai_api.utils.auth import verify_api_key
from documentai_api.utils.ddb import (
    classify_as_failed,
    get_ddb_by_job_id,
    insert_minimal_ddb_record,
)
from documentai_api.utils.models import ClassificationData
from documentai_api.utils.response_builder import build_csv_response
from documentai_api.utils.s3 import parse_s3_uri
from documentai_api.utils.schemas import get_all_fields, get_all_schemas, get_document_schema

logger = get_logger(__name__)

app = FastAPI(
    title=APIConfig.TITLE,
    description=APIConfig.DESCRIPTION,
    version=APIConfig.VERSION,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Lambda entrypoint for the API container. Configure the API Lambda function with
# ImageConfig.Command = ["documentai_api.app.handler"].
handler = Mangum(app, lifespan="off")

# Configure logging when running in Lambda. main() bypassed, so LoggingContext is
# never entered the normal way; without it, INFO logs are silently dropped.
# AWS_LAMBDA_FUNCTION_NAME is set automatically by the Lambda runtime.
if os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
    from documentai_api.logging.config import LoggingContext

    LoggingContext("documentai_api")

CONFIG_EXCLUDED_ROUTES = {"/", "/health", "/config", "/openapi.json", "/docs", "/redoc"}


def discover_endpoints(app: FastAPI) -> dict[str, str]:
    """Build a sorted map of operation name → path for all non-excluded routes."""
    endpoints = {}
    for route in app.routes:
        if isinstance(route, APIRoute) and route.name and route.path not in CONFIG_EXCLUDED_ROUTES:
            endpoints[route.name] = route.path
    return dict(sorted(endpoints.items()))


# public endpoints (no auth required)
@app.get("/")
def root() -> dict[str, Any]:
    return {"message": APIConfig.TITLE, "status": "healthy"}


@app.get("/health")
async def health() -> HealthResponse:
    return HealthResponse(message="healthy")


@app.get("/config", dependencies=[Depends(verify_api_key)])
def get_config(request: Request) -> ConfigResponse:
    endpoints = discover_endpoints(app)
    endpoints["postUploadSyncronous"] = f"{endpoints['postUpload']}?wait=true"

    app_config = get_app_env_config()
    return ConfigResponse(
        api_url=f"{request.url.scheme}://{request.url.netloc}",
        version=API_VERSION,
        image_tag=app_config.image_tag,
        environment=app_config.environment,
        endpoints=endpoints,
        supported_file_types=list(SUPPORTED_CONTENT_TYPES),
    )


@dataclass
class JobStatus:
    """Job status data from DDB."""

    ddb_record: dict[str, Any] | None
    object_key: str | None
    process_status: str | None
    v1_response_json: str | None


def _get_job_status(job_id: str) -> JobStatus:
    """Get job status from DDB.

    Returns:
        JobStatus: Job status data with all fields None if job not found

    Raises:
        Exception: If DDB query fails (network, permissions, etc.)
    """
    ddb_record = get_ddb_by_job_id(job_id)

    if not ddb_record:
        return JobStatus(None, None, None, None)

    object_key = ddb_record.get(DocumentMetadata.FILE_NAME)
    process_status = ddb_record.get(DocumentMetadata.PROCESS_STATUS)
    v1_response = ddb_record.get(DocumentMetadata.V1_API_RESPONSE_JSON)

    return JobStatus(ddb_record, object_key, process_status, v1_response)


async def upload_document_for_processing(
    src_file: BinaryIO,
    dest_path: str,
    original_file_name: str,
    content_type: str,
    user_provided_document_category: DocumentCategory | None = None,
    job_id: str | None = None,
    trace_id: str | None = None,
) -> None:
    logger.debug(
        "S3 upload started",
        extra={
            "dest_path": dest_path,
            "user_provided_document_category": user_provided_document_category,
            "category_type": type(user_provided_document_category).__name__,
        },
    )

    bucket_name, object_key = parse_s3_uri(dest_path)

    try:
        metadata = {}
        if user_provided_document_category:
            # add type check for safety
            if not isinstance(user_provided_document_category, DocumentCategory):
                raise ValueError(
                    f"Expected DocumentCategory, got {type(user_provided_document_category)}"
                )

            metadata[S3MetadataKeys.USER_PROVIDED_DOCUMENT_CATEGORY] = (
                user_provided_document_category.value
            )

        metadata[S3MetadataKeys.ORIGINAL_FILE_NAME] = original_file_name

        if job_id:
            metadata[S3MetadataKeys.JOB_ID] = job_id

        if trace_id:
            metadata[S3MetadataKeys.TRACE_ID] = trace_id

        logger.debug(
            "S3: Starting actual upload",
            extra={
                "metadata": metadata,
                "dest_path": dest_path,
            },
        )

        s3_service.upload_file(bucket_name, object_key, src_file, content_type, metadata)
        logger.info("=== S3 UPLOAD SUCCESS ===")

    except Exception as e:
        logger.error(f"Error uploading file to S3: {e}")
        logger.info(f"=== S3 UPLOAD FAILED: {e} ===")
        raise HTTPException(
            status_code=500,
            detail="Document upload failed",
        ) from e


async def get_v1_document_processing_results(job_id: str, timeout: int) -> JobStatusResponse:
    """Poll for document processing completion with timeout."""
    elapsed_time = 0
    object_key = None
    polling_interval = 5

    while elapsed_time < timeout:
        try:
            job_status = _get_job_status(job_id)

            if job_status.object_key:
                object_key = job_status.object_key

            # processing complete, return results
            if (
                job_status.process_status
                and ProcessStatus.is_completed(job_status.process_status)
                and job_status.v1_response_json
            ):
                return JobStatusResponse(**json.loads(job_status.v1_response_json))

            # still processing, wait and poll again
            await asyncio.sleep(polling_interval)
            elapsed_time += polling_interval

        except Exception as e:
            msg = f"Error polling DynamoDB for job {job_id}: {e}"
            logger.error(msg)

            await asyncio.sleep(polling_interval)
            elapsed_time += polling_interval

    # timeout - update ddb with failure if we have object_key
    if object_key:
        result = classify_as_failed(
            object_key=object_key,
            error_message="Processing timeout",
            data=ClassificationData(
                additional_info=f"Processing did not complete within {timeout} seconds"
            ),
        )

        return JobStatusResponse(**result)
    else:
        # fallback if we never got a record
        return JobStatusResponse(
            job_id=job_id,
            job_status="failed",
            message=f"Processing timeout after {timeout} seconds",
        )


# protected endpoints (require authorization)
@app.post("/v1/documents", dependencies=[Depends(verify_api_key)], name="postUpload")
async def create_document(
    request: Request,
    response: Response,
    file: UploadFile,
    category: Annotated[
        DocumentCategory | None, Form(description="Type of document being uploaded")
    ] = None,
    trace_id: Annotated[str | None, Header(alias="X-Trace-ID")] = None,
    wait: bool = False,  # async by default
    timeout: int = 180,  # accounts for ECS cold starts and BDA processing time
) -> UploadAsyncResponse | JobStatusResponse:
    """Upload a document for processing.

    Args:
        wait: If true, waits for processing to complete before returning results.
              If false (default), returns immediately with job_id for async polling.
        timeout: Maximum seconds to wait when wait=true (default: 120)
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    if not trace_id:
        trace_id = str(uuid.uuid4())

    file_content = await file.read()
    actual_content_type = filetype.guess_mime(file_content) or "application/octet-stream"

    logger.info(
        "Upload received",
        extra={
            "filename": file.filename,
            "declared_content_type": file.content_type,
            "detected_content_type": actual_content_type,
            "size_bytes": len(file_content),
            "first_bytes_hex": file_content[:16].hex() if file_content else "",
        },
    )

    if not FileValidation.is_supported(actual_content_type):
        raise HTTPException(
            status_code=400,
            detail=(
                f"Invalid file type detected '{actual_content_type}'. File must be "
                f"{', '.join(FileValidation.SUPPORTED_CONTENT_TYPES)}"
            ),
        )

    logger.info(
        f"Processing {file.filename}; category: {category}; content-type: {actual_content_type}"
    )

    file.file.seek(0)
    file_extension = file.filename.split(".")[-1]
    file_name = file.filename.split(".")[0]
    unique_file_name = f"{file_name}-{uuid.uuid4()}.{file_extension}"
    original_file_name = file.filename
    job_id = str(uuid.uuid4())
    ddb_key = unique_file_name

    # DOCUMENTAI_INPUT_LOCATION includes full path (e.g. s3://bucket/input)
    input_location = get_aws_config().documentai_input_location
    dest_path = f"{input_location}/{unique_file_name}"

    insert_minimal_ddb_record(
        ddb_key=ddb_key,
        original_file_name=original_file_name,
        job_id=job_id,
        user_provided_document_category=category,
        trace_id=trace_id,
        content_type=actual_content_type,
    )

    try:
        await upload_document_for_processing(
            src_file=file.file,
            dest_path=dest_path,
            original_file_name=file.filename,
            content_type=actual_content_type,
            user_provided_document_category=category,
            job_id=job_id,
            trace_id=trace_id,
        )
    except HTTPException as e:
        classify_as_failed(
            object_key=ddb_key,
            error_message=e.detail,
            data=ClassificationData(additional_info=e.detail),
        )
        raise

    response.headers["X-Trace-ID"] = trace_id
    if not wait:
        return UploadAsyncResponse(
            job_id=job_id,
            job_status=ProcessStatus.NOT_STARTED.value,
            message="Document uploaded successfully",
        )
    else:
        return await get_v1_document_processing_results(job_id, timeout)


@app.get("/v1/documents/{job_id}", dependencies=[Depends(verify_api_key)])
async def get_document_results(
    job_id: str, include_extracted_data: bool = False
) -> JobStatusResponse:
    """Get processing results by job ID."""
    try:
        job_status = _get_job_status(job_id)

        if not job_status.ddb_record:
            raise HTTPException(status_code=404, detail=f"Job ID {job_id} not found")

        if not job_status.v1_response_json:
            return JobStatusResponse(
                job_id=job_id,
                job_status=job_status.process_status or "processing",
                message="Processing in progress",
            )

        # processing complete
        if include_extracted_data:
            # rebuild response with extracted data
            from documentai_api.utils.response_builder import build_v1_api_response

            if not job_status.object_key or not job_status.process_status:
                raise HTTPException(status_code=500, detail=f"Incomplete record for job {job_id}")

            return JobStatusResponse(
                **build_v1_api_response(
                    object_key=job_status.object_key,
                    job_status=job_status.process_status,
                    include_extracted_data=True,
                )
            )
        else:
            # return cached response without extracted data
            return JobStatusResponse(**json.loads(job_status.v1_response_json))

    except HTTPException:
        raise
    except Exception as e:
        msg = f"Error retrieving results for job {job_id}: {e}"
        logger.error(msg)
        raise HTTPException(status_code=500, detail="Failed to retrieve results") from e


# ==============================================================================
# dictionary endpoints
# ==============================================================================


@app.get("/v1/dictionary/schemas", dependencies=[Depends(verify_api_key)], name="getSchemaList")
async def list_schemas() -> DictionarySchemaListResponse:
    """List all supported document types."""
    schemas = get_all_schemas()
    return DictionarySchemaListResponse(schemas=sorted(schemas.keys()))


@app.get(
    "/v1/dictionary/schemas/{document_type}",
    dependencies=[Depends(verify_api_key)],
    name="getSchemaDetail",
    response_model=DictionarySchemaDetailResponse,
)
async def get_schema_detail(
    document_type: str, format: DictionaryFormatType = DictionaryFormatType.JSON
) -> Any:
    """Get field schema for a specific document type."""
    schema = get_document_schema(document_type)

    if not schema:
        raise HTTPException(status_code=404, detail=f"Schema not found: {document_type}")

    data = schema[DictionaryBlueprintSchema.FIELDS]

    if format == DictionaryFormatType.CSV:
        return build_csv_response(data)

    return DictionarySchemaDetailResponse(document_type=document_type, fields=data)


@app.get(
    "/v1/dictionary/fields",
    dependencies=[Depends(verify_api_key)],
    name="getAllFields",
    response_model=DictionaryFieldsResponse,
)
async def get_all_schema_fields(
    format: DictionaryFormatType = DictionaryFormatType.JSON,
) -> Any:
    """Get all fields across all document types."""
    data = get_all_fields()

    if format == DictionaryFormatType.CSV:
        return build_csv_response(data)

    return DictionaryFieldsResponse(fields=data)


@app.get(
    "/v1/dictionary/search",
    dependencies=[Depends(verify_api_key)],
    name="searchSchemas",
    response_model=DictionarySearchResponse,
)
async def search_schema_fields(
    q: str | None = None,
    field: DictionaryBlueprintField | None = None,
    format: DictionaryFormatType = DictionaryFormatType.JSON,
) -> Any:
    """Search fields across all blueprints."""
    data = get_all_fields()

    if q:
        query = q.lower()
        if field:
            data = [f for f in data if query in str(f.get(field, "")).lower()]
        else:
            data = [f for f in data if any(query in str(v).lower() for v in f.values())]

    if format == DictionaryFormatType.CSV:
        return build_csv_response(data)

    return DictionarySearchResponse(fields=data)


@app.get(
    "/v1/dictionary/response-codes",
    dependencies=[Depends(verify_api_key)],
    name="getResponseCodes",
    response_model=DictionaryResponseCodesResponse,
)
async def get_response_codes(format: DictionaryFormatType = DictionaryFormatType.JSON) -> Any:
    """Get list of response codes and their meanings."""
    from documentai_api.utils.response_codes import ResponseCodes

    data = ResponseCodes.get_all()

    if format == DictionaryFormatType.CSV:
        return build_csv_response(data)

    return DictionaryResponseCodesResponse(response_codes=data)


@app.get(
    "/v1/dictionary/document-categories",
    dependencies=[Depends(verify_api_key)],
    name="getDocumentCategories",
    response_model=DictionaryDocumentCategoriesResponse,
)
async def get_document_categories(format: DictionaryFormatType = DictionaryFormatType.JSON) -> Any:
    """Get list of supported document categories."""
    from documentai_api.config.constants import DOCUMENT_CATEGORIES

    data = [{"category": c} for c in DOCUMENT_CATEGORIES]

    if format == DictionaryFormatType.CSV:
        return build_csv_response(data)

    return DictionaryDocumentCategoriesResponse(document_categories=DOCUMENT_CATEGORIES)


# ==============================================================================
# rule configuration endpoints
# ==============================================================================
@app.get(
    "/v1/config/extraction-rules",
    dependencies=[Depends(verify_api_key)],
    name="getExtractionRules",
    response_model=ExtractionRulesListResponse,
)
async def get_extraction_rules(
    tenant_id: str,
    document_type: str | None = None,
) -> Any:
    """Get extraction rules for a tenant."""
    from documentai_api.utils.extraction_rules import get_rules

    rules = get_rules(tenant_id, document_type)

    if not rules:
        raise HTTPException(status_code=404, detail="No rules found")
    return ExtractionRulesListResponse(rules=[ExtractionRuleItem(**r) for r in rules])


@app.put(
    "/v1/config/extraction-rules",
    dependencies=[Depends(verify_api_key)],
    name="putExtractionRule",
    response_model=ExtractionRuleItem,
)
async def put_extraction_rule(
    tenant_id: Annotated[str, Form()],
    document_type: Annotated[str, Form()],
    required_fields: Annotated[str, Form()],  # JSON string list of required field names
    optional_fields: Annotated[str, Form()],  # JSON string list of optional field names
) -> Any:
    """Create or update an extraction rule."""
    from documentai_api.utils.extraction_rules import upsert_rule

    try:
        parsed_required_fields = json.loads(required_fields)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=400, detail="required_fields must be valid JSON array"
        ) from None

    try:
        parsed_optional_fields = json.loads(optional_fields)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=400, detail="optional_fields must be valid JSON array"
        ) from None

    rule = upsert_rule(tenant_id, document_type, parsed_required_fields, parsed_optional_fields)
    return ExtractionRuleItem(**rule)


@app.delete(
    "/v1/config/extraction-rules",
    dependencies=[Depends(verify_api_key)],
    name="deleteExtractionRule",
    response_model=ExtractionRuleDeleteResponse,
)
async def delete_extraction_rule(
    tenant_id: str,
    document_type: str,
) -> Any:
    """Delete an extraction rule."""
    from documentai_api.utils.extraction_rules import delete_rule

    delete_rule(tenant_id, document_type)
    return ExtractionRuleDeleteResponse(message="Rule deleted")

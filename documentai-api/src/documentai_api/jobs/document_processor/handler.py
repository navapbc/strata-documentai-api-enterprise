"""Lambda handler for document processing."""

from typing import Any

from documentai_api.jobs.document_processor.main import main
from documentai_api.logging import get_logger
from documentai_api.utils.lambda_error_handler import handle_lambda_errors
from documentai_api.utils.s3 import extract_s3_info_from_event

logger = get_logger(__name__)


@handle_lambda_errors
def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    key, bucket, *_ = extract_s3_info_from_event(event)
    logger.info(f"Processing S3 upload: s3://{bucket}/{key}")
    main(object_key=key, bucket_name=bucket)
    return {"statusCode": 200}

"""Lambda handler for document processing."""

import os
from typing import Any

from documentai_api.jobs.document_processor.main import main
from documentai_api.logging import get_logger, init
from documentai_api.utils.ddb import classify_as_failed
from documentai_api.utils.dto import ClassificationData
from documentai_api.utils.lambda_error_handler import handle_lambda_errors
from documentai_api.utils.s3 import extract_s3_info_from_event

logger = get_logger(__name__)


@handle_lambda_errors
def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    key, bucket, *_ = extract_s3_info_from_event(event)

    try:
        with init(__package__):
            logger.info(f"Processing S3 upload: s3://{bucket}/{key}")
            main(object_key=key, bucket_name=bucket)
    except Exception as e:
        logger.error(f"Document processing failed for {key}: {e}")
        ddb_key = os.path.basename(key)
        try:
            classify_as_failed(
                object_key=ddb_key,
                error_message=str(e),
                data=ClassificationData(additional_info="Unhandled error in document processor"),
            )
        except Exception as ddb_err:
            logger.error(f"Failed to mark {ddb_key} as failed in DDB: {ddb_err}")
        raise
    return {"statusCode": 200}

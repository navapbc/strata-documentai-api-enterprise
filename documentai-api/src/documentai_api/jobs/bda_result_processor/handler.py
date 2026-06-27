"""Lambda handler for BDA output processing."""

from datetime import UTC, datetime
from typing import Any

from documentai_api.jobs.bda_result_processor.main import main
from documentai_api.logging import get_logger, init
from documentai_api.utils.ddb import get_ddb_key_from_bda_output
from documentai_api.utils.document_lifecycle import classify_as_failed
from documentai_api.utils.dto import ClassificationData
from documentai_api.utils.lambda_error_handler import handle_lambda_errors
from documentai_api.utils.s3 import extract_s3_info_from_event

logger = get_logger(__name__)


@handle_lambda_errors
def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    result_processor_started_at = datetime.now(UTC).isoformat()
    key, bucket, *_ = extract_s3_info_from_event(event)

    try:
        with init(__package__):
            logger.info(f"Processing BDA output: s3://{bucket}/{key}")
            main(
                bucket_name=bucket,
                object_key=key,
                result_processor_started_at=result_processor_started_at,
            )
    except Exception as e:
        logger.error(f"BDA result processing failed for {key}: {e}")
        try:
            ddb_key = get_ddb_key_from_bda_output(bucket, key)
            if not ddb_key:
                logger.error(f"Unable to resolve DDB key from BDA output: s3://{bucket}/{key}")
                raise
            classify_as_failed(
                object_key=ddb_key,
                error_message=str(e),
                data=ClassificationData(additional_info="Unhandled error in BDA result processor"),
                result_processor_started_at=result_processor_started_at,
            )
        except Exception as ddb_err:
            logger.error(f"Failed to mark document as failed in DDB: {ddb_err}")
        raise
    return {"statusCode": 200}

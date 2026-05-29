"""Lambda handler for metrics processor."""

import json
from typing import Any

from documentai_api.config.env import get_aws_config
from documentai_api.jobs.metrics_processor.main import write_to_s3
from documentai_api.logging import get_logger
from documentai_api.utils.lambda_error_handler import handle_lambda_errors

logger = get_logger(__name__)


@handle_lambda_errors
def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Lambda handler triggered by SQS event source.

    Processes metrics from SQS queue and writes to S3.
    """
    # TODO: Update to call main() if more complex processing is needed,
    # currently just writes raw messages to S3
    bucket_name = get_aws_config().ddb_export_bucket_name
    if not bucket_name:
        raise KeyError("DDB_EXPORT_BUCKET_NAME")
    records = event.get("Records", [])

    if records:
        queue_arn = records[0].get("eventSourceARN", "unknown")
        logger.info(f"Processing {len(records)} records from {queue_arn}")

    processed = 0
    for record in records:
        try:
            body = json.loads(record["body"])
            write_to_s3(bucket_name, body)
            processed += 1
        except Exception as e:
            logger.error(f"Failed to process record: {e}")

    logger.info(f"Processed {processed}/{len(records)} records")
    return {"statusCode": 200, "body": json.dumps({"processed": processed})}

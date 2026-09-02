"""Lambda handler for metrics processor."""

import json
from typing import Any

from opentelemetry import trace
from opentelemetry.propagate import extract

from documentai_api.config.env import get_aws_config
from documentai_api.jobs.metrics_processor.main import write_to_s3
from documentai_api.logging import get_logger
from documentai_api.telemetry import setup as setup_otel
from documentai_api.utils.lambda_error_handler import handle_lambda_errors

logger = get_logger(__name__)
tracer = trace.get_tracer(__name__)

setup_otel()


@handle_lambda_errors
def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Lambda handler triggered by SQS event source.

    Processes metrics from SQS queue and writes to S3.
    """
    # Calls write_to_s3 directly rather than invoking main(). main()'s receive/delete
    # loop conflicts with Lambda's SQS event-source mapping, which handles message
    # delivery and deletion
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
            # Extract traceparent from MessageAttributes to stitch this span
            # into the originating document trace.
            attrs = record.get("messageAttributes") or {}
            carrier = {k: v["stringValue"] for k, v in attrs.items() if "stringValue" in v}
            ctx = extract(carrier)

            with tracer.start_as_current_span("metrics.process", context=ctx):
                body = json.loads(record["body"])
                write_to_s3(bucket_name, body)
                processed += 1
        except Exception as e:
            logger.error(f"Failed to process record: {e}")

    logger.info(f"Processed {processed}/{len(records)} records")
    return {"statusCode": 200, "body": json.dumps({"processed": processed})}

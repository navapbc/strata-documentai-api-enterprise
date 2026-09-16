"""Lambda handler for LLM result processing."""

import json
from typing import Any

from opentelemetry import trace
from opentelemetry.propagate import extract

from documentai_api.dtos.processing import LlmExtractionMessage
from documentai_api.jobs.llm_result_processor.main import process_message
from documentai_api.logging import get_logger, init
from documentai_api.telemetry import setup as setup_otel
from documentai_api.utils.lambda_error_handler import handle_lambda_errors

logger = get_logger(__name__)
tracer = trace.get_tracer(__name__)

setup_otel()


@handle_lambda_errors
def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Lambda handler triggered by SQS event source."""
    records = event.get("Records", [])
    processed = 0

    with init(__package__):
        for record in records:
            attrs = record.get("messageAttributes") or {}
            carrier = {k: v["stringValue"] for k, v in attrs.items() if "stringValue" in v}
            ctx = extract(carrier)

            with tracer.start_as_current_span("llm_result_processor.handler", context=ctx) as span:
                try:
                    body = json.loads(record["body"])
                    msg = LlmExtractionMessage.from_dict(body)
                    span.set_attribute("document.key", msg.ddb_key)
                    span.set_attribute("document.type", msg.document_type)
                    process_message(body)
                    processed += 1
                except Exception as e:
                    logger.error(f"Failed to process record: {e}")
                    raise

        logger.info(f"Processed {processed}/{len(records)} records")

    return {"statusCode": 200, "body": json.dumps({"processed": processed})}

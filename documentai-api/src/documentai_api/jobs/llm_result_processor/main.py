"""Process LLM extraction requests from SQS queue."""

from typing import Any

from documentai_api.dtos.processing import LlmExtractionMessage
from documentai_api.logging import get_logger
from documentai_api.pipeline.llm import run_llm_pipeline

logger = get_logger(__name__)


def main(msg: LlmExtractionMessage) -> None:
    """Run the LLM extraction pipeline for a single SQS message."""
    run_llm_pipeline(msg)


def process_message(body: dict[str, Any]) -> None:
    """Unpack an SQS message body and run LLM extraction."""
    main(LlmExtractionMessage.from_dict(body))

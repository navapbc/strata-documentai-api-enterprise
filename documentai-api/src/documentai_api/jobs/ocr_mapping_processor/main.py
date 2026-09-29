"""Process OCR mapping extraction requests from SQS queue."""

from typing import Any

from documentai_api.dtos.processing import OcrMappingMessage
from documentai_api.logging import get_logger
from documentai_api.pipeline.ocr_mapping import run_ocr_mapping_pipeline

logger = get_logger(__name__)


def main(msg: OcrMappingMessage) -> None:
    """Run the OCR mapping extraction pipeline for a single SQS message."""
    run_ocr_mapping_pipeline(msg)


def process_message(body: dict[str, Any]) -> None:
    """Unpack an SQS message body and run OCR mapping extraction."""
    main(OcrMappingMessage.from_dict(body))

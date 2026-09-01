"""Lambda handler for the document reaper."""

from typing import Any

from documentai_api.jobs.document_reaper.main import main
from documentai_api.logging import get_logger, init
from documentai_api.utils.lambda_error_handler import handle_lambda_errors

logger = get_logger(__name__)


@handle_lambda_errors
def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Lambda handler triggered by EventBridge schedule.

    Finds DocumentRecord rows stuck in PROCESSING for more than one hour,
    checks BDA for actual status, and resolves them to a terminal state.
    """
    with init(__package__):
        result = main()
        logger.info(f"Reaper complete: {result}")

    return result

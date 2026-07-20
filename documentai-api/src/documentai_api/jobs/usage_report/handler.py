"""Lambda handler for monthly tenant usage report generation."""

from datetime import UTC, datetime, timedelta
from typing import Any

from documentai_api.jobs.usage_report.main import main
from documentai_api.logging import get_logger, init
from documentai_api.utils.lambda_error_handler import handle_lambda_errors

logger = get_logger(__name__)


@handle_lambda_errors
def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Lambda handler triggered by EventBridge schedule or manual invocation.

    Event fields:
    - month: Target month (YYYY-MM), "current", or "previous". Required.
    """
    yyyymm = event.get("month")
    if not yyyymm:
        raise ValueError("'month' (YYYY-MM, 'current', or 'previous') is required")

    if yyyymm == "current":
        yyyymm = datetime.now(UTC).strftime("%Y-%m")
    elif yyyymm == "previous":
        first_of_this_month = datetime.now(UTC).replace(day=1)
        last_month = first_of_this_month - timedelta(days=1)
        yyyymm = last_month.strftime("%Y-%m")

    with init(__package__):
        logger.info(f"Generating usage report for {yyyymm}")
        result = main(yyyymm)
        logger.info(f"Usage report complete: {result}")

    return result

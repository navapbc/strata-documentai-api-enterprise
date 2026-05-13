"""Lambda handler for daily metrics aggregator."""

from datetime import datetime, timedelta
from typing import Any

from documentai_api.config.constants import MetricsAggregatorTargetDate
from documentai_api.jobs.metrics_aggregator.main import main
from documentai_api.logging import get_logger
from documentai_api.utils.lambda_error_handler import handle_lambda_errors

logger = get_logger(__name__)


@handle_lambda_errors
def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Lambda handler triggered by EventBridge schedule.

    Aggregates metrics data for a given date

    Event can optionally include:
    - target_date: Date to aggregate (YYYY-MM-DD). Optional. Defaults to previous day.
    - overwrite: If True, re-aggregate even if stats exist.
    """
    mode = event.get("mode")
    target_date = event.get("target_date")

    if target_date:
        pass  # manual override, use as-is
    elif mode == MetricsAggregatorTargetDate.TODAY:
        target_date = datetime.now().strftime("%Y-%m-%d")
    elif mode == MetricsAggregatorTargetDate.YESTERDAY:
        target_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    else:
        raise ValueError(
            "Either 'mode' (current/prior_day) or 'target_date' (YYYY-MM-DD) is required"
        )

    overwrite = event.get("overwrite", False)
    logger.info(f"Aggregating metrics for {target_date} (overwrite={overwrite})")
    result = main(target_date, overwrite)
    logger.info(f"Aggregation complete: {result}")

    return result

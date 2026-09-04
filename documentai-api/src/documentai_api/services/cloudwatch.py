"""CloudWatch service methods."""

from __future__ import annotations

from typing import TYPE_CHECKING

from documentai_api.logging import get_logger
from documentai_api.services.aws_client_factory import AWSClientFactory

if TYPE_CHECKING:
    from mypy_boto3_cloudwatch.literals import StandardUnitType
    from mypy_boto3_cloudwatch.type_defs import MetricDatumTypeDef

logger = get_logger(__name__)


def put_metric_data(
    namespace: str,
    metric_name: str,
    value: float,
    unit: StandardUnitType = "Count",
    dimensions: dict[str, str] | None = None,
) -> None:
    """Publish a single metric data point to CloudWatch."""
    try:
        client = AWSClientFactory.get_cloudwatch_client()
        metric: MetricDatumTypeDef = {"MetricName": metric_name, "Value": value, "Unit": unit}
        if dimensions:
            metric["Dimensions"] = [{"Name": k, "Value": v} for k, v in dimensions.items()]
        client.put_metric_data(Namespace=namespace, MetricData=[metric])
    except Exception as e:
        logger.warning(f"Failed to emit CloudWatch metric {namespace}/{metric_name}: {e}")

from enum import StrEnum

# === Metric aggregates (S3 prefixes) ===
METRICS_RAW_DDB_DATA_S3_PREFIX = "raw/utc/date"
METRICS_AGG_DDB_DAILY_S3_PREFIX = "aggregated/utc/date"
METRICS_AGG_DDB_MONTHLY_S3_PREFIX = "aggregated/utc/month"
METRICS_USAGE_REPORT_S3_PREFIX = "usage-report/month"
METRICS_USAGE_REPORT_DAILY_S3_PREFIX = "usage-report/utc/date"

ATHENA_QUERY_TIMEOUT_SECONDS = 300


class MetricsGranularity(StrEnum):
    DAILY = "daily"
    MONTHLY = "monthly"


class MetricsAggregatorTargetDate:
    TODAY = "today"
    YESTERDAY = "yesterday"


class MetricsDisplayValues:
    NOT_SPECIFIED = "not specified"
    _LEGACY_UNSET = ("unknown", "not specified", "null", "")

    @staticmethod
    def is_legacy_unset(value: str) -> bool:
        return value.strip().lower() in MetricsDisplayValues._LEGACY_UNSET


class TimingMetrics:
    TOTAL_PROCESSING_TIME = "total_processing_time"
    BDA_PROCESSING_TIME = "bda_processing_time"
    BDA_WAIT_TIME = "bda_wait_time"


class AthenaQueryStatus:
    """AWS Athena query execution states.

    See: https://docs.aws.amazon.com/athena/latest/APIReference/API_QueryExecutionStatus.html
    Note: AWS uses British spelling 'CANCELLED' (double L). Canceled is preferred
    in American English, while cancelled is standard in British English.
    """

    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"

    @staticmethod
    def is_final(status: str) -> bool:
        return status in {
            AthenaQueryStatus.SUCCEEDED,
            AthenaQueryStatus.FAILED,
            AthenaQueryStatus.CANCELLED,
        }

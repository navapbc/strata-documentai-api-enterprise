"""Response models for metrics endpoints."""

from pydantic import Field

from documentai_api.models.base import BaseApiResponse


class TimingStats(BaseApiResponse):
    total_processing_time_avg: float = 0
    total_processing_time_sum: float = 0
    total_processing_time_count: int = 0
    bda_processing_time_avg: float = 0
    bda_processing_time_sum: float = 0
    bda_processing_time_count: int = 0
    bda_wait_time_avg: float = 0
    bda_wait_time_sum: float = 0
    bda_wait_time_count: int = 0


class UsageStats(BaseApiResponse):
    total_file_size_bytes: int = 0
    total_pages: int = 0
    total_bedrock_input_tokens: int = 0
    total_bedrock_output_tokens: int = 0


class MetricsSummary(BaseApiResponse):
    total_records: int = 0
    total_bda_invocations: int = 0
    by_status: dict[str, int] = Field(default_factory=dict)
    by_classification: dict[str, int] = Field(default_factory=dict)
    by_response_code: dict[str, int] = Field(default_factory=dict)
    timing_stats: TimingStats = TimingStats()
    usage_stats: UsageStats = UsageStats()


class PeriodStats(BaseApiResponse):
    date: str | None = None
    month: str | None = None
    total_records: int = 0
    total_bda_invocations: int = 0
    by_status: dict[str, int] = Field(default_factory=dict)
    by_classification: dict[str, int] = Field(default_factory=dict)
    by_response_code: dict[str, int] = Field(default_factory=dict)
    timing_stats: TimingStats = TimingStats()
    usage_stats: UsageStats = UsageStats()


class MetricsResponse(BaseApiResponse):
    start_date: str
    end_date: str
    granularity: str
    daily_stats: list[PeriodStats] | None = None
    monthly_stats: list[PeriodStats] | None = None
    summary: MetricsSummary

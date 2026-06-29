"""Response models for usage reporting."""

from pydantic import Field

from documentai_api.config.constants import MetricsGranularity
from documentai_api.models.base import BaseApiResponse


class TenantUsage(BaseApiResponse):
    tenant_id: str = ""
    total_records: int = 0
    total_bda_invocations: int = 0
    total_file_size_bytes: int = 0
    total_bda_pages: int = 0
    total_bedrock_input_tokens: int = 0
    total_bedrock_output_tokens: int = 0


class DailyUsage(BaseApiResponse):
    date: str = ""
    total_records: int = 0
    total_bda_invocations: int = 0
    total_pages: int = 0
    total_bda_pages: int = 0
    total_file_size_bytes: int = 0
    total_bedrock_input_tokens: int = 0
    total_bedrock_output_tokens: int = 0


class MonthlyUsageResponse(BaseApiResponse):
    month: str
    granularity: str = MetricsGranularity.MONTHLY
    tenants: list[TenantUsage] = Field(default_factory=list)


class DailyUsageResponse(BaseApiResponse):
    month: str
    granularity: str = MetricsGranularity.DAILY
    days: list[DailyUsage] = Field(default_factory=list)

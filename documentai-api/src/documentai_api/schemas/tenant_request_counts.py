"""Schema for the tenant_request_counts DynamoDB table."""

from documentai_api.utils.base_readonly_table import ReadOnlyTable


class TenantRequestCountRecord:
    """Field names for the tenant_request_counts DynamoDB table."""

    TENANT_ID = "tenantId"
    DATE = "date"
    COUNT = "count"
    TTL = "ttl"


class TenantRequestCountsTable(ReadOnlyTable):
    table_name_env = "tenant_request_counts_table_name"
    pk_field = TenantRequestCountRecord.TENANT_ID
    sk_field = TenantRequestCountRecord.DATE

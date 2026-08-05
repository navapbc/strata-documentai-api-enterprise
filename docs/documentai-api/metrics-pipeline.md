# Metrics pipeline

Every document processed by the platform generates a metrics event - processing time, document classification, response status, file size, page count, and Bedrock token usage. These events flow through an automated pipeline that stores and aggregates them for reporting.

## How it works

When a document finishes processing, a metrics event is emitted to an SQS queue. A Lambda processor reads from the queue and writes the raw event to S3. A separate aggregator Lambda runs on a daily schedule, reads the raw events for the previous day, and writes aggregated stats back to S3 - broken down by status, document type, response code, and timing.

Aggregated stats are stored at both daily and monthly granularity, scoped per tenant. The admin console reads from these aggregated files to display usage charts and summaries.

## What gets measured

Each processed document contributes to:

- Document counts by status (success, failure, etc.) and classification (document type)
- Processing time - total end-to-end, BDA invocation time, and BDA wait time
- File size and page count
- Bedrock token usage (input and output tokens)

## Querying metrics

The admin console exposes metrics for a configurable date range at daily or monthly granularity. Super-admins can view metrics across all tenants. Tenant-admins see only their own tenant's data.

For deeper analysis, the raw metrics data in S3 is queryable via Athena. A usage report command generates a per-tenant monthly summary covering pages processed, bytes, and Bedrock tokens - useful for billing and capacity planning.

## Running the aggregator manually

The aggregator Lambda runs on a daily schedule but can be triggered on demand:

```bash
make metrics-agg DATE=2025-01-15                  # Single date
make metrics-agg DATE=2025-01-01 END=2025-01-31   # Date range
make metrics-agg-last-n-days DAYS=7               # Last 7 days
make metrics-agg DATE=2025-01-15 OVERWRITE=1      # Force overwrite
```

Or directly via the CLI:

```bash
uv run --frozen metrics_aggregator cli 2025-01-15
uv run --frozen metrics_aggregator backfill 2025-01-01 2025-01-31
```

## Tenant scoping

Metrics are always scoped to the tenant that submitted the document. Aggregated stats are stored with a tenant partition, so queries for one tenant never include another tenant's data.

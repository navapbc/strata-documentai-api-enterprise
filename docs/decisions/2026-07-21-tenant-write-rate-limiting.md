# Use DynamoDB Atomic Counters for Tenant Write Quota Enforcement

- Status: accepted
- Deciders: Engineering
- Date: 2026-07-21

## Context and Problem Statement

Tenants need configurable daily and monthly write request quotas. How should per-tenant request counts be tracked and enforced in a way that is accurate, operationally simple, and consistent with the existing infrastructure?

## Decision Drivers

- Accuracy: increments must be atomic to avoid double-counting under concurrent requests
- Operational simplicity: minimize new infrastructure and operational surface area
- Cost: avoid over-engineering for a low-frequency counter use case
- Infrastructure consistency: prefer solutions that fit the existing serverless, non-VPC Lambda architecture

## Considered Options

- DynamoDB atomic counters (`UpdateItem` with `ADD`)
- ElastiCache (Redis) with periodic DynamoDB flush

## Decision Outcome

Chosen option: "DynamoDB atomic counters", because it meets all decision drivers without requiring new infrastructure. ElastiCache would require VPC placement for all Lambda functions - a significant lift with no other current driver.

### Positive Consequences

- No new AWS services or Terraform modules required
- DynamoDB `UpdateItem` with `ADD` is atomic - no distributed lock needed
- TTL on count items (5 years) retains history for trend analysis and capacity planning; DynamoDB handles cleanup automatically
- Monthly totals derived by summing daily items via a single `Query` with `begins_with` - at most ~31 items

### Negative Consequences

- Each write request incurs 1–2 additional DynamoDB `UpdateItem` calls (increment and optional rollback on quota exceeded), adding ~1–5ms to the upload path
- At very high write volumes (thousands of requests/second per tenant), DynamoDB hot partition pressure could become a concern
- The `ADD` increment is atomic, but enforcement (increment -> check -> rollback) is not transactional. Under a concurrent burst at the quota boundary, multiple requests may increment, all see over-limit, and all roll back - so a request that could have been the last allowed one gets 429'd. The monthly total query is also non-transactional and can briefly reflect inflated counts during a burst. This is acceptable for the low-frequency quota use case.

## Pros and Cons of the Options

### DynamoDB atomic counters

- Good, because no VPC or new infrastructure required
- Good, because atomic `ADD` prevents double-counting without a distributed lock
- Good, because TTL handles cleanup automatically (5-year retention for trend analysis)
- Bad, because adds latency to the upload path per request
- Bad, because not well-suited if write volume grows to thousands of requests/second per tenant

### ElastiCache (Redis)

- Good, because sub-millisecond in-memory increments reduce upload path latency
- Good, because Redis `INCR` is atomic and well-suited for high-frequency counters
- Bad, because requires VPC placement for all Lambda functions (subnets, security groups, NAT gateway)
- Bad, because adds a new service to monitor, patch, and pay for
- Bad, because periodic flush introduces a window where counts in Redis and DynamoDB are out of sync

## Links

- Supersedes consideration of ElastiCache for quota enforcement

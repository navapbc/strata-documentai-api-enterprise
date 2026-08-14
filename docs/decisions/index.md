# Architectural Decision Log

This log lists the architectural decisions for DocumentAI API.

<!-- adrlog -- Regenerate the content by using "adr-log -i -e template.md". You can install it via "npm install -g adr-log" -->

* [ADR-2026-07-21](2026-07-21-tenant-write-rate-limiting.md) - Use DynamoDB Atomic Counters for Tenant Write Quota Enforcement
* [ADR-2026-07-22](2026-07-22-odt-upload-rejection.md) - Reject ODT Uploads with a Friendly Error Instead of Converting
* [ADR-2026-07-23](2026-07-23-per-category-processing-sampling.md) - Per-Category Document Processing Sampling
* [ADR-2026-08-06](2026-08-06-audit-log-actor-dropdown-source.md) - Audit Log Actor Dropdown: Use Cognito as the Sole Source
* [ADR-2026-08-14](2026-08-14-document-identity-model.md) - Defer the Document/Job Identity Split; Start Collecting `systemDocumentId` Now

<!-- adrlogstop -->

For new ADRs, please use [template.md](template.md) as basis.
More information on MADR is available at <https://adr.github.io/madr/>.
General information about architectural decision records is available at <https://adr.github.io/>.
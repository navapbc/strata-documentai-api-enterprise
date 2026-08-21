# DocumentAI Business Rules

Last updated on Jul 7, 2026

DocumentAI is a document processing service that evaluates and extracts information from uploaded documents.

DocumentAI is **not** a policy engine and does **not** make final eligibility decisions. It applies configured document rules and returns explainable results that can support customer self-service and worker review.

DocumentAI is designed to be reused across many offices, programs, and states.

## DocumentAI capabilities

### DocumentAI can help assess whether:

  - A file can be processed
  - A document is readable and complete
  - A document appears to be the right type
  - Required information is present
  - The document supports the selected verification purpose
  - The result should be accepted, rejected, or routed for human review

DocumentAI supports customer self-service, worker review, reporting, and auditability.

### DocumentAI does not:

  - Define program policy
  - Approve, deny, close, sanction, or terminate benefits
  - Replace human judgment
  - Use AI output as the sole basis for adverse action
  - Hard-code state, agency, or program policy into the core service

DocumentAI supports document review. It does not replace the eligibility system or human review.

## DocumentAI rules

DocumentAI rules are structured checks that evaluate whether a document meets configured requirements.

Rules define:

  - What is checked
  - What counts as a successful result
  - What counts as a failed result
  - What requires human review
  - What reason code should be returned
  - Whether the rule is general or policy-specific

Examples of general DocumentAI rules include:

  - Is the file processable?
  - Is the document readable?
  - Is it the right document type?
  - Are required fields present?
  - Does the name match the customer or household member?
  - Does the document cover the required period?
  - Are there conflicts or low-confidence results?

### DocumentAI rules are configurable

DocumentAI is a standalone service intended for reuse across multiple offices, programs, and states.

Because different programs may have different policies, DocumentAI doesn’t hard-code every business rule into the core service. Instead, the core service provides reusable document intelligence capabilities, while customers manage their own policy-specific rules through their configurations.

Customers can configure rules by:

  - Program
  - Verification purpose
  - Document type
  - Required fields
  - Review thresholds
      - Confidence thresholds allow auto-acceptance, rejection, or flag for additional human review.
  - Reason codes
  - Customer-facing messages
      - Which outputs should be customer-facing versus worker-only.

### Managing rules configurations

Customers manage these configurations through a restricted interface for administrators and authorized personnel to handle:

  - Access
  - Authorization to use the service
  - Roles
  - Reference documents (also known as blueprints)
  - Individual program configurations

For example, state-specific rules may define how DocumentAI should evaluate documents for SNAP-related requirements, such as whether a document supports income, work hours, or a qualifying activity.

Programs can configure those rules in their own environment, while another program from the same state can configure different requirements using the same core DocumentAI service.

## Learn more

- [DocumentAI business rules](docs/documentai-api/business-rules.md) - capabilities, boundaries, configurable rules, and human-review outcomes
- [Extraction rules](docs/documentai-api/extraction-rules.md) - required, optional, and excluded fields by tenant and document type
- [Admin console](ui/admin/README.md) - manage tenants, users, API keys, document categories, and rules

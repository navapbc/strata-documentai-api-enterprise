# DocumentAI: Product Vision, Mission, Strategy, and Success Metrics

## Purpose of this document

This document defines DocumentAI's intended outcomes, product strategy, and approach to measuring success. It guides product development, prioritization, adoption, and evaluation across implementations.

It is intended to evolve as DocumentAI is adopted by additional organizations, new use cases emerge, and evidence informs product improvements. Not all capabilities or metrics described here are currently implemented or available in every deployment.

## Product Vision

People can access and complete government services without unnecessary delays or burden caused by document requirements, while agencies can review information accurately, efficiently, and transparently.

DocumentAI contributes to this vision by helping agencies and the people they serve identify document problems earlier, reduce repetitive work, and make better use of information already submitted. It is intended to support services that are adaptable to different programs, policies, and populations.

### What progress toward this vision looks like

- **Fewer avoidable barriers for people:** Clearer document requirements, earlier identification of issues, and fewer repeat submissions or unnecessary contacts.
- **Less repetitive work for staff:** Fewer requests for replacements, fewer manual checks of basic document problems, and more time for complex cases.
- **Timelier, more reliable service:** Documents become usable sooner, supporting faster downstream processing without sacrificing accuracy or fairness.
- **Adaptable public infrastructure:** Agencies can configure and operate the service for different documents, programs, and workflows without rebuilding the core product.

## Product Mission

Build and maintain an open-source, configurable document-processing service that helps people submit usable documents, enables staff to review them with less manual effort, and allows agencies to integrate document intelligence into existing services while preserving human oversight.

DocumentAI evaluates documents against configured requirements, identifies potential problems, and extracts structured information for downstream review and workflows. Its core capabilities should be reusable across agencies, jurisdictions, and programs.

Product boundary: DocumentAI is not a policy or eligibility decision engine. It does not independently approve, deny, close, sanction, or terminate benefits or services. Implementing organizations define applicable policy, document requirements, review workflows, and human decision-making responsibilities. DocumentAI results should not be the sole basis for adverse decisions.

## Product Strategy

The following principles guide product investment, prioritization, and implementation choices.

1. **Catch problems at the earliest useful point**

   Make document type, readability, completeness, and configured-requirement feedback available as early as practical so issues can be resolved before they create downstream rework. Client applications decide how and when to show that feedback.

2. **Augment human review rather than replace accountable decisions**

   Present extraction results, validation issues, and relevant supporting evidence in a way that enables staff to verify, correct, or override findings. Human reviewers and agencies remain responsible for consequential decisions.

3. **Design for both submitters and reviewers**

   Treat the document journey as an end-to-end workflow: submission, feedback, correction, extraction, review, and downstream action. Make the service useful to integrators and operators as well as frontline staff and the people they serve.

4. **Separate core capabilities from local requirements**

   Keep document types, blueprints, extraction rules, thresholds, and client workflows configurable rather than embedding jurisdiction-specific policies in the shared codebase.

5. **Build for adoption, ownership, and reuse**

   Provide documented APIs, deployment guidance, administration, testing patterns, and observability so implementing organizations can operate and extend the service. Encourage contributions that benefit multiple adopters.

6. **Use failures and corrections to improve quality**

   Monitor processing errors, no-match results, extraction performance, confidence signals, overrides, and user feedback. Use representative tests and reviewed examples to improve configurations and the product.

7. **Measure impact before expanding use**

   Pair product telemetry with workflow and outcome data supplied by adopters. Evaluate whether DocumentAI improves experiences and operations without introducing unacceptable errors, burdens, or unequal outcomes. Expand deliberately based on evidence and risk.

## What Success Looks Like

Product success has three connected layers:

- **Core product metrics:** Measures of DocumentAI's technical performance, reliability, and quality.
- **Workflow impact metrics:** Measures of how DocumentAI changes document submission, review, and processing. These usually require integration with client systems.
- **Public-service outcomes:** Measures of whether DocumentAI contributes to better service delivery. These depend on the program and require agency-owned data and interpretation.

### 1. People submit usable documents with less rework

**Desired change:** People can identify and resolve document issues sooner rather than learning later that more documentation is needed.

**Measures:**

- Percentage of documents flagged for potentially actionable quality, type, or configured-requirement issues.
- Percentage of flagged documents successfully corrected or replaced after feedback (requires client event tracking).
- Percentage of submitted documents usable at first downstream review (requires reviewer or agency data).
- Percentage of submissions requiring additional documentation.
- Number of repeat submissions per case or transaction.

**What good looks like:** Feedback is understandable and actionable; usable-at-first-review rates improve and repeat submissions decline, without increasing abandonment or confusion.

### 2. Staff spend less time on avoidable document work

**Desired change:** Reviewers receive more usable information and spend less time requesting replacements, correcting basic document issues, or repeating manual checks.

**Measures:**

- Number of follow-up requests and reviewer touches per case or transaction.
- Time spent on document review and correction.
- Rate and reasons for reviewer corrections or overrides of DocumentAI results.
- Qualitative feedback on usefulness, confidence, trust, and workflow burden.

**What good looks like:** Avoidable rework and repeated interactions decline while reviewers retain control and do not acquire new burdens that offset the gains.

### 3. Services complete document-dependent steps faster, without harming outcomes

**Desired change:** Earlier identification of document issues reduces delays in document-dependent workflows while maintaining accuracy, accessibility, and equitable treatment.

**Measures:**

- Time from initial submission to sufficient or accepted documentation.
- Time to the relevant service milestone or final determination, where applicable.
- Documentation-related delays, denials, closures, or other negative dispositions, where relevant.
- Differences in outcomes between DocumentAI users and a credible comparison group, where feasible.
- Differences across demographic, accessibility, language, or geographic groups, where data is appropriately available and appropriate to analyze.

**What good looks like:** Document-dependent processing is at least as fast, and ideally faster, with no material deterioration in accuracy, accessibility, or outcomes for particular populations.

**Important distinction:** DocumentAI processing speed is a technical performance measure, not proof that people receive services faster. Downstream improvements should not be attributed to DocumentAI without an appropriate comparison and consideration of other factors.

### 4. Agencies can independently adopt, operate, and extend DocumentAI

**Desired change:** DocumentAI becomes sustainable infrastructure that agencies can deploy and adapt without bespoke changes to the shared core for every use case.

**Measures and evidence:**

- Time and engineering effort required to deploy a new instance and integrate an application.
- Time and effort needed to add or update document types, blueprints, and extraction rules.
- Availability of runbooks, automated tests, monitoring, and administrator documentation.
- Ability of adopting teams to perform routine deployments, upgrades, incident response, and configuration.
- Number and diversity of active implementations, reusable contributions, and supported document workflows.

**What good looks like:** Organizations can operate and evolve the service with clear ownership, repeatable processes, and minimal changes to the shared core code.

## Product Health and Quality Metrics

These measures help maintain a reliable service and diagnose why desired outcomes are or are not improving. They are not, by themselves, evidence of improved public-service outcomes.

| Area | Suggested measures |
| --- | --- |
| **Reliability** | Processing completion rate, technical failure rate, response and error-code distribution |
| **Performance** | Median and 95th-percentile end-to-end processing time, processing backlog |
| **Classification** | Document-type accuracy against labeled test sets, mismatch rate, no-match rate |
| **Extraction** | Field-level extraction accuracy, missing or incorrect field rates |
| **Validation** | Agreement with expected outcomes for configured rules, false-positive and false-negative rates |
| **Human review** | Reviewer correction or override rate and reasons, where captured |
| **Operational readiness** | Service availability, incident frequency and recovery, deployment success, configuration-change lead time |

**How to interpret these measures:**

- Distinguish technical processing failures from documents that appropriately fail configured checks.
- Evaluate accuracy against reviewed reference data; confidence scores alone do not establish accuracy.
- Evaluate classification, extraction, and validation quality by document type and relevant field rather than relying exclusively on aggregate measures.
- Treat corrections and overrides as learning signals that may reflect classification errors, configuration issues, or contextual human judgment.
- Establish operational targets appropriate to each deployment's requirements and risk.

## Measurement Responsibilities

DocumentAI provides technical performance data, but the service alone generally cannot establish whether people have better experiences, staff workload decreases, or agency outcomes improve.

Measuring impact requires shared responsibility.

**DocumentAI maintainers**

- Define shared metric names, calculation guidance, and instrumentation standards.
- Establish quality-testing practices and reference datasets.
- Support consistent measurement of service reliability, performance, classification, extraction, and validation.

**Implementing organizations**

- Define the specific workflow and public-service outcomes relevant to their use cases.
- Track customer actions, reviewer decisions, and downstream processing milestones where appropriate.
- Determine which case- or transaction-level data can be linked to DocumentAI activity.
- Establish local performance targets, evaluation responsibilities, and applicable privacy safeguards.

**Joint evaluation**

- Compare product and program data when authorized and feasible.
- Document missing data, measurement limitations, and possible confounding factors.
- Assess unintended consequences, including additional burden or differences in outcomes across populations.
- Translate findings into product, workflow, and operational improvements.

Where possible, a DocumentAI processing identifier should be linked to a client submission or transaction identifier through a privacy-appropriate integration.

## Recommended Approach to Measuring Impact

### 1. Establish a baseline

Measure existing document workflows before or during implementation, including follow-up requests, review effort, timeliness, and relevant negative outcomes.

### 2. Instrument the full document journey

Collect DocumentAI processing events and, where feasible and permitted, client-side feedback, document replacement, reviewer correction, and downstream workflow events.

### 3. Evaluate quality and safeguards

Use representative, labeled test documents and reviewed examples to evaluate classification, extraction, and validation accuracy. Monitor operational failures and assess potential differences across relevant user groups.

### 4. Compare outcomes fairly

Use randomized or other credible comparison approaches when feasible to assess changes attributable to DocumentAI. Where comparison groups are unavailable, document evaluation limitations and possible confounding factors.

### 5. Improve, then expand

Use findings to refine blueprints, rules, messages, integrations, and workflows before adding additional document types, programs, or users.

## Shared Success Criteria

There is no universal numeric target that will be appropriate for every program, organization, or document type.

Each implementation should define baselines, thresholds, and review responsibilities before launch.

At minimum, DocumentAI implementations should seek evidence that:

- Document processing, classification, and extraction are sufficiently reliable and accurate for the intended workflow.
- People can understand and act on document feedback when it is surfaced to them.
- Avoidable requests for replacement documents and reviewer rework decrease.
- Downstream timeliness and service outcomes do not worsen, including for populations at risk of exclusion.
- Implementing organizations can monitor, configure, and maintain the service safely and independently.

These criteria should inform decisions about expanding DocumentAI to additional document types, use cases, programs, and jurisdictions.

## Scope and Implementation Considerations

DocumentAI provides document-processing capabilities and integration interfaces. It does not supply an entire public-service experience by itself.

Implementing organizations remain responsible for:

- Submission interfaces and the presentation of document feedback.
- Notices, communications, and customer support.
- Case or transaction management and downstream workflows.
- Policy interpretation and applicable document requirements.
- Consent, privacy, security, and accessibility obligations.
- Human review and consequential decisions made using document information.

The shared repository describes capabilities including document processing, configurable blueprints and extraction rules, structured extraction, administrative tooling, multi-tenant access, operational metrics, and observability.

The availability and maturity of capabilities may vary as the product evolves. Consult the repository README and technical documentation for current implementation details and limitations [here](https://github.com/navapbc/strata-documentai-api-enterprise).

---

*This document describes DocumentAI's intended product direction and evaluation framework. It does not imply that all proposed impact measures are currently collected or that DocumentAI has demonstrated causal improvements across all deployments.*

*The vision, strategy, success criteria, and measurement approach should be revisited as new implementations, research findings, operational evidence, and contributor feedback become available.*

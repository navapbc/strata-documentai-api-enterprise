# Use Nova Pro, Not Lite/Micro, for LLM Extraction

- Status: accepted
- Date: 2026-09-29

## Context and Problem Statement

The LLM extraction path (`documentai_api.extractors.llm`, model chosen via `get_llm_extractor_model_id`) receives Textract OCR text and maps it to a schema-validated Pydantic object via `instructor` and Bedrock Converse. It has defaulted to Nova Pro since introduction; this
investigation asked if a cheaper model tier could retain BDA-like accuracy while further reducing the LLM path's cost.

The call is text-only (`ocr_text`, a plain string built from Textract blocks - no image bytes are sent). The open question was purely whether Lite/Micro's reasoning capability was sufficient for this task's actual demands.

## Decision Drivers

- The LLM path must remain as accurate, if not more, than BDA to justify its existence; it is not competing on cost alone.
- Prior work in this same investigation showed the task is more reasoning-heavy than it first appears: resolving an ambiguous slash-date by cross-referencing other evidence on the page (e.g. a DOB), telling apart two adjacent fields that print the identical value, and reliably enumerating every row of a repeating table - all needed explicit prompt work even under Pro.
- `extraction-compare` exists specifically to measure accuracy/cost tradeoff

## Considered Options

- **Nova Pro** (status quo, chosen)
- **Nova Lite** (tested)
- **Nova Micro** (not directly tested - see Decision Outcome)

## Decision Outcome

Chosen option: Nova Pro. Nova Lite was tested by pointing `/docai/dev/llm-extraction/model-id` at `us.amazon.nova-lite-v1:0` and running the full `extraction-compare` suite. Aggregate LLM accuracy (Equivalent Match) via Nova Lite dropped from 82% to 74% versus the Pro baseline, with BDA holding steady at 76-77%. The LLM path's accuracy lead over BDA nearly disappeared. Two concrete issues drove the drop in accuracy, for example `synthetic-assets-life-insurance-policy-render.pdf`:

- `premium_frequency` returned empty using Lite despite being unambiguously printed ("Monthly"); the value extracted correctly by both BDA and Pro.
- `insured_name` returned empty using Nova Lite even though the identical text was correctly extracted for the adjacent `policyholder_name` field on the same document. Nova Lite could not reliably disambiguate two same-valued fields while Nova Pro handled without issue.

Nova Micro was not tested directly: it is a further capability cut below Lite, which already regressed. There was no reason to expect a better outcome with Micro and not worth trading accuracy advantage for minimal cost savings.

### Positive Consequences

- Preserves the LLM path's accuracy advantage over other models
- No further per-document cost change - stays at the pre-existing Pro baseline.

### Negative Consequences

- Highest per-token cost of the three Nova tiers for this step, though this is dwarfed by BDA's flat per-document cost in absolute terms.
- If a future Nova generation changes the small-model accuracy/cost curve, this decision should be re-tested via `extraction-compare` rather than assumed to still hold - see the docstring on `get_llm_extractor_model_id` for the specific failure modes to re-check against.

## Pros and Cons of the Options

### Nova Pro (chosen)

- Good, because it reliably disambiguates adjacent fields sharing the same literal value.
- Good, because it reliably returns simple, unambiguous fields rather than leaving them empty.
- Good, because it preserves the accuracy lead over BDA that justifies this path's existence.
- Bad, because it is the most expensive of the three tiers per token.

### Nova Lite

- Good, because it is roughly 14x cheaper than Pro for this specific step.
- Bad, because it measurably regresses aggregate accuracy (82% -> 74% Equivalent Match).
- Bad, because the regression isn't a formatting nuance - it includes simple fields returned empty and a real loss of same-value field disambiguation.
- Bad, because the savings are marginal in absolute terms next to BDA's flat $0.04/document cost, so the tradeoff doesn't pay for itself.

### Nova Micro

- Not directly tested - ruled out by extension, since it is strictly smaller than Lite, which already failed on tasks Micro would be less equipped to handle, not more.

## Links

- Implementation: [ssm.py](../../documentai-api/src/documentai_api/utils/ssm.py) (`get_llm_extractor_model_id`), [main.tf](../../infra/environments/dev/main.tf) (`llm-extraction/model-id`)
- Extraction path: [llm.py](../../documentai-api/src/documentai_api/extractors/llm.py)
- Measurement tool: [test_extraction_compare.py](../../documentai-api/tests/e2e/test_extraction_compare.py), results in `documentai-api/tests/e2e/results/extraction_compare/`

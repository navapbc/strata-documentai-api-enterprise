# Feature Flags

Feature flags are stored in SSM Parameter Store under `{SSM_PREFIX}/feature-flags/{flag-name}` and cached for 5 minutes. When no SSM prefix is configured (e.g. local development), each flag falls back to its default.

| Flag | SSM name | Default | Purpose | Used in |
|---|---|---|---|---|
| `DOCUMENT_CROP` | `document-crop` | `false` | Enables image document-ROI cropping before BDA processing. | [image_optimization.py](../../documentai-api/src/documentai_api/utils/image_optimization.py) |
| `ENABLE_BLUR_DETECTION` | `enable-blur-detection` | `true` | Runs Textract-based blur detection on each image and records results to DDB. Does not reject documents on its own - see `ENFORCE_BLUR_REJECTION`. | [document_lifecycle.py](../../documentai-api/src/documentai_api/utils/document_lifecycle.py) |
| `ENFORCE_BLUR_REJECTION` | `enforce-blur-rejection` | `false` | When enabled, a blurry detection result sets `BLURRY_DOCUMENT_DETECTED` status and rejects the document. Has no effect if `ENABLE_BLUR_DETECTION` is off. | [document_lifecycle.py](../../documentai-api/src/documentai_api/utils/document_lifecycle.py) |
| `TEXTRACT_IDENTITY_ENABLED` | `textract-identity-enabled` | `false` | Routes documents preclassified as `identity_verification` to Textract AnalyzeID instead of BDA. Can be toggled per-environment without redeploying. | [textract.py](../../documentai-api/src/documentai_api/utils/textract.py) |
| `INCLUDE_MISSING_GEO_WITH_MISSING_FIELDS` | `include-missing-geo-with-missing-fields` | `true` | Treats non-empty fields that lack geometry and fall below the confidence threshold as absent - excluded from non-empty count, average confidence, and extraction rule evaluation (triggers response code 101 if the field is required). | [bda.py](../../documentai-api/src/documentai_api/utils/bda.py), [response_builder.py](../../documentai-api/src/documentai_api/utils/response_builder.py), [extraction_timing.py](../../documentai-api/src/documentai_api/utils/extraction_timing.py) |
| `PRECLASSIFICATION_BASED_ROUTING` | `preclassification-based-routing` | `false` | Routes documents to a category-specific BDA project ARN based on their blueprint match category, rather than always using the default "all" project. Requires `ENABLE_PRECLASSIFICATION_BLUEPRINT_MATCHING` to be on - if blueprint matching is disabled, the match category is never written and routing always falls back to `all`. If routing is enabled but no per-category ARN is configured for the matched category, it silently falls back to `all`. | [bda_invoker.py](../../documentai-api/src/documentai_api/utils/bda_invoker.py) |
| `SKIP_BDA_IF_UNCLASSIFIED` | `skip-bda-if-unclassified` | `false` | Skips BDA invocation when preclassification returns `other_document` (no category match, unsupported type, or classification failure). Despite the flag name, the trigger is the `other_document` signal from preclassify, not blueprint matching. | [bda_invoker.py](../../documentai-api/src/documentai_api/utils/bda_invoker.py) |
| `ENABLE_PRECLASSIFICATION_BLUEPRINT_MATCHING` | `enable-preclassification-blueprint-matching` | `true` | Runs blueprint matching after preclassification to identify which specific blueprint the document matches. The matched category is stored in DDB and drives BDA project routing when `PRECLASSIFICATION_BASED_ROUTING` is also enabled. | [preclassification.py](../../documentai-api/src/documentai_api/utils/preclassification.py) |
| `FLAG_MULTIPLE_DOCUMENTS_IN_MULTIPAGE` | `flag-multiple-documents-in-multipage` | `true` | When enabled, rejects multipage documents where pages are not continuation pages of a single document instance (e.g. two different pay stubs, or a mix of document types). Sets status `MULTIPLE_DOCUMENTS_IN_MULTIPAGE` (response code 401). Has no effect on single-page documents. | [document_lifecycle.py](../../documentai-api/src/documentai_api/utils/document_lifecycle.py) |

## Updating a flag

Set the SSM parameter to `"true"` or `"false"` (string). The change takes effect within 5 minutes as the cache expires - no redeploy needed.

```bash
aws ssm put-parameter \
  --name "/{ssm-prefix}/feature-flags/enable-blur-detection" \
  --value "false" \
  --type String \
  --overwrite
```

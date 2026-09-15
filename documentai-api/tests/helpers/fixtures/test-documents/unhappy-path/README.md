# Unhappy Path Test Documents

This folder mirrors `happy-path/`: it holds synthetic documents that are
*intentionally* bad, wrong, or unreadable, and asserts that the pipeline
correctly rejects/flags them rather than silently mis-processing them.

This is distinct from the negative `responseCode`s already present in
`happy-path/` - those are *legitimate* documents (real burial receipts,
vehicle titles, etc.) that happen to hit a known BDA routing/blueprint gap.
Those stay in `happy-path/` as regression guards for that infra quirk; they
don't belong here because the input itself isn't the problem. Files in this
folder should be bad by design - a real, working pipeline should reject them
no matter how routing or blueprints evolve.

## Choosing the right expected `responseCode`

Pick the code based on *why* the document should fail, not just "it's not
000". See `src/documentai_api/utils/response_codes.py` for the full list.

| Failure mode | Code | When to use it |
| --- | --- | --- |
| Never categorized | `002` `NO_BLUEPRINT_MATCHED` | Right-ish input, but nothing matches any blueprint (e.g. an unsupported document type). |
| Never categorized | `103` `NO_DOCUMENT_DETECTED` | Image is too garbled/blank/illegible for a document to even be detected. |
| Categorized wrong | `102` `MISCATEGORIZED` | Matches a real blueprint, but the wrong one for this document's true type. |
| Categorized right, extraction weak | `105` `LOW_EXTRACTION_CONFIDENCE` | Correct blueprint matched, but field confidence falls below the tenant threshold (e.g. heavy noise/artifacts obscuring text). |
| Categorized right, extraction weak | `101` `MISSING_FIELDS` | Correct blueprint matched, but required fields are absent/blank (e.g. cropped or truncated document). |
| Structural reject (never reaches classification) | `104` `BLURRY_DOCUMENT_DETECTED` | Short-circuits on blur detection. Prefer adding blur-specific cases to `blur/` instead. |
| Structural reject | `106` `PASSWORD_PROTECTED` | Encrypted file, detected before preclassification. |
| Structural reject | `400`/`401` | Multiple documents on one page / inconsistent multi-page upload. |

Don't just default new unhappy-path entries to low-confidence (`105`) -
prefer whichever code above actually matches how the document is meant to
fail, so the suite exercises the full failure taxonomy instead of one path.

## Adding a new unhappy-path document

1. Drop the synthetic file in this folder (follow the naming/watermarking
   conventions in the parent `README.md`).
2. Add an entry to `../expected.json` keyed by the file's path relative to
   `test-documents/`, e.g. `"unhappy-path/synthetic-corrupted-scan.jpg"`.
3. Set `"e2e_enabled": true` and fill in the expected DDB fields
   (`responseCode`, `isDocumentBlurry`, `isPasswordProtected`,
   `preclassificationCategory`, `bdaMatchedDocumentClass`, `content_type`)
   using the table above to pick `responseCode`.
4. `test_app_documents.py::test_post_document` picks up every `e2e_enabled`
   entry in `expected.json` automatically - no code changes needed to add
   more documents here.

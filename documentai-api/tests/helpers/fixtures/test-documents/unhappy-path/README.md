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

## One example per defect, not per document type

Earlier iterations of this folder had three variants (bad-scan, blank-form,
handwritten) per document type, which mostly duplicated the same handful of
failure modes 15x over. We've since scoped this down to match the `blur/`
folder's approach: **one well-verified example per real-world defect**,
regardless of which document type it happens to be. The document type
underneath doesn't matter here - what's under test is whether the pipeline
correctly flags the defect.

| Defect | Status | Fixture |
| --- | --- | --- |
| Scans (poor scan quality) | ✅ Added | `synthetic-bad-scan.png` |
| Missing data fields | ✅ Added | `synthetic-missing-data-fields.pdf` |
| Unclear handwriting | ✅ Added | `synthetic-unclear-handwriting.jpg` |
| Multiple documents included in one file | ✅ Added | `synthetic-multiple-documents.pdf` |
| Crumpled paper | ✅ Added | `synthetic-crumpled.png` |
| Cut off | 🔜 Coming soon | - |

`synthetic-multiple-documents.pdf` was moved here from `happy-path/` (where
it predated this folder's existence) rather than regenerated - it already
consistently trips `401 MULTIPLE_DOCUMENTS_IN_MULTIPAGE`, the correct
failure mode for this defect. A sibling fixture,
`happy-path/synthetic-multipage-mixed-paystub-photo.pdf` (two pay stubs for
different people, same document type), stays in `happy-path/` since it
exercises the separate same-type/different-individual detection path rather
than the "multiple documents" defect itself.

`synthetic-crumpled.png` is a real physically crumpled/photographed utility
bill (not a synthetic wrinkle filter) - verified live (2x, consistent):
preclassification loosely detects the "invoices" category but the
crumpling degrades legibility enough that no blueprint matches at all
(`002`).

Still needed: **cut off**. Notes for whoever picks this up:

- **Cut off** should map to `101 MISSING_FIELDS` per the table below, but
  that code only fires when the tenant has extraction rules with required
  fields configured for the matched document type (see
  `src/documentai_api/utils/extraction_rules.py`) - the e2e test tenant has
  none configured today. Until that's set up, a cropped/truncated document
  will more realistically land on `105` (matched but low confidence) or
  `002` (unrecognizable); target `105` and treat `101` as a follow-up once
  required-field rules exist for the e2e tenant.

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

1. Drop the synthetic file in this folder, named for the *defect* it
   exercises rather than the document type (e.g. `synthetic-cut-off.pdf`) -
   follow the watermarking conventions in the parent `README.md`.
2. Add an entry to `../expected.json` keyed by the file's path relative to
   `test-documents/`, e.g. `"unhappy-path/synthetic-cut-off.pdf"`.
3. Set `"e2e_enabled": true` and fill in the expected DDB fields
   (`responseCode`, `isDocumentBlurry`, `isPasswordProtected`,
   `preclassificationCategory`, `bdaMatchedDocumentClass`, `content_type`)
   using the table above to pick `responseCode`.
4. Update the defect coverage table above to point at the new fixture.
5. `test_app_documents.py::test_post_document` picks up every `e2e_enabled`
   entry in `expected.json` automatically - no code changes needed to add
   more documents here.

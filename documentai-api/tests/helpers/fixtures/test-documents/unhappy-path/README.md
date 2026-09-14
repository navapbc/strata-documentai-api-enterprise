# Unhappy Path Test Documents

This folder mirrors `happy-path/`: it holds synthetic documents that are expected to
fail, be rejected, or otherwise not classify cleanly (e.g. corrupted files, illegible
scans, wrong/unsupported document types, mismatched content, truncated uploads).

## Adding a new unhappy-path document

1. Drop the synthetic file in this folder (follow the naming/watermarking
   conventions in the parent `README.md`).
2. Add an entry to `../expected.json` keyed by the file's path relative to
   `test-documents/`, e.g. `"unhappy-path/synthetic-corrupted-scan.jpg"`.
3. Set `"e2e_enabled": true` and fill in the expected DDB fields
   (`responseCode`, `isDocumentBlurry`, `isPasswordProtected`,
   `preclassificationCategory`, `bdaMatchedDocumentClass`, `content_type`).
4. `test_app_documents.py::test_post_document` picks up every `e2e_enabled`
   entry in `expected.json` automatically - no code changes needed to add
   more documents here.

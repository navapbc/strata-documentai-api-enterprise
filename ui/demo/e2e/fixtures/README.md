# e2e fixtures

Drop the sample document the real-BDA e2e uploads here (gitignored - don't commit
customer documents). Default expected name: `sample.pdf` (override with
`DEMO_E2E_SAMPLE`).

Pick a document that BDA reliably extracts fields **with bounding boxes** from, so
`upload.spec.js` can assert overlay rects render. A W-2, invoice, or similar
structured doc works well.

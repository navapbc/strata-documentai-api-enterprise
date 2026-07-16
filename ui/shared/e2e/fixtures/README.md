# Shared e2e fixtures

## `recording/`

Synthetic document data used by the demo video specs (`e2e-video/`) in both
`ui/admin` and `ui/demo`. These are not test fixtures in the CI sense — they
exist solely to provide deterministic, realistic-looking data for recorded
walkthroughs.

| File | Used by |
|------|---------|
| `w2-document.js` | `ui/admin/e2e-video/admin-walkthrough.spec.js`, `ui/demo/e2e-video/demo-walkthrough.spec.js` |

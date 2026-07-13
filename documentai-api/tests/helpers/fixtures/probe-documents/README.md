# Testing Synthetic Documents - Edge Cases & Known Failures

Synthetic edge-case documents that test DocumentAI extraction and validation.
KF IDs follow the edge-case numbering (below): `KF-<edge case>`, with letters when one edge case has several
distinct failures (`KF-1a`, `KF-1b`, …).

Every file is fake and synthetic: no real customer, applicant, employer, or agency data.
File names are prefixed `synthetic-` and the rendered documents carry visible synthetic markers
("SYNTHETIC SAMPLE DOCUMENT", "FOR TESTING ONLY", or "NOT A REAL RECORD") injected by the generator's safety rules.

See `test-documents/README.md` for the rationale for committing synthetic documents to
this public repository.

## Provenance

Generated 2026-07-06/13 by the [synthetic-doc-generator](https://github.com/navapbc/synthetic-doc-generator).
All blur probes are post-processing transforms (sharp/pdfkit) of the same
base image, committed here as `synthetic-probe-payslip-clean-scan.jpg`.
The fiscal-year payslip (KF-13) was generated 2026-07-13 by that repo's
`scripts/generate-fiscal-year-payslip.mjs`; the Spanish payslip (KF-17) comes
from its `out/from-existing/17-multi-language` set (2026-07-06 run).

## The tenant edge-case list and coverage

| # | Edge case | Coverage |
|---|-----------|----------|
| 1 | Blurry/missing document detection | KF-1a..1e |
| 2 | Unsupported or invalid document types | KF-2a, KF-2b |
| 3 | Tampered documents | KF-3 |
| 4 | Fabricated documents | KF-4 |
| 5 | Document type mismatches | KF-5 |
| 6 | Name discrepancies | KF-6 |
| 7 | Low quality resolution | KF-7 |
| 8 | Partial document capture | KF-8a..8c |
| 9 | Multi-page documents | KF-9 (regression guard — red since 2026-07-13, see table) |
| 10 | Extremely large file(s) | no fixture — the 288 MB upload is already rejected cleanly with 413, and the file is too large to commit |
| 11 | Password protected PDF | KF-11 |
| 12 | Scanned image embedded in PDF | green control (`…pdf-mixed-pages.pdf`), no known failure |
| 13 | Fiscal vs. calendar year employer reporting | KF-13 |
| 14 | Income period outside of eligibility window | KF-14 |
| 15 | Future dated documents | KF-15 |
| 16 | Invalid employer | KF-16 |
| 17 | Multi-language | KF-17 |

## The known failures

Response codes are the tenant table in `documentai_api.utils.response_codes`. The
2026-07-06 probe runs established that only the classification (`002`) and
average-confidence (`105`) gates were live; every document-level validation code
(`101/102/103/104/106/400`) was unreachable from the input side, and hard failures
surfaced as raw HTTP 500s rather than `999`. The 2026-07-13 e2e run against dev
(probe-run.log) re-observed every case with this branch's Textract gates enabled:
blur (`104`) and no-document (`103`) are now live and no case crashed with a raw
5xx, but password-protection (`106`) still never fires and all business-rule and
category gates (`101/102/400`) remain unreachable. Rows unmarked with a date below
were reconfirmed unchanged on 2026-07-13.

| Issue | Failure | Fixture | Spec asserts | Observed (dev, 2026-07) |
|-------|---------|---------|--------------|--------------------------|
| KF-1a | Extreme blur crashes the pipeline | `…payslip-blur-gaussian-sigma6.jpeg` | 104 | **104 ✓** (2026-07-13; was HTTP 500 "Failed to retrieve results") |
| KF-1b | Content-free page crashes the pipeline | `…gray-page.jpeg` | 103 | **103 ✓** (2026-07-13; was HTTP 500) |
| KF-1c | Crashes are raw 500s, never a graceful code | *(cross-cutting; filed under edge case 1 because the observed crashes are its inputs)* | every case: terminal outcome must be a responseCode, never 5xx | **no raw 5xx in the 2026-07-13 run ✓** (was HTTP 500) |
| KF-1d | Blur gate (104) never fires | `…payslip-blur-focus-miss.jpeg` | 104 | **104 ✓** (2026-07-13; was 000 / Payslip) |
| KF-1e | Degradation causes silent misclassification | `…payslip-blur-gaussian-sigma4.jpeg` | 104 or 105 | **gated ✓** (2026-07-13, code in {104, 105}; was 000 / **Receipts**) |
| KF-2a | Multi-document gate (400) never fires | `…two-docs-one-page.jpeg` | 400 | 000, W-2 half ignored ✗ |
| KF-2b | Out-of-scope doc type accepted | `…receipt-grocery.jpg` (declared income) | 102 | 000 / Receipts ✗ |
| KF-3 | Tampered document accepted clean | `…payslip-tampered.jpg` | never 000 | 000 ✗ |
| KF-4 | Fabricated document accepted | `…letter-fabricated.jpg` | never 000 | 000 ✗ |
| KF-5 | Miscategorization gate (102) never fires; declared category inert | 3 chimera fixtures + clean payslip as `category=identity` | 102 | 000, content-driven class ✗ |
| KF-6 | Name discrepancy undetected | `…payslip-name-discrepancy.jpg` | never 000 | 000 ✗ |
| KF-7 | Per-field confidence not gated | `…payslip-faint-fields.jpg` | 105 | 000 with fields at 0.06–0.41 conf ✗ |
| KF-8a | Missing-required-fields gate (101) can't fire | `…payslip-missing-fields.jpeg` | 101 + fields listed in `missingRequiredFieldList` | 000, list null ✗ |
| KF-8b | Absent fields hallucinated | `…payslip-missing-fields.jpeg` (`emptyFields`) | pay-period fields empty, not invented | fabricated dates at 0.05 conf ✗ |
| KF-8c | Confident blanks indistinguishable | `…payslip-missing-fields.jpeg` (via KF-8a list) | absent YTD fields reported missing | empty at 0.93–0.94 conf, not reported ✗ |
| KF-9 | Multi-page extraction (page-1 dominance was suspected, inconclusive) | `…1040-two-pages.pdf` | 000 / Form-1040 + page-2-only field values | **DRIFT ✗** 2026-07-13 e2e run: 000 / Form-1040 but `total_refund` and `is_signed` mismatched — page-2 extraction failed after passing earlier the same day (jobId e1c77357 vs 1674a5ba) |
| KF-11 | Encrypted PDF hangs forever | `…password-protected.pdf` | 106 (60s budget) | stuck `processing` 40+ min ✗ (reconfirmed 2026-07-13: still no terminal state within 60s; 106 never fired) |
| KF-13 | Fiscal-year YTD reporting basis unflagged | `…payslip-fiscal-year-ytd.jpeg` | never 000 | 000 ✗ (2026-07-13, FYTD figures accepted clean) |
| KF-14 | Stale (out-of-window) income unflagged | `…payslip-stale-income.jpg` | never 000 | 000 ✗ |
| KF-15 | Future-dated document unflagged | `…payslip-future-dated.jpg` | never 000 | 000 ✗ |
| KF-16 | Implausible employer unflagged | `…payslip-implausible-employer.jpg` | never 000 | 000 ✗ |
| KF-17 | Multi-language (Spanish/English) handling | `…payslip-spanish.jpg` | 000 or 105, class Payslip | **✓** (2026-07-13, classified Payslip; green regression guard) |

Controls (no KF tag, green): clean scan, σ2.5 / σ3.5 / motion-15px / low-dpi blur
boundary cases, the mixed sharp+blurred PDF, and the 422 invalid-category upload.
On 2026-07-13 the low-dpi control returned `104` (`not_supported`) — the live blur
gate now claims the 8×-upscaled thumbnail. That is a legitimate boundary call
consistent with the σ2.5/σ3.5/motion controls, so `104` was added to its accepted
set in `expected.json` (decision recorded there).

**`forbiddenResponseCodes`** (KF-3/4/6/13/14/15/16) is the spec floor for anomalies the
  tenant code table has no code for yet: whatever the eventual signal is, the document
  must not validate clean with `000`. If the tenant rules these out of scope for the
  API, disable the case with `e2e_enabled: false` and record the decision here.

**SSM feature-flag flips, verified 2026-07-13:** KF-1a, KF-1b, KF-1d, and KF-1e
flipped green as predicted — Textract-based blur detection (104) and no-document
detection (103) are live in dev. KF-11 did **not** flip: the encrypted PDF still
reached no terminal state within its 60s budget, so password-protection detection
(106) is either not enabled or not effective in this environment. If a gate returns
a *different* graceful code than asserted here (e.g. 105 instead of 104 for
focus-miss), update `expected.json` deliberately with a comment recording the
decision.

**New drift to investigate (2026-07-13):** the KF-9 multi-page guard failed —
`total_refund` and `is_signed` no longer match the page-2 values — despite the same
fixture passing earlier the same day. Either extraction is nondeterministic on this
document or page-2 handling regressed alongside the gate rollout.
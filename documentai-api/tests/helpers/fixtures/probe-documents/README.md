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

## Tenant triage (2026-07-30)

The tenant triaged the edge-case list and confirmed four cases as in-scope
failures to fix and seven as out of scope for the API:

- **In scope, failing:** low quality resolution (#7), partial document capture
  (#8), multi-page documents (#9), password protected PDF (#11).
- **Out of scope:** tampered documents (#3), fabricated documents (#4),
  document type mismatches (#5), the date-validation cases (#13, #14, #15),
  and invalid employer (#16).
- **Out of scope, decided separately:** name discrepancies (#6). The Slack
  triage did not mention edge case 6 either way; it was ruled out of scope in
  the follow-up rather than by the tenant message, so it is called out here
  distinctly in case that needs confirming back with the tenant.

One red case is still **untriaged**: the multi-document gate (KF-2a, edge case
#2), which is neither confirmed in scope nor ruled out. Note that its sibling
KF-2b turned green on 2026-07-30, so edge case 2 is now half-green, half-open.

The ten out-of-scope probe cases (KF-3, KF-4, the three KF-5 chimeras, KF-6,
KF-13, KF-14, KF-15, KF-16) are now `e2e_enabled: false` in `expected.json`, each
with the decision and its last observed result recorded in its own comment block.
The fixtures and their specs stay committed so the cases can be revived if the
tenant's scope changes. Collection drops from 29 items to 19, and the suite from
16 failures to 6 (KF-2a, KF-7, KF-8a, KF-9, KF-11, and the invalid-category
control), with 13 still passing.

**KF-5's declared-category leg is deliberately kept enabled.** It turned green on
2026-07-30 (see *New drift*, below), so `test_miscategorized_declared_category`
now guards working behavior instead of asserting an unimplemented gate — a
failure there is a regression in the declared-vs-detected check, not the old
known failure. Only the three content-vs-layout chimera legs of #5 are disabled.

## The tenant edge-case list and coverage

| # | Edge case | Coverage | Status (2026-07-30) |
|---|-----------|----------|---------------------|
| 1 | Blurry/missing document detection | KF-1a..1e | green since 2026-07-13 |
| 2 | Unsupported or invalid document types | KF-2a, KF-2b | KF-2b green (new); KF-2a red, **untriaged** |
| 3 | Tampered documents | KF-3 | red — **out of scope** |
| 4 | Fabricated documents | KF-4 | red — **out of scope** |
| 5 | Document type mismatches | KF-5 | chimera legs red — **out of scope**; declared-category leg green (new) |
| 6 | Name discrepancies | KF-6 | red — **out of scope** (decided in follow-up, not by the tenant triage) |
| 7 | Low quality resolution | KF-7 | red — **in scope** |
| 8 | Partial document capture | KF-8a..8c | red — **in scope** |
| 9 | Multi-page documents | KF-9 | red — **in scope** (drift now confirmed persistent) |
| 10 | Extremely large file(s) | no fixture — the 288 MB upload is already rejected cleanly with 413, and the file is too large to commit | n/a |
| 11 | Password protected PDF | KF-11 | red — **in scope** |
| 12 | Scanned image embedded in PDF | green control (`…pdf-mixed-pages.pdf`), no known failure | green |
| 13 | Fiscal vs. calendar year employer reporting | KF-13 | red — **out of scope** |
| 14 | Income period outside of eligibility window | KF-14 | red — **out of scope** |
| 15 | Future dated documents | KF-15 | red — **out of scope** |
| 16 | Invalid employer | KF-16 | red — **out of scope** |
| 17 | Multi-language | KF-17 | green |

## The known failures

Response codes are the tenant table in `documentai_api.utils.response_codes`. The
2026-07-06 probe runs established that only the classification (`002`) and
average-confidence (`105`) gates were live; every document-level validation code
(`101/102/103/104/106/400`) was unreachable from the input side, and hard failures
surfaced as raw HTTP 500s rather than `999`. The 2026-07-13 e2e run against dev
(probe-run.log) re-observed every case with this branch's Textract gates enabled:
blur (`104`) and no-document (`103`) went live and no case crashed with a raw 5xx.
The **2026-07-30 e2e run against dev** (29 items, 16 failed / 13 passed in 4m49s)
reconfirmed every 07-13 result except for three status flips in category
handling: `102` now fires for two of the four KF-5/KF-2b category cases, while
the invalid-category upload control regressed from `422` to `202` (see *New
drift*, below). Password-protection (`106`) still never fires, and the
missing-fields (`101`) and multi-document (`400`) gates remain unreachable. Rows
unmarked with a date below were reconfirmed unchanged on 2026-07-30.

| Issue | Failure | Fixture | Spec asserts | Observed (dev, 2026-07-30) |
|-------|---------|---------|--------------|-----------------------------|
| KF-1a | Extreme blur crashes the pipeline | `…payslip-blur-gaussian-sigma6.jpeg` | 104 | **104 ✓** (since 2026-07-13; was HTTP 500 "Failed to retrieve results") |
| KF-1b | Content-free page crashes the pipeline | `…gray-page.jpeg` | 103 | **103 ✓** (since 2026-07-13; was HTTP 500) |
| KF-1c | Crashes are raw 500s, never a graceful code | *(cross-cutting; filed under edge case 1 because the observed crashes are its inputs)* | every case: terminal outcome must be a responseCode, never 5xx | **no raw 5xx in the 2026-07-30 run ✓** (was HTTP 500) |
| KF-1d | Blur gate (104) never fires | `…payslip-blur-focus-miss.jpeg` | 104 | **104 ✓** (since 2026-07-13; was 000 / Payslip) |
| KF-1e | Degradation causes silent misclassification | `…payslip-blur-gaussian-sigma4.jpeg` | 104 or 105 | **gated ✓** (since 2026-07-13, code in {104, 105}; was 000 / **Receipts**) |
| KF-2a | Multi-document gate (400) never fires | `…two-docs-one-page.jpeg` | 400 | 000, W-2 half ignored ✗ (jobId 236d1046) — **untriaged** |
| KF-2b | Out-of-scope doc type accepted | `…receipt-grocery.jpg` (declared income) | 102 | **102 ✓** (new 2026-07-30; was 000 / Receipts) |
| KF-3 | Tampered document accepted clean | `…payslip-tampered.jpg` | never 000 | 000 ✗ (jobId 15c7db5a) — **out of scope** |
| KF-4 | Fabricated document accepted | `…letter-fabricated.jpg` | never 000 | 000 ✗ (jobId eac84c4c) — **out of scope** |
| KF-5 | Miscategorization gate (102) never fires; declared category inert | 3 chimera fixtures + clean payslip as `category=identity` | 102 | split: declared-category leg **102 ✓** (new 2026-07-30), 3 chimeras still 000 ✗ (jobIds 6fd02b87, a25bc672, 86cc602f) — **out of scope** |
| KF-6 | Name discrepancy undetected | `…payslip-name-discrepancy.jpg` | never 000 | 000 ✗ (jobId a4b84d63) — **out of scope** (follow-up decision) |
| KF-7 | Per-field confidence not gated | `…payslip-faint-fields.jpg` | 105 | 000 ✗ (jobId a146c9ed) — **in scope** |
| KF-8a | Missing-required-fields gate (101) can't fire | `…payslip-missing-fields.jpeg` | 101 + fields listed in `missingRequiredFieldList` | 000, list null ✗ (jobId a6d9c09e) — **in scope** |
| KF-8b | Absent fields hallucinated | `…payslip-missing-fields.jpeg` (`emptyFields`) | pay-period fields empty, not invented | still fabricated: PayPeriodStartDate at 0.05, PayPeriodEndDate at 0.04 conf ✗ — **in scope** |
| KF-8c | Confident blanks indistinguishable | `…payslip-missing-fields.jpeg` (via KF-8a list) | absent YTD fields reported missing | still unreported (list null) ✗ — **in scope** |
| KF-9 | Multi-page (page-2-only) extraction fails | `…1040-two-pages.pdf` | 000 / Form-1040 + page-2-only field values | 000 / Form-1040 but `total_refund` and `is_signed` both mismatched ✗ (jobId 66fe7db5) — the 07-13 drift is now **a confirmed, repeatable failure**, not a one-off — **in scope** |
| KF-11 | Encrypted PDF hangs forever | `…password-protected.pdf` | 106 (60s budget) | still no terminal state within the 60s budget, stuck `jobStatus=processing`, 106 never fired ✗ (jobId 7c22e9d9) — **in scope** |
| KF-13 | Fiscal-year YTD reporting basis unflagged | `…payslip-fiscal-year-ytd.jpeg` | never 000 | 000 ✗ (jobId 17c6e344) — **out of scope** |
| KF-14 | Stale (out-of-window) income unflagged | `…payslip-stale-income.jpg` | never 000 | 000 ✗ (jobId c143e381) — **out of scope** |
| KF-15 | Future-dated document unflagged | `…payslip-future-dated.jpg` | never 000 | 000 ✗ (jobId 65729f3e) — **out of scope** |
| KF-16 | Implausible employer unflagged | `…payslip-implausible-employer.jpg` | never 000 | 000 ✗ (jobId adabcb17) — **out of scope** |
| KF-17 | Multi-language (Spanish/English) handling | `…payslip-spanish.jpg` | 000 or 105, class Payslip | **✓** (classified Payslip; green regression guard) |

Controls (no KF tag): clean scan, σ2.5 / σ3.5 / motion-15px / low-dpi blur
boundary cases, and the mixed sharp+blurred PDF — all green on 2026-07-30. The
422 invalid-category upload control is **now red**; see *New drift*.
On 2026-07-13 the low-dpi control returned `104` (`not_supported`) — the live blur
gate now claims the 8×-upscaled thumbnail. That is a legitimate boundary call
consistent with the σ2.5/σ3.5/motion controls, so `104` was added to its accepted
set in `expected.json` (decision recorded there).

**`forbiddenResponseCodes`** (KF-3/4/6/13/14/15/16) is the spec floor for anomalies the
  tenant code table has no code for yet: whatever the eventual signal is, the document
  must not validate clean with `000`. If the tenant rules these out of scope for the
  API, disable the case with `e2e_enabled: false` and record the decision here.
  As of 2026-07-30 **all seven** have been ruled out of scope and disabled, so no
  `forbiddenResponseCodes` case is currently collected. The floor is documented
  here rather than enforced; revive the cases if any of these anomalies come back
  into scope.

**SSM feature-flag flips, verified 2026-07-13:** KF-1a, KF-1b, KF-1d, and KF-1e
flipped green as predicted — Textract-based blur detection (104) and no-document
detection (103) are live in dev, and all four stayed green on 2026-07-30. KF-11
has still not flipped: the encrypted PDF reaches no terminal state within its 60s
budget, so password-protection detection (106) is either not enabled or not
effective in this environment. If a gate returns a *different* graceful code than
asserted here (e.g. 105 instead of 104 for focus-miss), update `expected.json`
deliberately with a comment recording the decision.

**New drift to investigate (2026-07-30):** category handling changed in three
correlated ways, and the net effect includes one regression.

- **Regression — the invalid-category control now fails.** Uploading with
  `category=not-a-category` used to be rejected at upload with `422`; it now
  returns `202` and creates a job (`jobId 7a4fe94b`). The category value is no
  longer enum-validated at the upload boundary, so a typo'd or unknown category
  is silently accepted.
- **Improvement — `102` now fires for two category cases.** KF-2b (grocery
  receipt declared `income`) and KF-5's declared-category leg (clean payslip
  declared `identity`) both returned `102` and now pass. The declared category is
  no longer inert.
- These two most likely share a cause: validation appears to have moved from an
  upload-time enum check to a declared-vs-detected comparison in the pipeline. If
  so, restoring the `422` should be additive and should not disturb the new `102`
  behavior — but that is a hypothesis, not a verified finding.
- **Not explained by the above:** the three KF-5 chimera fixtures still return
  `000` while declaring `category=income`, even though the declared-category
  comparison is now live. The chimeras are content-classified as
  Bank-Statement / Receipts / Payslip, and at least the Receipts case looks
  inconsistent with KF-2b now returning `102` on the same declared/detected
  pairing. The run does not report `matchedDocumentClass` for these cases (the
  spec does not assert on it), so today's detected classes are unknown. Worth
  capturing the full response bodies before drawing a conclusion. Note this is
  in the #5 out-of-scope bucket, so it may not be worth chasing beyond
  understanding the mechanism.

**Resolved drift:** the 2026-07-13 KF-9 anomaly (`total_refund` / `is_signed` not
matching the page-2 values after the same fixture passed earlier that day) is no
longer open as "nondeterminism vs. regression" — it failed the same way on
2026-07-30 and the tenant has confirmed #9 as an in-scope failure. Treat it as a
regression in page-2 extraction.

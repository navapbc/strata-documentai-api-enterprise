# Reject ODT Uploads with a Friendly Error Instead of Converting

- Status: accepted
- Date: 2026-07-22

## Context and Problem Statement

When adding support for DOC and DOCX uploads, OpenDocument Text (.odt) was also considered. ODT is not natively supported by Amazon Bedrock Data Automation (BDA), so files would need to be converted to PDF before processing. What is the right approach for ODT files?

## Considered Options

- **Bundle headless LibreOffice in the Lambda container** and shell out to `soffice --headless --convert-to pdf`
- **Pure-Python conversion** via a library (e.g. `odt2pdf`, `odfpy` + `reportlab`)
- **Reject ODT with a friendly error** directing users to re-upload as PDF or DOCX

## Decision Outcome

Chosen option: reject ODT with a friendly error, because the two conversion paths both introduce unacceptable operational cost with no clear user demand for ODT specifically.

The error message is: *"OpenDocument Text (.odt) files aren't currently supported. Please save the document as PDF or Microsoft Word (.docx) and try again."*

Both PDF and DOCX are now natively accepted, so users have a clear, low-friction path forward.

## Pros and Cons of the Options

### Bundle headless LibreOffice

- Good, because conversion fidelity is high
- Bad, because it adds ~300MB to the Lambda container image, increasing cold start time significantly
- Bad, because `soffice` requires a writable home directory and display environment, adding Lambda-specific workarounds
- Bad, because it introduces a system dependency that must be patched and maintained

### Pure-Python conversion

- Good, because no system dependencies
- Bad, because available libraries (`odt2pdf`) are not Lambda-runnable: empty `__init__`, Windows-only paths (`C:\Program Files\...\soffice.exe`), and a file-path API rather than bytes-in/bytes-out
- Bad, because layout fidelity for complex documents is poor
- Bad, because it adds a fragile dependency with no active maintenance signal

### Reject with friendly error (chosen)

- Good, because zero new dependencies and no conversion code to maintain
- Good, because the error message gives users a clear, actionable alternative
- Good, because both suggested alternatives (PDF, DOCX) are natively supported by BDA
- Bad, because users with ODT files must convert manually before uploading

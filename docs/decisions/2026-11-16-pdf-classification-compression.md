# Rasterize oversized scan PDFs before Bedrock classification

- Status: accepted
- Date: 2026-11-16

Technical Story: WH-380 scan PDF (15.9 MB, 4 pages) was taking ~6s to compress and still exceeding the Bedrock payload limit in some cases.

## Context and Problem Statement

Before sending a PDF to Bedrock for classification, we downscale any embedded images that exceed `CLASSIFICATION_MAX_IMAGE_PX` (1400px). This reduces payload size and latency. Scan PDFs from physical documents or scanner software embed full-resolution bitmaps - often 2400px or larger - and are the primary target.

How should we compress those images while keeping the pipeline fast and correct?

## Decision Drivers

- Compression must run in Lambda within the overall classification budget (~20s total, Bedrock takes 7–11s)
- Digital PDFs with no oversized images must not pay any compression cost
- BDA receives the original bytes regardless, so text layer loss in the compressed copy is acceptable
- The solution must handle all common scan encodings, not just a specific colorspace or filter

## Considered Options

- **pypdf stream-swap**: replace image XObject streams in-place using pypdf's `ImageFile.replace()`
- **pypdfium2 page render**: render each page to a bitmap via pypdfium2, JPEG-encode, reassemble
- **Ghostscript**: shell out to `gs -dPDFSETTINGS=/screen`

## Decision Outcome

Chosen option: **pypdfium2 page render**, with a cheap read-only pre-scan that returns the original bytes immediately when no image exceeds the limit.

The pre-scan reads `/Width` and `/Height` directly from image XObject dictionaries without decoding any pixel data. It exits as soon as it finds one oversized image, or returns the original bytes if none are found. This eliminates all cost for digital PDFs.

When compression is needed, pypdfium2 renders each page at `scale = max_dimension_px / max(page_width_pt, page_height_pt)`, producing a bitmap with the long side at exactly `max_dimension_px` pixels. Pages are JPEG-encoded at quality 85 and reassembled into a new PDF.

Measured on the WH-380 scan (4 pages, 15.9 MB): 0.14s warm versus 1.08s for the stream-swap approach.

### Positive Consequences

- ~7x faster than stream-swap on real scan PDFs
- Handles all page content regardless of image encoding, colorspace, or filter
- Pre-scan makes the digital PDF case effectively free
- pypdfium2 is already a project dependency

### Negative Consequences

- Text layer is lost in the compressed copy. Searchable scans (OCR'd by scanner software) lose their hidden text layer. This is accepted because Bedrock classification uses visual content, and BDA receives the original bytes with the text layer intact.
- All pages are rasterized even if only one image is oversized. A mixed document with one large image and many small pages pays the render cost for every page.
- The pre-scan reads only images listed directly in each page's `/Resources` `/XObject` dictionary. Images nested inside form XObjects, or inline images, are not seen, so such a PDF skips compression and is sent to Bedrock at full size. This is uncommon for scanner output; the only cost is a slower, larger request.
- If the flatten raises (for example a malformed page or a zero-size page), `compress_pdf_for_classification` returns the original bytes, which can be large (the WH-380 scan is 15.9 MB). Bedrock may reject a payload that size, in which case preclassification fails, is logged, and the document falls through to BDA without a classification.

### Classification windows and the multipage check

PDFs are truncated to `MAX_PAGES_PER_DOCUMENT` (5) before classification, then split into windows of `PAGES_PER_CLASSIFICATION_CALL` pages and classified in parallel. The window is **5 pages**, equal to the page limit, so an upload is a single call that sees every page together.

**Window size is not a latency lever.** Laptop timings on the WH-380 scan suggested a large page effect (4 pages averaged 22.2s against about 15s for 1 or 2 pages), but Lambda X-Ray traces showed each Bedrock call has a floor of about 7s: a 1-page window took 6.94s, a 3-page window 7.81s, and the old 4-page call 7.75s. Output is only about 125 tokens, so input pages are cheap on top of the floor. `document.preclassification` measured 8.1-9.0s with windows of 3 and of 5. Blueprint matching (first window only, large text prompt, 6.5-7.5s) runs in parallel and has the same floor. We tried a window of 3 with a one-page overlap and removed it: a single 5-page call already compares every page with every other, so smaller windows give each call less context, add a Bedrock call per 4-5 page upload, and add no detection.

**Cross-window `document_type` comparison removed.** The previous aggregation flagged an inconsistency when high-confidence windows returned different `document_type` strings. That field is free text, so the same document is worded differently from window to window, and a form followed by its privacy notice reads as two documents: the 32-page PA-600 packet was flagged `multiple_documents_in_multipage` (response 401) with the windows returning "application form", "application", "privacy notice" and "unknown". Label equality also cannot detect the same type of document for a different person. Aggregation now flags only when a window's own judgement (the per-call `has_multipage_inconsistency` from the classification prompt) flags, and carries that window's reason.

**Truncation moved before classification.** BDA reads only the first 5 pages, but preclassification previously saw the whole PDF; the PA-600 sent 54,439 input tokens over 7 windows for pages the pipeline discards. Truncation happens in `_run_preclassification` before compression, so neither compress nor classification touches pages BDA discards (a long scan would otherwise be fully rendered by the flatten first). `preclassify_document` truncates again, which is a no-op in the pipeline but keeps the CLI and any other caller consistent. This covers every upload path, including presigned uploads. Because the window now equals the page limit, a PDF always produces one window; the windowing and aggregation code remains for a window set below the limit.

**Consequence: the multipage and per-page document-count checks cover only the first 5 pages.** A different document or person starting on page 6 or later is not flagged (`multiple_documents_in_multipage`, response 401). This matches what BDA extracts, since it reads only the same 5 pages, so nothing from later pages reaches the output. Catching a mixed upload beyond page 5 would need a separate design, such as a cheap check on later pages or rejecting PDFs above a page count.

Open work and levers:
- **Multipage check quality.** The check is one model judgement per call. How well it catches a different document or a different person starting mid-upload has not been measured; it needs a mixed-upload fixture set.
- **Per-call floor.** A faster model (Nova Lite, which needs the JSON-fence parsing fix and was not chosen in the OCR mapping ADR) or latency-optimized inference (not checked for Nova Pro in us-east-1).
- Quota: 500 requests/min and 2M tokens/min on the `us.amazon.nova-pro-v1:0` profile; tokens/min is the binding limit.

## Pros and Cons of the Options

### pypdf stream-swap

Swaps only the oversized image streams, leaving page structure, text layer, and vector content untouched.

- Good, because text layer is preserved
- Good, because only oversized images are touched
- Bad, because pypdf decodes every image through `page.images` and re-encodes it with `ImageFile.replace()`, which takes ~1.08s locally on the WH-380 scan (5.9s in Lambda)
- Bad, because the faster variant, rewriting the image streams directly to skip that decode, was prototyped and failed: it only matched a narrow set of encodings (8-bpc RGB, Flate), and its output was corrupt (zlib data labelled as JPEG), so it would also mean hand-maintained PDF stream code

### pypdfium2 page render

Renders each page as a flat bitmap.

- Good, because handles all page content regardless of encoding
- Good, because ~7x faster than stream-swap on real scan PDFs
- Bad, because text layer is lost in the compressed copy

### Ghostscript

- Good, because well-tested, handles all PDF content
- Bad, because adds a system dependency not present in the Lambda image
- Bad, because subprocess overhead and cold-start cost

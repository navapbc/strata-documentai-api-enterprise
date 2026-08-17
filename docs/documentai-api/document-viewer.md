# Document viewer

When a document is processed, the platform stores both the original image and the extracted fields. The document viewer shows them together - the source image on one side, the extracted fields on the other, with each field linked to the region of the image it came from.

## See it in action

![Document viewer walkthrough](media/document-viewer-walkthrough.gif)

## Bounding box overlay

Every extracted field has coordinates from the model - the bounding box of the text region it was read from. The viewer draws those boxes as an overlay on the document image. Hovering over a field in the results panel highlights its bounding box on the image. Hovering over a box on the image highlights the corresponding field in the panel.

This makes extraction accuracy easy to verify: the overlay shows what the model read and where it found it.

## What gets shown

The viewer displays the fields returned in the processed result for that document. If the tenant has extraction rules configured, only the fields allowed by those rules appear - required and optional fields that were found, plus any required fields that were missing. Fields excluded by the rule aren't shown.

If no extraction rule exists for the tenant and document type, all extracted fields are shown.

## Field status

Each field shows its extracted value and a confidence indicator from the model. Required fields that couldn't be extracted are shown as missing, so reviewers can immediately see what needs follow-up.

## Where it appears

The document viewer is available in both the admin console and the demo UI. In the admin console, it opens as a side panel when you select a document from the processed documents list. In the demo UI, it appears after a document finishes processing.

"""CLI tool to generate ground-truth geometry candidates for fixture documents.

For each fixture that has an expected JSON:
  - geo-matched:    resolved fields are merged into the expected JSON under a "geometry" key.
                    Existing geometry entries are never overwritten (human picks survive re-runs).
  - manual-review:  ambiguous or list-value fields written to <fixtures_dir>/expected/geometry_manual.json.
  - text-not-found: fields whose normalized value had no OCR match, also in expected/geometry_manual.json.
"""

from __future__ import annotations

import dataclasses
import json
import re
from pathlib import Path
from typing import Annotated

import pypdfium2  # type: ignore[import-not-found]
import pytesseract  # type: ignore[import-not-found]
import typer
from PIL import Image

from documentai_api.utils.extraction_compare_client import normalize_value as _normalize_value
from documentai_api.utils.schemas import is_list_field

app = typer.Typer()

_DOC_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg"}
_FIXTURE_KEY_ORDER = {
    "fields": 0,
    "geometry": 1,
    "expected_document_class": 2,
    "language": 3,
    "notes": 4,
}
_COMPUTED_FIELDS = {
    "BalanceGreaterCheck",
    "BillingDateBeforeDueDate",
    "Is_NumMeterIDsListed",
    "Is_PrevGreaterThanCurr",
    "Is_ValidPinCode",
    "Is_ValidState",
    "VALIDATION",
    "are_field_names_sufficient",
    "expire",
    "has_signature",
    "is_gross_pay_valid",
    "is_total_amount_greater_than_equal_to_current_charges",
    "is_ytd_gross_pay_highest",
}


@dataclasses.dataclass
class _OcrLine:
    text: str
    page: int
    left: float
    top: float
    width: float
    height: float


@dataclasses.dataclass
class _OcrWord:
    text: str
    page: int
    left: float
    top: float
    width: float
    height: float


@dataclasses.dataclass
class _BBox:
    page: int
    left: float
    top: float
    width: float
    height: float


def _normalize(value: object) -> str:
    """Normalize for OCR matching: date/currency normalization then lowercase, strip punctuation."""
    text = str(value) if not isinstance(value, str) else value
    text = _normalize_value(text)
    text = re.sub(r"[^\w\s]", "", text)
    return re.sub(r"\s+", " ", text).strip()


def _bbox(line: _OcrLine | _OcrWord) -> _BBox:
    return _BBox(page=line.page, left=line.left, top=line.top, width=line.width, height=line.height)


def _ocr_image(
    image: Image.Image, page: int, lang: str = "eng"
) -> tuple[list[_OcrLine], list[_OcrWord]]:
    """Run pytesseract; return line-level and word-level results."""
    data = pytesseract.image_to_data(image, lang=lang, output_type=pytesseract.Output.DICT)
    w, h = image.size
    line_bboxes: dict[tuple[int, int, int], dict[str, float]] = {}
    line_words: dict[tuple[int, int, int], list[str]] = {}
    words: list[_OcrWord] = []
    for i, level in enumerate(data["level"]):
        key = (data["block_num"][i], data["par_num"][i], data["line_num"][i])
        if level == 4:
            line_bboxes[key] = {
                "left": data["left"][i] / w,
                "top": data["top"][i] / h,
                "width": data["width"][i] / w,
                "height": data["height"][i] / h,
            }
        elif level == 5 and data["text"][i].strip():
            line_words.setdefault(key, []).append(data["text"][i])
            words.append(
                _OcrWord(
                    text=data["text"][i],
                    page=page,
                    left=data["left"][i] / w,
                    top=data["top"][i] / h,
                    width=data["width"][i] / w,
                    height=data["height"][i] / h,
                )
            )
    lines = [
        _OcrLine(text=" ".join(ws), page=page, **line_bboxes[key])
        for key, ws in line_words.items()
        if key in line_bboxes
    ]
    return lines, words


def _ocr_document(path: Path, lang: str = "eng") -> tuple[list[_OcrLine], list[_OcrWord]]:
    """OCR all pages via pytesseract + pypdfium2; each entry carries its page index."""
    if path.suffix.lower() == ".pdf":
        all_lines: list[_OcrLine] = []
        all_words: list[_OcrWord] = []
        pdf = pypdfium2.PdfDocument(str(path))
        for i, pdf_page in enumerate(pdf):
            bitmap = pdf_page.render(scale=2.0)
            lines, words = _ocr_image(bitmap.to_pil(), page=i, lang=lang)
            all_lines.extend(lines)
            all_words.extend(words)
        return all_lines, all_words

    lines, words = _ocr_image(Image.open(path).convert("RGB"), page=0, lang=lang)
    return lines, words


def _find_document(fixtures_dir: Path, stem: str) -> Path | None:
    for ext in _DOC_EXTENSIONS:
        candidate = fixtures_dir / (stem + ext)
        if candidate.exists():
            return candidate
    return None


@app.command()
def main(
    fixtures_dir: Annotated[
        Path,
        typer.Option(
            "--fixtures-dir",
            "-f",
            help="Directory containing fixture documents and expected/ subdir",
        ),
    ] = Path("tests/helpers/fixtures/test-documents/happy-path"),
) -> None:
    """Generate ground-truth geometry candidates by OCR-matching expected field values.

    Uses pytesseract + pypdfium2 (independent of Textract) so ground-truth geometry
    is not circular with the OCR-mapping extractor.

    Resolved geometry is written to geometry.matched in each fixture JSON.
    Unresolved fields are written to geometry.not_matched.text_not_found or geometry.not_matched.ambiguous.
    Existing matched entries are never overwritten so human picks survive re-runs.
    """
    expected_dir = fixtures_dir / "expected"
    if not expected_dir.is_dir():
        typer.echo(f"Expected dir not found: {expected_dir}", err=True)
        raise typer.Exit(1)

    total_matched = 0
    total_manual = 0
    total_not_found = 0

    for expected_path in sorted(expected_dir.glob("*.json")):
        stem = expected_path.stem
        document_path = _find_document(fixtures_dir, stem)

        if document_path is None:
            typer.echo(typer.style(f"[SKIP] no document found for {stem}", fg=typer.colors.RED))
            continue

        fixture = json.loads(expected_path.read_text())
        fields: dict[str, object] = fixture.get("fields", {})
        doc_type = fixture.get("expected_document_class") or ""

        all_lines, all_words = _ocr_document(document_path, lang=fixture.get("language", "eng"))

        existing_geo: dict[str, object] = fixture.get("geometry", {})
        # Seed only from manual entries — pytesseract entries are rebuilt on every run
        # so the algorithm can improve without manual picks being overwritten.
        _raw = existing_geo.get("matched")
        existing_matched: dict[str, object] = _raw if isinstance(_raw, dict) else existing_geo
        matched_geo: dict[str, object] = {
            k: v
            for k, v in existing_matched.items()
            if isinstance(v, dict) and v.get("determination_method") == "manual"
        }
        not_matched: dict[str, dict[str, object]] = {"text_not_found": {}, "ambiguous": {}}
        not_found_count = 0

        for field, value in fields.items():
            if value is None:
                continue

            if field in matched_geo:
                continue

            if is_list_field(doc_type, field):
                not_matched["ambiguous"][field] = {"reason": "list_value", "expected_value": value}
                continue

            if field in _COMPUTED_FIELDS:
                continue

            norm_expected = _normalize(value)
            # exact line match, then word match, then substring line match (last resort — line
            # bboxes span the full row including labels, so word-level is preferred when available)
            matches: list[_OcrLine | _OcrWord] = [
                ln for ln in all_lines if _normalize(ln.text) == norm_expected
            ]

            if not matches:
                matches = [w for w in all_words if _normalize(w.text) == norm_expected]

            if not matches:
                matches = [ln for ln in all_lines if norm_expected in _normalize(ln.text)]

            if len(matches) == 1:
                matched_geo[field] = {
                    "determination_method": "pytesseract",
                    "explanation": "Resolved via pytesseract OCR match.",
                    **dataclasses.asdict(_bbox(matches[0])),
                }
            elif len(matches) == 0:
                not_found_count += 1
                not_matched["text_not_found"][field] = {"expected_value": value}
            else:
                not_matched["ambiguous"][field] = {
                    "reason": "multiple_ocr_matches",
                    "expected_value": value,
                    "candidates": [dataclasses.asdict(_bbox(m)) for m in matches],
                }

        geometry_out: dict[str, object] = {"matched": matched_geo}
        if not_matched["text_not_found"] or not_matched["ambiguous"]:
            geometry_out["not_matched"] = {k: v for k, v in not_matched.items() if v}
        fixture = dict(
            sorted(
                {**fixture, "geometry": geometry_out}.items(),
                key=lambda kv: _FIXTURE_KEY_ORDER.get(kv[0], 99),
            )
        )
        expected_path.write_text(json.dumps(fixture, indent=2, ensure_ascii=False) + "\n")

        matched = len(matched_geo)
        manual_count = len(not_matched["ambiguous"])

        total_matched += matched
        total_manual += manual_count
        total_not_found += not_found_count

        typer.echo(
            f"[OCR] {document_path.name} - "
            + typer.style(f"geo-matched={matched}", fg=typer.colors.GREEN)
            + "  "
            + typer.style(f"manual-review={manual_count}", fg=typer.colors.YELLOW)
            + "  "
            + typer.style(f"text-not-found={not_found_count}", fg=typer.colors.RED)
        )

    typer.echo(
        "\nDone. "
        + typer.style(f"geo-matched={total_matched}", fg=typer.colors.GREEN)
        + "  "
        + typer.style(f"manual-review={total_manual}", fg=typer.colors.YELLOW)
        + "  "
        + typer.style(f"text-not-found={total_not_found}", fg=typer.colors.RED)
    )


if __name__ == "__main__":
    app()

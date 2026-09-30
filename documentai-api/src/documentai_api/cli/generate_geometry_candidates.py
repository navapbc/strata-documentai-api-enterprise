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

app = typer.Typer()

_DOC_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg"}
_MANUAL_REVIEW_FILENAME = "geometry_manual.json"
_FIXTURE_KEY_ORDER = {"fields": 0, "geometry": 1, "notes": 2}
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


@dataclasses.dataclass
class _ManualReview:
    reason: str
    expected_value: object
    candidates: list[_BBox] = dataclasses.field(default_factory=list)


def _normalize(value: object) -> str:
    """Normalize for OCR matching: date/currency normalization then lowercase, strip punctuation."""
    text = str(value) if not isinstance(value, str) else value
    text = _normalize_value(text)
    text = re.sub(r"[^\w\s]", "", text)
    return re.sub(r"\s+", " ", text).strip()


def _bbox(line: _OcrLine | _OcrWord) -> _BBox:
    return _BBox(page=line.page, left=line.left, top=line.top, width=line.width, height=line.height)


def _is_list_value(value: object) -> bool:
    if not isinstance(value, str):
        return False
    return len([p for p in value.split(",") if p.strip()]) > 1


def _ocr_image(image: Image.Image, page: int) -> tuple[list[_OcrLine], list[_OcrWord]]:
    """Run pytesseract; return line-level and word-level results."""
    data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
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


def _ocr_document(path: Path) -> tuple[list[_OcrLine], list[_OcrWord]]:
    """OCR all pages via pytesseract + pypdfium2; each entry carries its page index."""
    if path.suffix.lower() == ".pdf":
        all_lines: list[_OcrLine] = []
        all_words: list[_OcrWord] = []
        pdf = pypdfium2.PdfDocument(str(path))
        for i, pdf_page in enumerate(pdf):
            bitmap = pdf_page.render(scale=2.0)
            lines, words = _ocr_image(bitmap.to_pil(), page=i)
            all_lines.extend(lines)
            all_words.extend(words)
        return all_lines, all_words

    lines, words = _ocr_image(Image.open(path).convert("RGB"), page=0)
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

    Resolved geometry is merged into each expected JSON under a "geometry" key.
    Existing geometry entries are never overwritten so human picks survive re-runs.
    All manual-review and text-not-found fields are written to <fixtures_dir>/expected/geometry_manual.json.
    """
    expected_dir = fixtures_dir / "expected"
    if not expected_dir.is_dir():
        typer.echo(f"Expected dir not found: {expected_dir}", err=True)
        raise typer.Exit(1)

    all_manual: dict[str, dict[str, _ManualReview]] = {}
    total_matched = 0
    total_manual = 0
    total_not_found = 0

    for expected_path in sorted(expected_dir.glob("*.json")):
        if expected_path.name == _MANUAL_REVIEW_FILENAME:
            continue

        stem = expected_path.stem
        document_path = _find_document(fixtures_dir, stem)

        if document_path is None:
            typer.echo(typer.style(f"[SKIP] no document found for {stem}", fg=typer.colors.RED))
            continue

        fixture = json.loads(expected_path.read_text())
        fields: dict[str, object] = fixture.get("fields", {})

        all_lines, all_words = _ocr_document(document_path)

        matched_geo: dict[str, object] = {}
        manual_review: dict[str, _ManualReview] = {}
        not_found_count = 0

        for field, value in fields.items():
            if value is None:
                continue

            if _is_list_value(value):
                manual_review[field] = _ManualReview(reason="list_value", expected_value=value)
                continue

            if field in _COMPUTED_FIELDS:
                continue

            norm_expected = _normalize(value)
            # try exact line match first, then word match for single-token values
            matches: list[_OcrLine | _OcrWord] = [
                ln for ln in all_lines if _normalize(ln.text) == norm_expected
            ]
            if not matches:
                matches = [w for w in all_words if _normalize(w.text) == norm_expected]

            if len(matches) == 1:
                matched_geo[field] = dataclasses.asdict(_bbox(matches[0]))
            elif len(matches) == 0:
                not_found_count += 1
                manual_review[field] = _ManualReview(reason="text_not_found", expected_value=value)
            else:
                manual_review[field] = _ManualReview(
                    reason="ambiguous",
                    expected_value=value,
                    candidates=[_bbox(m) for m in matches],
                )

        fixture = dict(
            sorted(
                {**fixture, "geometry": matched_geo}.items(),
                key=lambda kv: _FIXTURE_KEY_ORDER.get(kv[0], 99),
            )
        )
        expected_path.write_text(json.dumps(fixture, indent=2, ensure_ascii=False) + "\n")

        newly_matched = len(matched_geo)
        manual_count = len([e for e in manual_review.values() if e.reason != "text_not_found"])

        total_matched += newly_matched
        total_manual += manual_count
        total_not_found += not_found_count

        if manual_review:
            all_manual[stem] = manual_review

        typer.echo(
            f"[OCR] {document_path.name} - "
            + typer.style(f"geo-matched={newly_matched}", fg=typer.colors.GREEN)
            + "  "
            + typer.style(f"manual-review={manual_count}", fg=typer.colors.YELLOW)
            + "  "
            + typer.style(f"text-not-found={not_found_count}", fg=typer.colors.RED)
        )

    (expected_dir / _MANUAL_REVIEW_FILENAME).write_text(
        json.dumps(
            {
                stem: {f: dataclasses.asdict(e) for f, e in entries.items()}
                for stem, entries in all_manual.items()
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n"
    )

    typer.echo(
        "\nDone. "
        + typer.style(f"geo-matched={total_matched}", fg=typer.colors.GREEN)
        + "  "
        + typer.style(f"manual-review={total_manual}", fg=typer.colors.YELLOW)
        + "  "
        + typer.style(f"text-not-found={total_not_found}", fg=typer.colors.RED)
    )
    typer.echo(f"Manual review written to {expected_dir}/{_MANUAL_REVIEW_FILENAME}")


if __name__ == "__main__":
    app()

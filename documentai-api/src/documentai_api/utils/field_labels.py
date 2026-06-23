"""Field label lookup for human-readable display names."""

import json
import re
from functools import lru_cache
from pathlib import Path

from documentai_api.logging import get_logger

logger = get_logger(__name__)

LABELS_DIR = Path(__file__).resolve().parent.parent / "config" / "field_labels"

_ACRONYMS = {
    "ssn",
    "ein",
    "id",
    "dso",
    "uscis",
    "va",
    "ira",
    "ytd",
    "po",
    "omb",
    "qty",
    "amt",
    "cusip",
    "mrz",
    "usa",
    "tin",
    "ptin",
    "pin",
}


def _split_words(part: str) -> list[str]:
    """Split a single name segment into words on snake_case, camelCase, and digit boundaries."""
    if "_" in part:
        tokens = part.split("_")
    elif any(c.isupper() for c in part[1:]):
        tokens = re.sub(r"([a-z])([A-Z])", r"\1 \2", part).split()
    else:
        tokens = [part]
    # Separate letter/digit runs so "Box17Row0" -> "Box 17 Row 0", "Line1" -> "Line 1".
    words = []
    for token in tokens:
        words.extend(re.findall(r"[A-Za-z]+|\d+", token) or [token])
    return words


def _to_human_label(field_name: str) -> str:
    """Best-effort conversion of a field name to a human-readable label."""
    words = []
    for part in field_name.split("."):
        words.extend(_split_words(part))
    return " ".join(w.upper() if w.lower() in _ACRONYMS else w.capitalize() for w in words)


@lru_cache(maxsize=64)
def _load_labels(document_type: str) -> dict[str, str]:
    """Load label map for a document type, cached."""
    label_file = LABELS_DIR / f"{document_type.lower()}.json"
    if label_file.exists():
        labels: dict[str, str] = json.loads(label_file.read_text())
        return labels
    logger.warning(
        "No field-label file for document type %r (looked for %s); "
        "falling back to auto-generated labels",
        document_type,
        label_file.name,
    )
    return {}


def get_field_label(document_type: str | None, field_name: str) -> str:
    """Look up display name for a field. Falls back to auto-generated label."""
    if document_type:
        labels = _load_labels(document_type)
        label = labels.get(field_name)
        if label:
            return label
    return _to_human_label(field_name)

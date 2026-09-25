import importlib.resources
import json
from functools import lru_cache


@lru_cache(maxsize=1)
def _load_model_cost() -> dict[str, dict[str, float]]:
    data = importlib.resources.files("documentai_api.config").joinpath("model_cost.json").read_text()
    return json.loads(data)  # type: ignore[return-value]


def compute_llm_cost(model_id: str, input_tokens: int, output_tokens: int) -> float | None:
    """Return the cost in USD for a single model invocation, or None if the model is unpriced."""
    pricing = _load_model_cost().get(model_id)
    if not pricing:
        return None

    return float((input_tokens * pricing["input_per_1m"] + output_tokens * pricing["output_per_1m"]) / 1_000_000)


def compute_textract_cost(pages: int) -> float:
    """Return the cost in USD for Textract AnalyzeID on the given number of pages."""
    pricing = _load_model_cost()["textract"]
    return float(pages * pricing["per_page"])


def compute_bda_cost(pages: int, is_custom: bool) -> float:
    """Return the cost in USD for BDA on the given number of pages."""
    pricing = _load_model_cost()["bda"]
    rate = pricing["custom_output_per_page"] if is_custom else pricing["standard_output_per_page"]
    return float(pages * rate)

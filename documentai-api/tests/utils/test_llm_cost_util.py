import pytest

from documentai_api.utils.llm_cost import compute_llm_cost


@pytest.mark.parametrize(
    ("model_id", "input_tokens", "output_tokens", "expected"),
    [
        # us.amazon.nova-pro-v1:0 — input: $0.80/1M, output: $3.20/1M
        ("us.amazon.nova-pro-v1:0", 1_234, 567, (1_234 * 0.80 + 567 * 3.20) / 1_000_000),
        # us.amazon.nova-lite-v1:0 — input: $0.06/1M, output: $0.24/1M
        ("us.amazon.nova-lite-v1:0", 8_901, 2_345, (8_901 * 0.06 + 2_345 * 0.24) / 1_000_000),
        # us.amazon.nova-micro-v1:0 — input: $0.035/1M, output: $0.14/1M
        ("us.amazon.nova-micro-v1:0", 4_567, 891, (4_567 * 0.035 + 891 * 0.14) / 1_000_000),
        # us.amazon.nova-2-lite-v1:0 — input: $0.33/1M, output: $2.75/1M
        ("us.amazon.nova-2-lite-v1:0", 3_210, 6_789, (3_210 * 0.33 + 6_789 * 2.75) / 1_000_000),
        # zero tokens
        ("us.amazon.nova-pro-v1:0", 0, 0, 0.0),
    ],
)
def test_compute_llm_cost(model_id, input_tokens, output_tokens, expected):
    assert compute_llm_cost(model_id, input_tokens, output_tokens) == pytest.approx(expected)


def test_compute_llm_cost_unknown_model_returns_none():
    assert compute_llm_cost("unknown-model", input_tokens=1_234, output_tokens=567) is None

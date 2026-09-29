import pytest

from documentai_api.utils.numbers import clean_number, median, normalize


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("920 kWh", "920"),
        ("640", "640"),
        ("-323.75", "-323.75"),
        ("$1,234.56", "1234.56"),
        ("1,000", "1000"),
        ("abc", "abc"),  # no numeric match — return as-is
        ("", ""),
    ],
)
def test_clean_number(value, expected):
    assert clean_number(value) == expected


@pytest.mark.parametrize(
    ("vals", "expected"),
    [
        ([1.0, 2.0, 3.0], 2.0),
        ([1.0, 2.0], 1.5),
        ([5.0], 5.0),
        ([], None),
    ],
)
def test_median(vals, expected):
    assert median(vals) == expected


@pytest.mark.parametrize(
    ("value", "min_val", "max_val", "expected"),
    [
        (50, 0, 100, 0.5),
        (0, 0, 100, 0.0),
        (100, 0, 100, 1.0),
        (-10, 0, 100, 0.0),  # resolves to 0
        (150, 0, 100, 1.0),  # resolves to 1
    ],
)
def test_normalize(value, min_val, max_val, expected):
    assert normalize(value, min_val, max_val) == expected

from typing import Any


def assert_dict_contains(d: dict[str, Any], expected: dict[str, Any]) -> None:
    """Assert that d contains all the key-value pairs in expected.

    Do this by checking to see if adding `expected` to `d` leaves `d` unchanged.
    """
    assert d | expected == d

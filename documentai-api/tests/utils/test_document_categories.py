import pytest

from documentai_api.utils import document_categories as categories_util
from documentai_api.utils.cache import get_cache


@pytest.fixture(autouse=True)
def clear_cache():
    get_cache().clear()
    yield
    get_cache().clear()


def test_get_processing_percentage_returns_stored_value(document_categories_table):
    document_categories_table.put_item(
        Item={"tenantId": "t1", "categoryName": "income", "processingPercentage": "0.5"}
    )
    assert categories_util.get_processing_percentage("t1", "income") == pytest.approx(0.5)


def test_get_processing_percentage_defaults_to_1_when_missing(document_categories_table):
    assert categories_util.get_processing_percentage("t1", "no-such-category") == pytest.approx(1.0)


def test_get_processing_percentage_defaults_to_1_when_field_absent(document_categories_table):
    document_categories_table.put_item(Item={"tenantId": "t1", "categoryName": "income"})
    assert categories_util.get_processing_percentage("t1", "income") == pytest.approx(1.0)


def test_get_processing_percentage_caches_result(document_categories_table, mocker):
    document_categories_table.put_item(
        Item={"tenantId": "t1", "categoryName": "income", "processingPercentage": "0.7"}
    )
    mock_get = mocker.patch(
        "documentai_api.utils.document_categories.get_category",
        wraps=categories_util.get_category,
    )

    categories_util.get_processing_percentage("t1", "income")
    categories_util.get_processing_percentage("t1", "income")

    mock_get.assert_called_once()


def test_update_category_invalidates_processing_percentage_cache(document_categories_table, mocker):
    document_categories_table.put_item(
        Item={
            "tenantId": "t1",
            "categoryName": "income",
            "processingPercentage": "0.5",
            "displayName": "Income",
            "isActive": True,
        }
    )

    categories_util.get_processing_percentage("t1", "income")
    assert get_cache().get("processing_percentage:t1:income") == pytest.approx(0.5)

    categories_util.update_category("t1", "income", processing_percentage=0.25)

    assert get_cache().get("processing_percentage:t1:income") is None


def test_update_category_without_processing_percentage_does_not_invalidate_cache(
    document_categories_table,
):
    document_categories_table.put_item(
        Item={
            "tenantId": "t1",
            "categoryName": "income",
            "processingPercentage": "0.5",
            "displayName": "Income",
            "isActive": True,
        }
    )

    categories_util.get_processing_percentage("t1", "income")
    assert get_cache().get("processing_percentage:t1:income") == pytest.approx(0.5)

    categories_util.update_category("t1", "income", display_name="Updated Income")

    assert get_cache().get("processing_percentage:t1:income") == pytest.approx(0.5)

import pytest

from documentai_api.utils import document_categories as categories_util
from documentai_api.utils.cache import get_cache


@pytest.fixture(autouse=True)
def clear_cache():
    get_cache().clear()
    yield
    get_cache().clear()


@pytest.fixture
def clear_registered_categories():
    categories_util._registered_categories.clear()
    yield
    categories_util._registered_categories.clear()


def test_get_processing_percentage_returns_stored_value(document_categories_table):
    document_categories_table.put_item(
        Item={"tenantId": "t1", "categoryName": "income", "processingPercentage": "0.5"}
    )
    assert categories_util.get_processing_percentage("t1", "income") == pytest.approx(0.5)


@pytest.mark.parametrize(
    "item",
    [
        None,
        {"tenantId": "t1", "categoryName": "income"},
    ],
)
def test_get_processing_percentage_defaults_to_1(document_categories_table, item):
    if item:
        document_categories_table.put_item(Item=item)

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


def test_auto_register_category_skips_ddb_on_duplicate(
    document_categories_table, clear_registered_categories, mocker
):
    mock_get_table = mocker.patch(
        "documentai_api.utils.document_categories.AWSClientFactory.get_ddb_table",
        return_value=document_categories_table,
    )
    categories_util.auto_register_category("t1", "income")
    categories_util.auto_register_category("t1", "income")
    mock_get_table.assert_called_once()


def test_auto_register_category_evicts_oldest_at_cap(
    document_categories_table, clear_registered_categories, mocker
):
    mocker.patch("documentai_api.utils.document_categories._MAX_REGISTERED_CATEGORIES", 2)
    categories_util.auto_register_category("t1", "a")
    categories_util.auto_register_category("t1", "b")
    categories_util.auto_register_category("t1", "c")
    assert ("t1", "a") not in categories_util._registered_categories
    assert ("t1", "b") in categories_util._registered_categories
    assert ("t1", "c") in categories_util._registered_categories


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

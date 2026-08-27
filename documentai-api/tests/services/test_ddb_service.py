"""Tests for services/ddb.py."""

from documentai_api.services import ddb as ddb_service


def test_get_item(ddb_table):
    """Get item from DynamoDB table."""
    ddb_table.put_item(Item={"id": "123", "name": "test"})
    result = ddb_service.get_item(ddb_table.name, {"id": "123"})
    assert result == {"id": "123", "name": "test"}


def test_get_item_not_found(ddb_table):
    """Get item returns None when not found."""
    result = ddb_service.get_item(ddb_table.name, {"id": "123"})
    assert result is None


def test_get_item_eventual_consistency(ddb_table):
    """Get item with eventual consistency."""
    ddb_table.put_item(Item={"id": "123"})
    result = ddb_service.get_item(ddb_table.name, {"id": "123"}, consistent_read=False)
    assert result == {"id": "123"}


def test_put_item(ddb_table):
    """Put item to DynamoDB table."""
    item = {"id": "123", "name": "test"}
    ddb_service.put_item(ddb_table.name, item)

    response = ddb_table.get_item(Key={"id": "123"})
    assert response["Item"] == item


def test_update_item(ddb_table):
    """Update item in DynamoDB table."""
    ddb_table.put_item(Item={"id": "123", "description": "old"})

    key = {"id": "123"}
    update_expr = "SET description = :description"
    expr_values = {":description": "updated"}

    ddb_service.update_item(ddb_table.name, key, update_expr, expr_values)

    response = ddb_table.get_item(Key={"id": "123"})
    assert response["Item"]["description"] == "updated"


def test_query_by_key(ddb_table):
    """Query DynamoDB GSI by partition key only."""
    ddb_table.put_item(Item={"id": "123", "userId": "user-123", "category": "a"})
    ddb_table.put_item(Item={"id": "456", "userId": "user-123", "category": "b"})

    result = ddb_service.query_by_key(
        ddb_table.name, ddb_table.test_index_name, "userId", "user-123"
    )

    assert len(result) == 2
    assert {item["id"] for item in result} == {"123", "456"}


def test_query_by_key_no_results(ddb_table):
    """Query returns empty list when no items found."""
    result = ddb_service.query_by_key(
        ddb_table.name, ddb_table.test_index_name, "userId", "user-999"
    )
    assert result == []


def test_query_by_key_with_sort_key(ddb_table):
    """Query DynamoDB GSI by partition key and sort key returns only matching item."""
    ddb_table.put_item(Item={"id": "123", "userId": "user-123", "category": "a"})
    ddb_table.put_item(Item={"id": "456", "userId": "user-123", "category": "b"})

    result = ddb_service.query_by_key(
        ddb_table.name, ddb_table.test_index_name, "userId", "user-123", "category", "a"
    )

    assert len(result) == 1
    assert result[0]["id"] == "123"


def test_query_by_key_with_sort_key_no_results(ddb_table):
    """Query with sort key returns empty list when no items match."""
    ddb_table.put_item(Item={"id": "123", "userId": "user-123", "category": "a"})

    result = ddb_service.query_by_key(
        ddb_table.name, ddb_table.test_index_name, "userId", "user-123", "category", "z"
    )

    assert result == []


def test_query_by_key_paginates_past_one_page(ddb_table):
    """Query follows LastEvaluatedKey so results aren't truncated at the 1MB page limit."""
    # DynamoDB caps a query page at 1MB. Write enough large items under one GSI
    # key to span multiple pages; ~350KB each x 5 = ~1.75MB.
    blob = "x" * 350_000
    expected_ids = {f"id-{i}" for i in range(5)}
    for i, item_id in enumerate(expected_ids):
        ddb_table.put_item(
            Item={"id": item_id, "userId": "user-123", "category": str(i), "blob": blob}
        )

    result = ddb_service.query_by_key(
        ddb_table.name, ddb_table.test_index_name, "userId", "user-123"
    )

    assert {item["id"] for item in result} == expected_ids

"""DynamoDB service methods."""

from typing import Any, cast

from documentai_api.utils.aws_client_factory import AWSClientFactory


def get_item(
    table_name: str, key: dict[str, Any], consistent_read: bool = True
) -> dict[str, Any] | None:
    """Get item from DynamoDB table."""
    ddb_table = AWSClientFactory.get_ddb_table(table_name)
    response = ddb_table.get_item(Key=key, ConsistentRead=consistent_read)
    return cast(dict[str, Any], response.get("Item"))


def put_item(
    table_name: str, item: dict[str, Any], condition_expression: str | None = None
) -> None:
    """Put item to DynamoDB table. Optional condition_expression for conditional writes."""
    ddb_table = AWSClientFactory.get_ddb_table(table_name)
    kwargs: dict[str, Any] = {"Item": item}
    if condition_expression:
        kwargs["ConditionExpression"] = condition_expression
    ddb_table.put_item(**kwargs)


def update_item(
    table_name: str,
    key: dict[str, Any],
    update_expression: str,
    expression_values: dict[str, Any],
    expression_names: dict[str, str] | None = None,
) -> None:
    """Update item in DynamoDB table.

    Pass `expression_names` to alias reserved attribute names (e.g. `ttl`) in the
    update expression via `#placeholder` references.
    """
    ddb_table = AWSClientFactory.get_ddb_table(table_name)
    kwargs: dict[str, Any] = {
        "Key": key,
        "UpdateExpression": update_expression,
        "ExpressionAttributeValues": expression_values,
    }
    if expression_names:
        kwargs["ExpressionAttributeNames"] = expression_names
    ddb_table.update_item(**kwargs)


def delete_item(table_name: str, key: dict[str, Any]) -> None:
    """Delete item from DynamoDB table."""
    table = AWSClientFactory.get_ddb_table(table_name)
    table.delete_item(Key=key)


def query_by_pk(table_name: str, pk_name: str, pk_value: str) -> list[dict[str, Any]]:
    """Query DynamoDB table by partition key."""
    table = AWSClientFactory.get_ddb_table(table_name)
    response = table.query(
        KeyConditionExpression=f"{pk_name} = :val",
        ExpressionAttributeValues={":val": pk_value},
    )
    return response.get("Items", [])


def scan(table_name: str) -> list[dict[str, Any]]:
    """Scan all items in a DynamoDB table, handling pagination."""
    table = AWSClientFactory.get_ddb_table(table_name)
    items: list[dict[str, Any]] = []
    kwargs: dict[str, Any] = {}

    while True:
        response = table.scan(**kwargs)
        items.extend(response.get("Items", []))
        last_key = response.get("LastEvaluatedKey")
        if not last_key:
            break
        kwargs["ExclusiveStartKey"] = last_key

    return items


def query_by_key(
    table_name: str, index_name: str, key_name: str, key_value: str
) -> list[dict[str, Any]]:
    """Query DynamoDB table by key using GSI."""
    import boto3

    ddb_table = AWSClientFactory.get_ddb_table(table_name)
    key_condition = boto3.dynamodb.conditions.Key(key_name).eq(key_value)  # type: ignore[attr-defined]

    items: list[dict[str, Any]] = []
    last_evaluated_key: dict[str, Any] | None = None
    while True:
        kwargs: dict[str, Any] = {
            "IndexName": index_name,
            "KeyConditionExpression": key_condition,
        }
        if last_evaluated_key:
            kwargs["ExclusiveStartKey"] = last_evaluated_key

        response = ddb_table.query(**kwargs)
        items.extend(dict(item) for item in response.get("Items", []))

        last_evaluated_key = response.get("LastEvaluatedKey")
        if not last_evaluated_key:
            break

    return items

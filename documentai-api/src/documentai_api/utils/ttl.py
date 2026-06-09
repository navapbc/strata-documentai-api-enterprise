from datetime import UTC, datetime


def ttl_epoch_in_days(days: int) -> int:
    """Unix-epoch seconds `days` in the future, for a DynamoDB `ttl` attribute."""
    return int(datetime.now(UTC).timestamp()) + days * 24 * 60 * 60

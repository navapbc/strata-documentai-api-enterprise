import traceback
from collections.abc import Callable
from functools import wraps
from typing import Any

from documentai_api.logging import get_logger

logger = get_logger(__name__)


def handle_lambda_errors(handler_func: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator to standardize Lambda error handling and logging."""

    @wraps(handler_func)
    def wrapper(event: dict[str, Any], context: Any) -> Any:
        try:
            return handler_func(event, context)
        except Exception as e:
            logger.error(f"Handler {handler_func.__name__} failed: {e}")
            logger.error(traceback.format_exc())
            return {"statusCode": 500, "body": str(e)}

    return wrapper

"""SSM Parameter Store helpers with caching."""

import os

from documentai_api.logging import get_logger
from documentai_api.services import ssm as ssm_service
from documentai_api.utils.cache import get_cache

logger = get_logger(__name__)

_SSM_CACHE_TTL_MINUTES = 5


def _get_env_name() -> str:
    env_name = os.getenv("ENVIRONMENT_NAME")
    if not env_name:
        raise ValueError("ENVIRONMENT_NAME is required but not set")
    return env_name


def get_parameter_value(param_name: str, default: str | None = None) -> str:
    """Get SSM parameter with caching."""
    cache = get_cache()
    cached = cache.get(f"ssm:{param_name}")
    if cached is not None:
        return str(cached)

    try:
        value = ssm_service.get_parameter(param_name)
        cache.add(f"ssm:{param_name}", value, _SSM_CACHE_TTL_MINUTES)
        return value
    except Exception as e:
        logger.error(f"Failed to get parameter {param_name}: {e}")
        if default is not None:
            return default
        raise


def get_bda_percentage(document_type: str) -> float:
    """Get BDA processing percentage for document type (0.0-1.0)."""
    # TODO: fetch from SSM, update tests to monkeypatch ENVIRONMENT_NAME
    # standardized = re.sub(r"\s+", "-", document_type.strip())
    # param_name = f"/idp/config/{_get_env_name()}/bda-sample-percentage/{standardized}"
    # percentage_str = get_parameter_value(param_name, default="0")
    # return float(percentage_str) / 100.0
    return 1.0


def get_field_confidence_threshold() -> float:
    """Get BDA confidence threshold from Parameter Store."""
    param_name = f"/idp/config/{_get_env_name()}/bda-field-confidence-threshold"
    threshold_str = get_parameter_value(param_name, default="0.7")
    return float(threshold_str)


def get_empty_field_threshold_percentage() -> float:
    """Get empty field threshold percentage from parameter store."""
    param_name = f"/idp/config/{_get_env_name()}/empty-field-threshold-percentage"
    percentage_str = get_parameter_value(param_name, default="50")
    return float(percentage_str) / 100.0

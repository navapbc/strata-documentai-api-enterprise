"""SSM Parameter Store helpers with caching."""

from documentai_api.logging import get_logger
from documentai_api.services import ssm as ssm_service
from documentai_api.utils.cache import get_cache

logger = get_logger(__name__)

_SSM_CACHE_TTL_MINUTES = 5


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


def is_document_crop_enabled() -> bool:
    """Whether image document-ROI cropping is on. SSM-configurable at runtime; default off.

    Mirrors the preclassification-routing flag: the parameter path is provided via
    env config so it can be toggled in SSM without a redeploy. Defaults to off
    (opt-in) when the flag is unconfigured or the parameter is missing, so it can
    be validated per-environment before being turned on.
    """
    from documentai_api.config.env import get_aws_config

    config = get_aws_config()
    if not config.document_crop_param:
        return False
    return get_parameter_value(config.document_crop_param, default="false").lower() == "true"


def is_blur_detection_enabled() -> bool:
    """Whether Textract-based blur detection runs on each image.

    When enabled, detect_blur is called and results (is_blurry, analysis_failed,
    avg confidence, word count, llm_checked) are recorded to DDB. Does not reject
    documents unless enforce-blur-rejection is also enabled. Default: true (param
    absent means enabled so detection is on by default).
    """
    from documentai_api.config.env import get_aws_config

    config = get_aws_config()
    if not config.enable_blur_detection_param:
        return True
    return get_parameter_value(config.enable_blur_detection_param, default="true").lower() == "true"


def is_blur_rejection_enforced() -> bool:
    """Whether a blurry detection actually rejects the document.

    When false, blur detection still runs (if enabled) and records results, but
    does not set BLURRY_DOCUMENT_DETECTED status. Default: false.
    """
    from documentai_api.config.env import get_aws_config

    config = get_aws_config()
    if not config.enforce_blur_rejection_param:
        return False
    return (
        get_parameter_value(config.enforce_blur_rejection_param, default="false").lower() == "true"
    )


def is_textract_identity_enabled() -> bool:
    """Whether Textract AnalyzeID is used for identity documents.

    When enabled, documents preclassified as identity_verification are routed to
    Textract AnalyzeID instead of BDA. Controlled via an SSM parameter so it can
    be toggled per-environment without redeploying.
    """
    from documentai_api.config.env import get_aws_config

    config = get_aws_config()
    if not config.textract_identity_param:
        return False
    return get_parameter_value(config.textract_identity_param, default="false").lower() == "true"

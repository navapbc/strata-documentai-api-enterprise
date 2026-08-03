"""SSM Parameter Store helpers with caching."""

from documentai_api.config.constants import FeatureFlags
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


def _get_flag(flag: str, default: bool) -> bool:
    from documentai_api.config.env import get_aws_config

    config = get_aws_config()
    if not config.ssm_prefix:
        logger.info(f"{flag}: {default} (default, no SSM prefix)")
        return default
    param = f"{config.ssm_prefix}/feature-flags/{flag}"
    value = get_parameter_value(param, default=str(default).lower()).lower() == "true"
    logger.info(f"{flag}: {value}")
    return value


def is_document_crop_enabled() -> bool:
    """Whether image document-ROI cropping is on. SSM-configurable at runtime; default off."""
    return _get_flag(FeatureFlags.DOCUMENT_CROP, default=False)


def is_blur_detection_enabled() -> bool:
    """Whether Textract-based blur detection runs on each image.

    When enabled, detect_blur is called and results (is_blurry, analysis_failed,
    avg confidence, word count, llm_checked) are recorded to DDB. Does not reject
    documents unless enforce-blur-rejection is also enabled. Default: true (param
    absent means enabled so detection is on by default).
    """
    return _get_flag(FeatureFlags.ENABLE_BLUR_DETECTION, default=True)


def is_blur_rejection_enforced() -> bool:
    """Whether a blurry detection actually rejects the document.

    When false, blur detection still runs (if enabled) and records results, but
    does not set BLURRY_DOCUMENT_DETECTED status. Default: false.
    """
    return _get_flag(FeatureFlags.ENFORCE_BLUR_REJECTION, default=False)


def is_textract_identity_enabled() -> bool:
    """Whether Textract AnalyzeID is used for identity documents.

    When enabled, documents preclassified as identity_verification are routed to
    Textract AnalyzeID instead of BDA. Controlled via an SSM parameter so it can
    be toggled per-environment without redeploying.
    """
    return _get_flag(FeatureFlags.TEXTRACT_IDENTITY_ENABLED, default=False)


def is_missing_geo_included_with_missing_fields() -> bool:
    """Whether fields without geometry and below confidence threshold are treated as missing.

    When enabled, non-empty fields lacking a bounding box (geometry) with confidence
    below the configured threshold are excluded from the non-empty count, excluded
    from average confidence, and treated as absent for extraction rule evaluation
    (triggering response code 101 if required). Default: true.
    """
    return _get_flag(FeatureFlags.INCLUDE_MISSING_GEO_WITH_MISSING_FIELDS, default=True)


def is_preclassification_routing_enabled() -> bool:
    """Whether documents are routed to a category-specific BDA project ARN.

    When enabled, documents with a matched preclassification category are sent to
    the corresponding per-category BDA project instead of the default "all" project.
    Default: false.
    """
    return _get_flag(FeatureFlags.PRECLASSIFICATION_BASED_ROUTING, default=False)


def is_skip_bda_if_unclassified() -> bool:
    """Whether BDA is skipped when preclassification returns "other_document".

    When enabled, documents that preclassify as other_document (no category match,
    unsupported type, or classification failure) are not sent to BDA. Despite the
    flag name, the live trigger is the other_document signal from preclassify, not
    blueprint matching. Default: false (always invoke BDA).
    """
    return _get_flag(FeatureFlags.SKIP_BDA_IF_UNCLASSIFIED, default=False)


def is_preclassification_blueprint_matching_enabled() -> bool:
    """Whether blueprint matching runs after preclassification.

    When enabled, documents are matched against available BDA blueprints after
    preclassification. Results are stored for observability only - no routing
    decisions are made from them. Default: true.
    """
    return _get_flag(FeatureFlags.ENABLE_PRECLASSIFICATION_BLUEPRINT_MATCHING, default=True)


def is_multipage_document_flagging_enabled() -> bool:
    """Whether multipage documents containing multiple distinct document types are flagged.

    When enabled, a multipage PDF where preclassification identifies more than one
    distinct document type across pages is rejected with response code 401. Default: true.
    """
    return _get_flag(FeatureFlags.FLAG_MULTIPLE_DOCUMENTS_IN_MULTIPAGE, default=True)

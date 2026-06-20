import os
from typing import Any

from fastapi import (
    Depends,
    FastAPI,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRoute
from mangum import Mangum

from documentai_api.app_admin_documents import router as admin_documents_router
from documentai_api.app_api_keys import router as api_keys_router
from documentai_api.app_audit_log import router as audit_log_router
from documentai_api.app_auth_events import router as auth_events_router

# Routers
from documentai_api.app_batch import router as batch_router
from documentai_api.app_blueprint_test import router as blueprint_test_router
from documentai_api.app_build import router as build_router
from documentai_api.app_demo import router as demo_router
from documentai_api.app_dictionary import router as dictionary_router
from documentai_api.app_document_categories import router as document_categories_router
from documentai_api.app_documents import router as documents_router
from documentai_api.app_extraction_rules import router as extraction_rules_router
from documentai_api.app_me import router as me_router
from documentai_api.app_metrics import router as metrics_router
from documentai_api.app_presigned import router as presigned_router
from documentai_api.app_tenants import router as tenants_router
from documentai_api.app_users import router as users_router
from documentai_api.config.constants import (
    API_VERSION,
    APIConfig,
    FileValidation,
)
from documentai_api.config.env import get_app_env_config
from documentai_api.logging import get_logger
from documentai_api.models.api_responses import (
    ConfigResponse,
    HealthResponse,
)
from documentai_api.utils.auth import verify_api_key

logger = get_logger(__name__)

app = FastAPI(
    title=APIConfig.TITLE,
    description=APIConfig.DESCRIPTION,
    version=APIConfig.VERSION,
)
app.include_router(documents_router)
app.include_router(batch_router)
app.include_router(build_router)
app.include_router(presigned_router)
app.include_router(dictionary_router)
app.include_router(extraction_rules_router)
app.include_router(api_keys_router)
app.include_router(tenants_router)
app.include_router(users_router)
app.include_router(audit_log_router)
app.include_router(admin_documents_router)
app.include_router(document_categories_router)
app.include_router(blueprint_test_router)
app.include_router(demo_router)
app.include_router(me_router)
app.include_router(metrics_router)
app.include_router(auth_events_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "PUT", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "x-api-key", "API-Key", "Authorization", "X-Trace-ID"],
    expose_headers=["X-Trace-ID"],
)

# Lambda entrypoint for the API container. Configure the API Lambda function with
# ImageConfig.Command = ["documentai_api.app.handler"].
handler = Mangum(app, lifespan="off")

# Configure logging when running in Lambda. main() bypassed, so LoggingContext is
# never entered the normal way; without it, INFO logs are silently dropped.
# AWS_LAMBDA_FUNCTION_NAME is set automatically by the Lambda runtime.
if os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
    from documentai_api.logging.config import LoggingContext

    LoggingContext("documentai_api")


def _require_auth_in_hosted_envs() -> None:
    """Refuse to start with per-key auth disabled in a hosted environment.

    API_AUTH_ENABLED defaults to false for local dev, where the API falls back to a
    single shared key. Booting a hosted deployment that way would put the entire API
    behind one shared secret, so fail closed instead. Mangum runs with lifespan="off",
    so a FastAPI startup event would not fire in Lambda; this runs at import time.
    """
    config = get_app_env_config()
    if not config.api_auth_enabled and config.is_hosted_env():
        raise RuntimeError(
            f"API_AUTH_ENABLED is false in a hosted environment (ENVIRONMENT={config.environment!r}). "
            "Per-key DynamoDB auth is required for deployed environments; set API_AUTH_ENABLED=true."
        )


_require_auth_in_hosted_envs()

CONFIG_EXCLUDED_ROUTES = {"/", "/health", "/config", "/openapi.json", "/docs", "/redoc"}

_cached_endpoints: dict[str, str] | None = None


def discover_endpoints(app: FastAPI) -> dict[str, str]:
    """Build a sorted map of operation name → path for all non-excluded routes. Cached after first call."""
    global _cached_endpoints
    if _cached_endpoints is not None:
        return dict(_cached_endpoints)
    endpoints = {}
    for route in app.routes:
        if isinstance(route, APIRoute) and route.name and route.path not in CONFIG_EXCLUDED_ROUTES:
            endpoints[route.name] = route.path
    _cached_endpoints = dict(sorted(endpoints.items()))
    return dict(_cached_endpoints)


# =============================================================================
# Public endpoints (no auth required)
# =============================================================================


@app.get("/")
def root() -> dict[str, Any]:
    return {"message": APIConfig.TITLE, "status": "healthy"}


@app.get("/health")
async def health() -> HealthResponse:
    return HealthResponse(message="healthy")


@app.get("/config", dependencies=[Depends(verify_api_key)])
def get_config() -> ConfigResponse:
    endpoints = discover_endpoints(app)

    app_config = get_app_env_config()
    return ConfigResponse(
        api_url=app_config.api_base_url,
        version=API_VERSION,
        image_tag=app_config.image_tag,
        environment=app_config.environment,
        endpoints=endpoints,
        supported_file_types=list(FileValidation.SUPPORTED_CONTENT_TYPES),
    )

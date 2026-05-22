import os
from typing import Any

from fastapi import (
    Depends,
    FastAPI,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRoute
from mangum import Mangum

# Routers
from documentai_api.app_batch import router as batch_router
from documentai_api.app_build import router as build_router
from documentai_api.app_dictionary import router as dictionary_router
from documentai_api.app_documents import router as documents_router
from documentai_api.app_extraction_rules import router as extraction_rules_router
from documentai_api.app_presigned import router as presigned_router
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "PUT", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "x-api-key", "X-Trace-ID"],
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
    if "postUpload" in endpoints:
        endpoints["postUploadSynchronous"] = f"{endpoints['postUpload']}?wait=true"

    app_config = get_app_env_config()
    return ConfigResponse(
        api_url=app_config.api_base_url,
        version=API_VERSION,
        image_tag=app_config.image_tag,
        environment=app_config.environment,
        endpoints=endpoints,
        supported_file_types=list(FileValidation.SUPPORTED_CONTENT_TYPES),
    )

"""OpenTelemetry initialisation.

Call ``setup()`` once at process startup before the FastAPI app is created.
When OTEL_SDK_DISABLED=true (the default) this is a no-op so nothing changes
for existing workflows.
"""

from __future__ import annotations

import logging

from pydantic_settings import SettingsConfigDict

from documentai_api.config.env import PydanticBaseEnvConfig

logger = logging.getLogger(__name__)


class OtelConfig(PydanticBaseEnvConfig):
    model_config = SettingsConfigDict(env_prefix="otel_")

    sdk_disabled: bool = True
    service_name: str = "documentai-api"
    # OTLP endpoint, e.g. "http://localhost:4317" or an ADOT collector URL
    exporter_otlp_endpoint: str = "http://localhost:4317"


def setup() -> None:
    """Initialise the OTEL TracerProvider and instrument FastAPI.

    Safe to call unconditionally — exits immediately when OTEL_SDK_DISABLED=true.
    """
    config = OtelConfig()
    if config.sdk_disabled:
        return

    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.sdk.resources import SERVICE_NAME, Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    resource = Resource.create({SERVICE_NAME: config.service_name})
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(
        BatchSpanProcessor(OTLPSpanExporter(endpoint=config.exporter_otlp_endpoint))
    )
    trace.set_tracer_provider(provider)

    FastAPIInstrumentor().instrument()

    from opentelemetry.instrumentation.boto3sqs import Boto3SQSInstrumentor

    Boto3SQSInstrumentor().instrument()

    logger.info(
        "OpenTelemetry enabled: service=%s endpoint=%s",
        config.service_name,
        config.exporter_otlp_endpoint,
    )

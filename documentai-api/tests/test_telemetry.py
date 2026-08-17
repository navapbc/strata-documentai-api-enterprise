from unittest.mock import patch

import pytest
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider


@pytest.fixture(autouse=True)
def reset_tracer_provider():
    """Reset the process-global TracerProvider before each test.

    TracerProvider is set-once on the global proxy; without this reset the
    second test inherits whatever the first test installed, making results
    order-dependent.
    """
    yield
    proxy = trace.get_tracer_provider()
    if hasattr(proxy, "_lock"):
        with proxy._lock:
            proxy._real_tracer_provider = None
    else:
        trace._TRACER_PROVIDER = None  # type: ignore[attr-defined]
        trace._TRACER_PROVIDER_INITIALIZED = False  # type: ignore[attr-defined]


def test_setup_is_noop_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    """setup() must not install a TracerProvider when OTEL_SDK_DISABLED=true."""
    monkeypatch.setenv("OTEL_SDK_DISABLED", "true")

    from documentai_api.telemetry import setup

    setup()

    assert type(trace.get_tracer_provider()).__name__ in (
        "ProxyTracerProvider",
        "NoOpTracerProvider",
    )


def test_setup_installs_provider_when_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    """setup() must install a real TracerProvider when OTEL_SDK_DISABLED=false."""
    monkeypatch.setenv("OTEL_SDK_DISABLED", "false")
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")

    with (
        patch("opentelemetry.instrumentation.fastapi.FastAPIInstrumentor.instrument"),
        patch("opentelemetry.exporter.otlp.proto.grpc.trace_exporter.OTLPSpanExporter"),
    ):
        from documentai_api.telemetry import setup

        setup()

    assert isinstance(trace.get_tracer_provider(), TracerProvider)

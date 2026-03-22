"""
otel.py — OpenTelemetry instrumentation for ScopeSentinel API (Epic 5.5.5)

Import this at the very top of main.py BEFORE any other imports to ensure
all instrumented libraries are captured correctly.

Usage in main.py:
    from otel import configure_otel
    configure_otel()

Exports traces to Grafana Tempo via OTLP gRPC.
"""

import os

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor


def configure_otel(app=None, service_name: str = "scopesentinel-api") -> None:
    """
    Configure OpenTelemetry tracing for the service.

    Exports to OTLP endpoint (Grafana Tempo) via grpc.
    Set OTEL_EXPORTER_OTLP_ENDPOINT env var (default: http://tempo:4317)
    """
    if os.environ.get("OTEL_DISABLED", "false").lower() == "true":
        return

    otlp_endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "http://tempo:4317")

    resource = Resource.create({
        "service.name": service_name,
        "service.version": "1.0.0",
        "deployment.environment": os.environ.get("ENV", "development"),
    })

    provider = TracerProvider(resource=resource)
    provider.add_span_processor(
        BatchSpanProcessor(OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True))
    )
    trace.set_tracer_provider(provider)

    # Auto-instrument SQLAlchemy and HTTPX
    SQLAlchemyInstrumentor().instrument()
    HTTPXClientInstrumentor().instrument()

    # Auto-instrument FastAPI if app provided
    if app is not None:
        FastAPIInstrumentor.instrument_app(app)

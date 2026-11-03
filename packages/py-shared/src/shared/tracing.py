from __future__ import annotations

from opentelemetry import trace


def configure_tracing(service_name: str = "fintech-ai-platform") -> object:
    """Initialize OpenTelemetry tracing for platform services.

    This is intentionally a stub so the platform can later add exporter wiring without
    changing call sites.
    """
    tracer = trace.get_tracer(service_name)
    return tracer

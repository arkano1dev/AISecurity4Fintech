from __future__ import annotations

import logging
from typing import Any


def configure_logging(level: str = "INFO") -> None:
    """Configure structured application logging.

    This ensures logs are emitted in a format that supports security-forensic review and
    correlation across services.
    """
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


def log_event(event: str, **fields: Any) -> None:
    """Emit a simple structured event.

    This is a lightweight helper for consistent event logging and is covered by the
    platform's operational requirements.
    """
    payload = ", ".join(f"{key}={value}" for key, value in fields.items())
    logging.info("%s %s", event, payload)

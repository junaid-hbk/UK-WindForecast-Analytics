"""Structured JSON logging.

Every log record is emitted as a single JSON object so runs can be inspected and
grepped without a log shipper. ``configure_logging`` is idempotent.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any

_CONFIGURED = False

_RESERVED = {
    "args",
    "asctime",
    "created",
    "exc_info",
    "exc_text",
    "filename",
    "funcName",
    "levelname",
    "levelno",
    "lineno",
    "module",
    "msecs",
    "message",
    "msg",
    "name",
    "pathname",
    "process",
    "processName",
    "relativeCreated",
    "stack_info",
    "thread",
    "threadName",
    "taskName",
}


class JsonFormatter(logging.Formatter):
    """Render log records as one-line JSON."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key not in _RESERVED and not key.startswith("_"):
                payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str, ensure_ascii=False)


def configure_logging(level: str = "INFO") -> None:
    """Install the JSON handler on the root logger exactly once."""
    global _CONFIGURED
    root = logging.getLogger()
    if _CONFIGURED:
        root.setLevel(level.upper())
        return

    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(JsonFormatter())
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level.upper())

    # HTTP client internals are noisy at DEBUG; keep them at WARNING.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """Return a module logger."""
    return logging.getLogger(name)

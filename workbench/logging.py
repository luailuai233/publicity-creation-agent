from __future__ import annotations

import json
import logging
import re
from typing import Any


SENSITIVE_KEYS = {"authorization", "api_key", "prompt", "messages", "reference_text", "raw_text", "upload_text", "parsed_text", "content"}
PHONE = re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)")
SECRET = re.compile(r"(?i)(?:bearer\s+|token\s*=\s*|api[_-]?key\s*=\s*)[^\s,;]+|sk-[A-Za-z0-9_-]+")


def _redact_text(value: str) -> str:
    return SECRET.sub("[REDACTED]", PHONE.sub("[REDACTED]", value))


def sanitize_event(value: Any, key: str = "") -> Any:
    if key.lower() in SENSITIVE_KEYS:
        return "[REDACTED]"
    if isinstance(value, dict):
        return {str(item_key): sanitize_event(item_value, str(item_key)) for item_key, item_value in value.items()}
    if isinstance(value, (list, tuple)):
        return [sanitize_event(item) for item in value]
    if isinstance(value, str):
        return _redact_text(value)
    return value


def log_event(logger: logging.Logger, event: str, **fields: Any) -> None:
    logger.info(json.dumps(sanitize_event({"event": event, **fields}), ensure_ascii=False, default=str, sort_keys=True))

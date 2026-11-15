import hashlib
import json
from enum import Enum
from typing import Any

from pydantic import BaseModel


def _json_value(value: Any):
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, Enum):
        return value.value
    raise TypeError(f"Unsupported fingerprint value: {type(value).__name__}")


def fingerprint_for(tool_name: str, payload: Any) -> str:
    canonical = json.dumps(
        {"tool": tool_name, "payload": payload},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=_json_value,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

from typing import Generic, List, Optional, TypeVar

from pydantic import BaseModel


T = TypeVar("T")


class AIEnvelope(BaseModel, Generic[T]):
    schema_version: str = "1.0"
    result: Optional[T]
    warnings: List[str] = []
    source_ids: List[str] = []
    fact_ids: List[str] = []
    provider: str = "mock-structured-v1"
    duration_ms: int = 0
    token_count: int = 0
    retries: int = 0
    is_demo: bool = True
    status: str = "DONE"

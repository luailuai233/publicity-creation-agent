from typing import List

from pydantic import BaseModel, Field


class StrategyResult(BaseModel):
    name: str
    angle: str
    opening: str
    structure: str
    fact_ids: List[str]
    method_summary: str
    risk: str


class StrategySetResult(BaseModel):
    strategies: List[StrategyResult]
    recommended_index: int = Field(default=0, ge=0, le=2)

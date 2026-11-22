from typing import List

from pydantic import BaseModel, ConfigDict, Field


class StrategyResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    protagonist: str = "未指定"
    angle: str
    opening: str
    structure: str
    fact_ids: List[str]
    method_summary: str
    risk: str


class StrategySetResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    strategies: List[StrategyResult] = Field(min_length=3, max_length=3)
    recommended_index: int = Field(default=0, ge=0, le=2)

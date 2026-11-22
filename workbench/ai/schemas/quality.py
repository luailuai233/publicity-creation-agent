from typing import List, Literal

from pydantic import BaseModel, ConfigDict


class QualitySuggestion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["MISSING_SOURCE", "FACT_CONFLICT", "SIMILAR_EXPRESSION", "PRIVACY_RISK", "TONE_RISK"]
    severity: Literal["LOW", "MEDIUM", "HIGH"]
    block_id: str
    message: str
    auto_fixable: bool = False


class QualityResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    issues: List[QualitySuggestion]

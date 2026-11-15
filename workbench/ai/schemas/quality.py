from typing import List

from pydantic import BaseModel


class QualitySuggestion(BaseModel):
    type: str
    severity: str
    block_id: str
    message: str
    auto_fixable: bool = False


class QualityResult(BaseModel):
    issues: List[QualitySuggestion]

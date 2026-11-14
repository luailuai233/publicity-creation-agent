from typing import List

from pydantic import BaseModel, Field


class ReferenceAnalysisResult(BaseModel):
    hook: str = Field(min_length=2)
    emotion: str = Field(min_length=2)
    structure: str = Field(min_length=2)
    image_role: str = Field(min_length=2)
    transferable: List[str] = Field(min_length=1)
    avoid: List[str] = Field(min_length=1)

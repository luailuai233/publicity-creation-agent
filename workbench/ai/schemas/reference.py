from typing import List

from pydantic import BaseModel, ConfigDict, Field


class ReferenceAnalysisResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    hook: str = Field(min_length=2)
    emotion: str = Field(min_length=2)
    structure: str = Field(min_length=2)
    image_role: str = Field(min_length=2)
    transferable: List[str] = Field(min_length=1)
    avoid: List[str] = Field(min_length=1)

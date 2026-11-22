from pydantic import BaseModel, ConfigDict, Field


class MaterialUnderstandingResult(BaseModel):
    category: str
    summary: str
    parsed_text: str


class ImageUnderstandingResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    description: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    confidence: float = Field(ge=0, le=1)
    identity_inferred: bool = False

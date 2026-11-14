from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class FactPatch(BaseModel):
    content: Optional[str] = Field(default=None, min_length=1)
    status: Optional[str] = None


class ConflictResolution(BaseModel):
    fact_id: str


class ConfirmedFact(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    type: str
    content: str
    status: str
    confidence: float

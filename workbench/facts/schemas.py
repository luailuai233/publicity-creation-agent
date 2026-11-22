from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class FactPatch(BaseModel):
    content: Optional[str] = Field(default=None, min_length=1)
    status: Optional[str] = None


class ConflictResolution(BaseModel):
    fact_id: str


class ConflictSourceEvidence(BaseModel):
    label: str
    excerpt: str


class ConflictFactOption(BaseModel):
    id: str
    content: str
    sources: list[ConflictSourceEvidence] = Field(default_factory=list)


class ConflictGroupDetail(BaseModel):
    id: str
    fact_type: str
    options: list[ConflictFactOption] = Field(default_factory=list)


class ConfirmedFact(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    type: str
    content: str
    status: str
    confidence: float

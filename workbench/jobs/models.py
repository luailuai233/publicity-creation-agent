from typing import Optional

from pydantic import BaseModel, ConfigDict


class JobCreate(BaseModel):
    project_id: str
    material_id: Optional[str] = None
    type: str


class JobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    material_id: Optional[str]
    type: str
    status: str
    progress: int
    stage: str
    error_code: Optional[str]
    retryable: bool

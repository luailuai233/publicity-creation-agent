from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    audience: str = Field(default="校园活动关注者", max_length=160)
    tone: str = Field(default="真实、温暖、克制", max_length=160)
    length_min: int = Field(default=1200, ge=200, le=10000)
    length_max: int = Field(default=1600, ge=200, le=10000)
    is_demo: bool = False


class ProjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    audience: str
    tone: str
    length_min: int
    length_max: int
    status: str
    is_demo: bool

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    audience: str = Field(default="校园活动关注者", max_length=160)
    tone: str = Field(default="真实、温暖、克制", max_length=160)
    length_min: int = Field(default=1200, ge=200, le=10000)
    length_max: int = Field(default=1600, ge=200, le=10000)
    is_demo: bool = False


class ProjectPatch(BaseModel):
    goal: Optional[str] = Field(default=None, max_length=2000)
    audience: Optional[str] = Field(default=None, max_length=160)
    tone: Optional[str] = Field(default=None, max_length=160)
    length_min: Optional[int] = Field(default=None, ge=200, le=10000)
    length_max: Optional[int] = Field(default=None, ge=200, le=10000)

    @field_validator("goal", "audience", "tone")
    @classmethod
    def strip_non_empty_text(cls, value: Optional[str], info):
        if value is None:
            return value
        value = value.strip()
        if info.field_name in {"audience", "tone"} and not value:
            raise ValueError("不能为空")
        return value

    @model_validator(mode="after")
    def validate_supplied_length_range(self):
        if self.length_min is not None and self.length_max is not None and self.length_min > self.length_max:
            raise ValueError("最少字数不能大于最多字数")
        return self


class ProjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    goal: str
    audience: str
    tone: str
    length_min: int
    length_max: int
    status: str
    revision: int
    is_demo: bool

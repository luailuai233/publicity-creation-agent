from typing import Optional

from pydantic import BaseModel, Field


class DraftPatch(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1)
    outline: Optional[list[str]] = None
    content: Optional[str] = None

from typing import Optional

from pydantic import BaseModel, Field


class DraftPatch(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1)
    outline: Optional[list[str]] = None
    content: Optional[str] = None
    locked_fact_ids: Optional[list[str]] = None
    locked_block_ids: Optional[list[str]] = None


class ParagraphRewriteRequest(BaseModel):
    block_id: str = Field(min_length=1, max_length=120)
    goal: str = Field(min_length=1, max_length=500)
    expected_revision: int = Field(ge=0)

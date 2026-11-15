from typing import List

from pydantic import BaseModel, Field


class OutlineResult(BaseModel):
    titles: List[str]
    outline: List[str]
    recommended_title_index: int = Field(default=0, ge=0)


class DraftResult(BaseModel):
    content: str
    cited_fact_ids: List[str]

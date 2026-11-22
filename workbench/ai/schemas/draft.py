from typing import List

from pydantic import BaseModel, ConfigDict, Field


class OutlineResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    titles: List[str] = Field(min_length=1)
    outline: List[str] = Field(min_length=1)
    recommended_title_index: int = Field(default=0, ge=0)


class DraftResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content: str
    cited_fact_ids: List[str]


class ParagraphRewriteResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content: str = Field(min_length=1)
    cited_fact_ids: List[str]

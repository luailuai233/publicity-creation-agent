from typing import List

from pydantic import BaseModel


class OutlineResult(BaseModel):
    titles: List[str]
    outline: List[str]


class DraftResult(BaseModel):
    content: str
    cited_fact_ids: List[str]

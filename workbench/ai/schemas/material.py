from pydantic import BaseModel


class MaterialUnderstandingResult(BaseModel):
    category: str
    summary: str
    parsed_text: str

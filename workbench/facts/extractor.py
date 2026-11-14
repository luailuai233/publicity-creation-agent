import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from workbench.db.models import FactCard, FactSource, Material, SourceChunk


PATTERNS = [
    ("TIME", re.compile(r"(?:20\d{2}年)?\d{1,2}月\d{1,2}日(?:[^。\n]{0,12}\d{1,2}[:：]\d{2})?")),
    ("LOCATION", re.compile(r"(?:在|地点[:：])([^，。；\n]{2,24})")),
    ("NUMBER", re.compile(r"\d+(?:\.\d+)?(?:人|名|组|场|次|份|元)")),
    ("QUOTE", re.compile(r"[“\"]([^”\"]{4,120})[”\"]")),
]


def extract_fact_candidates(session: Session, project_id: str) -> list[FactCard]:
    chunks = session.scalars(select(SourceChunk).join(Material).where(Material.project_id == project_id)).all()
    created = []
    for chunk in chunks:
        for fact_type, pattern in PATTERNS:
            for match in pattern.finditer(chunk.content):
                content = match.group(1) if match.lastindex else match.group(0)
                fact = FactCard(project_id=project_id, type=fact_type, content=content.strip(), status="PENDING", confidence=0.72)
                session.add(fact)
                session.flush()
                session.add(FactSource(fact_id=fact.id, source_chunk_id=chunk.id))
                created.append(fact)
    session.commit()
    return created

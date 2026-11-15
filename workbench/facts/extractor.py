import re
import uuid

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
    for fact_type in ("TIME", "NUMBER"):
        same_type = [fact for fact in created if fact.type == fact_type]
        if len({fact.content for fact in same_type}) > 1:
            group_id = f"{fact_type.lower()}-{uuid.uuid4()}"
            for fact in same_type:
                fact.status = "CONFLICT"
                fact.conflict_group = group_id
    session.commit()
    return created

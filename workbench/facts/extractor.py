import re
import hashlib

from sqlalchemy import select
from sqlalchemy.orm import Session

from workbench.db.models import FactCard, FactSource, Material, SourceChunk
from workbench.materials.categories import infer_material_category


PATTERNS = [
    ("TIME", re.compile(r"(?:20\d{2}年)?\d{1,2}月\d{1,2}日(?:[^。\n]{0,12}\d{1,2}[:：]\d{2})?")),
    ("LOCATION", re.compile(r"(?:在|地点[:：])([^，。；\n]{2,24})")),
    ("NUMBER", re.compile(r"\d+(?:\.\d+)?\s*(?:人|名|组|场|次|份|元)")),
    ("QUOTE", re.compile(r"[“\"]([^”\"]{4,120})[”\"]")),
]


def normalize_fact_value(value: str) -> str:
    return re.sub(r"\s+", "", value).strip("，。；：,. ")


def _can_extract_quote(category: str, text: str) -> bool:
    if category == "SPEECH":
        return True
    if category != "INTERVIEW":
        return False
    return bool(re.search(r"受访|表示|提到|认为|回忆|介绍|强调|坦言|指出|回答|告诉|说道|说[:：]", text))


def extract_fact_candidates(session: Session, project_id: str) -> list[FactCard]:
    chunks = session.scalars(select(SourceChunk).join(Material).where(Material.project_id == project_id)).all()
    created = []
    for chunk in chunks:
        material = chunk.material
        material.category = infer_material_category(material.file_name, material.category)
        for fact_type, pattern in PATTERNS:
            if fact_type == "QUOTE" and not _can_extract_quote(material.category, chunk.content):
                continue
            for match in pattern.finditer(chunk.content):
                content = match.group(1) if match.lastindex else match.group(0)
                normalized = normalize_fact_value(content)
                fingerprint = hashlib.sha256(f"{project_id}:{fact_type}:{normalized}".encode("utf-8")).hexdigest()
                fact = session.scalar(
                    select(FactCard).where(
                        FactCard.project_id == project_id,
                        FactCard.type == fact_type,
                        FactCard.normalized_value == normalized,
                    )
                )
                if fact is None:
                    fact = FactCard(
                        project_id=project_id,
                        type=fact_type,
                        content=content.strip(),
                        normalized_value=normalized,
                        fingerprint=fingerprint,
                        status="PENDING",
                        confidence=0.72,
                    )
                    session.add(fact)
                    session.flush()
                    created.append(fact)
                if session.get(FactSource, (fact.id, chunk.id)) is None:
                    session.add(FactSource(fact_id=fact.id, source_chunk_id=chunk.id))
    for fact_type in ("TIME", "NUMBER"):
        same_type = list(session.scalars(select(FactCard).where(FactCard.project_id == project_id, FactCard.type == fact_type)).all())
        normalized_values = sorted({fact.normalized_value or normalize_fact_value(fact.content) for fact in same_type})
        if len(normalized_values) > 1:
            digest = hashlib.sha256(f"{project_id}:{fact_type}:{'|'.join(normalized_values)}".encode("utf-8")).hexdigest()[:12]
            group_id = f"{fact_type.lower()}-{digest}"
            for fact in same_type:
                fact.status = "CONFLICT"
                fact.conflict_group = group_id
    session.commit()
    return created

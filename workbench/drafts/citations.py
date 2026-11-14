from sqlalchemy import func, select
from sqlalchemy.orm import Session

from workbench.db.models import FactSource


def fact_has_source(session: Session, fact_id: str) -> bool:
    return bool(session.scalar(select(func.count(FactSource.source_chunk_id)).where(FactSource.fact_id == fact_id)))

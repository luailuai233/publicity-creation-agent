from sqlalchemy import select
from sqlalchemy.orm import Session

from workbench.db.models import FactCard
from workbench.facts.schemas import ConfirmedFact


def get_eligible_facts(session: Session, project_id: str) -> list[ConfirmedFact]:
    facts = session.scalars(
        select(FactCard)
        .where(FactCard.project_id == project_id, FactCard.status == "CONFIRMED", FactCard.conflict_group.is_(None))
        .order_by(FactCard.created_at, FactCard.id)
    ).all()
    return [ConfirmedFact.model_validate(fact) for fact in facts]

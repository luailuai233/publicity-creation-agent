from pydantic import BaseModel
from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from workbench.api.responses import api_error, api_response
from workbench.db.models import Strategy
from workbench.strategies.service import StrategyNeedsReview, generate_strategies, select_strategy
from workbench.web.dependencies import get_session


router = APIRouter(tags=["strategies"])


class StrategySettings(BaseModel):
    tone: str = "真实、温暖、克制"
    length: str = "1200-1600"
    focus_fact_ids: list[str] = []


def serialize(item: Strategy) -> dict:
    return {
        "id": item.id, "project_id": item.project_id, "name": item.name, "angle": item.angle,
        "opening": item.opening, "structure": item.structure, "fact_ids": item.fact_ids,
        "method_summary": item.method_summary, "risk": item.risk, "selected": item.selected,
        "settings": item.settings, "is_demo": item.is_demo,
    }


@router.get("/api/projects/{project_id}/strategies")
def index(project_id: str, session: Session = Depends(get_session)):
    items = session.scalars(select(Strategy).where(Strategy.project_id == project_id)).all()
    return api_response([serialize(item) for item in items])


@router.post("/api/projects/{project_id}/strategies/generate")
def generate(project_id: str, request: Request, session: Session = Depends(get_session)):
    try:
        return api_response([serialize(item) for item in generate_strategies(session, request.app.state.ai_provider, project_id)], status_code=201)
    except StrategyNeedsReview as error:
        return api_error("STRATEGY_NEEDS_REVIEW", str(error), 409)


@router.patch("/api/strategies/{strategy_id}/select")
def select(strategy_id: str, settings: StrategySettings, session: Session = Depends(get_session)):
    try:
        return api_response(serialize(select_strategy(session, strategy_id, settings.model_dump())))
    except LookupError:
        return api_error("STRATEGY_NOT_FOUND", "没有找到这个创作策略", 404)

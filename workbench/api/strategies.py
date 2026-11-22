from pydantic import BaseModel
from fastapi import APIRouter, BackgroundTasks, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from workbench.ai.errors import AIProviderError
from workbench.api.responses import api_error, api_response
from workbench.db.models import AgentRun, Strategy
from workbench.strategies.service import StrategyNeedsReview, generate_strategies, select_strategy
from workbench.web.dependencies import get_session


router = APIRouter(tags=["strategies"])


class StrategySettings(BaseModel):
    tone: str = "真实、温暖、克制"
    length: str = "1200-1600"
    focus_fact_ids: list[str] = []


def serialize(item: Strategy) -> dict:
    return {
        "id": item.id, "project_id": item.project_id, "name": item.name, "protagonist": item.protagonist, "angle": item.angle,
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
    except AIProviderError as error:
        messages = {
            "AI_AUTHENTICATION_ERROR": "模型服务认证失败，请检查 API Key",
            "AI_RATE_LIMIT_ERROR": "模型服务当前限流，请稍后重试",
            "AI_NETWORK_ERROR": "暂时无法连接模型服务，请稍后重试",
            "AI_REQUEST_ERROR": "模型服务拒绝了策略生成请求，请检查模型名称或接口兼容配置",
            "AI_RESPONSE_SCHEMA_ERROR": "模型返回的策略格式不符合要求，请重试",
            "AI_CONTENT_ERROR": "模型无法处理当前策略输入，请调整后重试",
        }
        return api_error(error.code, messages.get(error.code, "模型生成策略失败，请稍后重试"), 502)


@router.patch("/api/strategies/{strategy_id}/select")
def choose_strategy(strategy_id: str, settings: StrategySettings, request: Request, background_tasks: BackgroundTasks, session: Session = Depends(get_session)):
    try:
        strategy = select_strategy(session, strategy_id, settings.model_dump())
        waiting_run = session.scalar(select(AgentRun).where(AgentRun.project_id == strategy.project_id, AgentRun.status == "WAITING_USER", AgentRun.waiting_reason == "STRATEGY_SELECTION").order_by(AgentRun.updated_at.desc()))
        if waiting_run is not None:
            waiting_run.status = "QUEUED"
            waiting_run.waiting_reason = None
            waiting_run.waiting_payload = None
            session.commit()
            background_tasks.add_task(request.app.state.agent_runner.run, waiting_run.id)
        return api_response(serialize(strategy))
    except LookupError:
        return api_error("STRATEGY_NOT_FOUND", "没有找到这个创作策略", 404)

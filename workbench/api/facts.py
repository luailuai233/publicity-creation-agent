from fastapi import APIRouter, BackgroundTasks, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from workbench.api.responses import api_error, api_response
from workbench.agent.interrupts import reconcile_resolved_conflict, replan_waiting_run
from workbench.db.models import FactCard, FactSource, Material, SourceChunk
from workbench.facts.extractor import extract_fact_candidates
from workbench.facts.schemas import ConflictResolution, FactPatch
from workbench.facts.service import FactNotFoundError, FactTransitionError, resolve_conflict, update_fact
from workbench.web.dependencies import get_session


router = APIRouter(tags=["facts"])


def serialize_fact(session: Session, fact: FactCard) -> dict:
    sources = session.execute(
        select(Material.file_name, SourceChunk.page, SourceChunk.paragraph, SourceChunk.content)
        .join(SourceChunk, SourceChunk.material_id == Material.id)
        .join(FactSource, FactSource.source_chunk_id == SourceChunk.id)
        .where(FactSource.fact_id == fact.id)
    ).all()
    return {
        "id": fact.id,
        "project_id": fact.project_id,
        "type": fact.type,
        "content": fact.content,
        "status": fact.status,
        "confidence": fact.confidence,
        "conflict_group": fact.conflict_group,
        "sources": [
            {"file_name": row.file_name, "page": row.page, "paragraph": row.paragraph, "content": row.content}
            for row in sources
        ],
    }


@router.get("/api/projects/{project_id}/facts")
def index(project_id: str, session: Session = Depends(get_session)):
    facts = session.scalars(select(FactCard).where(FactCard.project_id == project_id).order_by(FactCard.created_at)).all()
    return api_response([serialize_fact(session, fact) for fact in facts])


@router.post("/api/projects/{project_id}/facts/extract")
def extract(project_id: str, session: Session = Depends(get_session)):
    facts = extract_fact_candidates(session, project_id)
    return api_response([serialize_fact(session, fact) for fact in facts], status_code=201)


@router.patch("/api/facts/{fact_id}")
def update(
    fact_id: str,
    patch: FactPatch,
    request: Request,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
):
    try:
        fact = update_fact(session, fact_id, patch, commit=False)
        resumed_run = replan_waiting_run(session, fact.project_id)
        session.commit()
        session.refresh(fact)
        if resumed_run is not None:
            background_tasks.add_task(request.app.state.agent_runner.run, resumed_run.id)
        return api_response(serialize_fact(session, fact))
    except FactNotFoundError:
        session.rollback()
        return api_error("FACT_NOT_FOUND", "没有找到这个事实", 404)
    except FactTransitionError as error:
        session.rollback()
        return api_error("FACT_TRANSITION_BLOCKED", str(error), 409)


@router.post("/api/facts/conflicts/{group_id}/resolve")
def resolve(
    group_id: str,
    resolution: ConflictResolution,
    request: Request,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
):
    try:
        chosen = resolve_conflict(session, group_id, resolution, commit=False)
        resumed_run = reconcile_resolved_conflict(session, chosen.project_id, group_id)
        session.commit()
        session.refresh(chosen)
        if resumed_run is not None:
            background_tasks.add_task(request.app.state.agent_runner.run, resumed_run.id)
        return api_response(serialize_fact(session, chosen))
    except FactNotFoundError:
        session.rollback()
        return api_error("CONFLICT_NOT_FOUND", "没有找到这个冲突组", 404)
    except FactTransitionError as error:
        session.rollback()
        return api_error("CONFLICT_RESOLUTION_BLOCKED", str(error), 409)

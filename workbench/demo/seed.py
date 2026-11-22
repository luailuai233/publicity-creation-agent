from pathlib import Path
import json
import shutil

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from workbench.db.models import Draft, DraftCitation, EventLog, FactCard, FactSource, Job, Material, Project, QualityIssue, ReferenceCase, SourceChunk, Strategy, TimelineItem
from workbench.db.projects import create_project
from workbench.domain.project_schemas import ProjectCreate

SAMPLE_PATH = Path(__file__).resolve().parents[2] / "data" / "samples" / "demo.json"


def load_demo_dataset() -> dict:
    return json.loads(SAMPLE_PATH.read_text(encoding="utf-8"))


_DATASET = load_demo_dataset()
DEMO_PROJECT_NAME = _DATASET["project_name"]
MATERIALS = [(item["file_name"], item["category"], item["content"]) for item in _DATASET["materials"]]
REFERENCES = list(_DATASET["references"])


def ensure_demo_project(session: Session) -> Project:
    existing = session.scalar(select(Project).where(Project.is_demo.is_(True)))
    if existing is not None:
        return existing
    return create_project(session, ProjectCreate(name=DEMO_PROJECT_NAME, is_demo=True))


def reset_demo_project(session: Session, uploads_root: Path) -> Project:
    demo_ids = list(session.scalars(select(Project.id).where(Project.is_demo.is_(True))))
    if demo_ids:
        draft_ids = list(session.scalars(select(Draft.id).where(Draft.project_id.in_(demo_ids))))
        if draft_ids:
            session.execute(delete(QualityIssue).where(QualityIssue.draft_id.in_(draft_ids)))
            session.execute(delete(DraftCitation).where(DraftCitation.draft_id.in_(draft_ids)))
            session.execute(delete(Draft).where(Draft.id.in_(draft_ids)))
        for model in (Strategy, TimelineItem, Job, EventLog):
            session.execute(delete(model).where(model.project_id.in_(demo_ids)))
        session.execute(delete(Project).where(Project.id.in_(demo_ids)))
        session.commit()
        safe_root = uploads_root.resolve()
        for project_id in demo_ids:
            target = (safe_root / project_id).resolve()
            if target.parent == safe_root and target.exists():
                shutil.rmtree(target)

    project = create_project(session, ProjectCreate(name=DEMO_PROJECT_NAME, is_demo=True))
    chunks = []
    for file_name, category, content in MATERIALS:
        material = Material(project_id=project.id, file_name=file_name, mime_type="text/plain", category=category, parse_status="DONE", summary=content[:42], parsed_text=content, path="", size_bytes=len(content.encode("utf-8")))
        session.add(material); session.flush()
        chunk = SourceChunk(material_id=material.id, content=content, paragraph=1)
        session.add(chunk); session.flush(); chunks.append(chunk)
    facts = [
        FactCard(project_id=project.id, type="TIME", content="10 月 18 日 9:00 开始", status="PENDING", confidence=0.92, conflict_group="demo-start-time"),
        FactCard(project_id=project.id, type="TIME", content="10 月 18 日 9:30 开始", status="PENDING", confidence=0.80, conflict_group="demo-start-time"),
        FactCard(project_id=project.id, type="NUMBER", content="志愿者共 36 人", status="CONFIRMED", confidence=0.94),
        FactCard(project_id=project.id, type="QUOTE", content="孩子们把旧书认真分类并写下阅读寄语", status="CONFIRMED", confidence=0.91),
        FactCard(project_id=project.id, type="EVENT", content="现场设置旧书交换与公益义卖区域", status="CONFIRMED", confidence=0.90),
        FactCard(project_id=project.id, type="OPINION", content="现场氛围温暖", status="PENDING", confidence=0.55),
    ]
    for fact in facts:
        session.add(fact); session.flush()
    for fact, chunk in zip(facts, (chunks[0], chunks[2], chunks[0], chunks[1], chunks[2], chunks[1])):
        session.add(FactSource(fact_id=fact.id, source_chunk_id=chunk.id))
    for index, raw_text in enumerate(REFERENCES, start=1):
        session.add(ReferenceCase(project_id=project.id, input_type="TEXT", raw_text=raw_text, source_label=f"参考案例 {index}", status="PENDING", selected=True))
    session.commit(); session.refresh(project)
    return project

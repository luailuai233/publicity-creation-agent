from pathlib import Path
import shutil

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from workbench.db.models import Draft, DraftCitation, EventLog, FactCard, FactSource, Job, Material, Project, QualityIssue, ReferenceCase, SourceChunk, Strategy, TimelineItem
from workbench.db.projects import create_project
from workbench.domain.project_schemas import ProjectCreate

DEMO_PROJECT_NAME = "Demo · 秋日公益市集宣传"
MATERIALS = [
    ("event_flow.txt", "活动流程", "10 月 18 日 9:00，秋日公益市集在校园中央广场开始。志愿者共 36 人。"),
    ("interview.txt", "采访", "受访者说，最难忘的是孩子们把旧书认真分类，并写下新的阅读寄语。"),
    ("speech.txt", "主持稿", "主持稿记录活动于 10 月 18 日 9:30 开始，现场设置旧书交换与公益义卖区域。"),
]
REFERENCES = [
    "从一双沾着颜料的手写起，文章沿人物行动展开，最后回到社区共同参与的价值。",
    "先呈现义卖前后的反差，再追溯志愿者如何解决现场问题，结尾保持克制。",
    "以时间线串联三个现场切面，让图片承担证据与节奏，而不是代替事实判断。",
]


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
    ]
    for fact in facts:
        session.add(fact); session.flush()
    for fact, chunk in zip(facts, (chunks[0], chunks[2], chunks[0], chunks[1], chunks[2])):
        session.add(FactSource(fact_id=fact.id, source_chunk_id=chunk.id))
    for index, raw_text in enumerate(REFERENCES, start=1):
        session.add(ReferenceCase(project_id=project.id, input_type="TEXT", raw_text=raw_text, source_label=f"参考案例 {index}", status="PENDING", selected=True))
    session.commit(); session.refresh(project)
    return project

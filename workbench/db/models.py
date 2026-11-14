from __future__ import annotations

from datetime import datetime
import time
import uuid
from typing import Optional

from sqlalchemy import BigInteger, Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from workbench.db.base import Base
from workbench.domain.enums import FactStatus, JobStatus, MaterialCategory, ParseStatus, ProjectStatus


def new_id() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.utcnow()


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    audience: Mapped[str] = mapped_column(String(160), default="校园活动关注者")
    tone: Mapped[str] = mapped_column(String(160), default="真实、温暖、克制")
    length_min: Mapped[int] = mapped_column(Integer, default=1200)
    length_max: Mapped[int] = mapped_column(Integer, default=1600)
    status: Mapped[str] = mapped_column(String(32), default=ProjectStatus.MATERIALS.value)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    sort_order: Mapped[int] = mapped_column(BigInteger, default=time.time_ns, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    materials: Mapped[list[Material]] = relationship(back_populates="project", cascade="all, delete-orphan")
    references: Mapped[list[ReferenceCase]] = relationship(back_populates="project", cascade="all, delete-orphan")
    facts: Mapped[list[FactCard]] = relationship(back_populates="project", cascade="all, delete-orphan")


class Material(Base):
    __tablename__ = "materials"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    file_name: Mapped[str] = mapped_column(String(255))
    mime_type: Mapped[str] = mapped_column(String(120))
    category: Mapped[str] = mapped_column(String(32), default=MaterialCategory.OTHER.value)
    parse_status: Mapped[str] = mapped_column(String(32), default=ParseStatus.QUEUED.value)
    summary: Mapped[str] = mapped_column(Text, default="")
    parsed_text: Mapped[str] = mapped_column(Text, default="")
    path: Mapped[str] = mapped_column(String(600), default="")
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    project: Mapped[Project] = relationship(back_populates="materials")
    chunks: Mapped[list[SourceChunk]] = relationship(back_populates="material", cascade="all, delete-orphan")


class SourceChunk(Base):
    __tablename__ = "source_chunks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    material_id: Mapped[str] = mapped_column(ForeignKey("materials.id", ondelete="CASCADE"), index=True)
    content: Mapped[str] = mapped_column(Text)
    page: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    paragraph: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    bbox: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    material: Mapped[Material] = relationship(back_populates="chunks")
    fact_links: Mapped[list[FactSource]] = relationship(back_populates="source_chunk", cascade="all, delete-orphan")


class FactCard(Base):
    __tablename__ = "fact_cards"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    type: Mapped[str] = mapped_column(String(32))
    content: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default=FactStatus.PENDING.value)
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    conflict_group: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    project: Mapped[Project] = relationship(back_populates="facts")
    sources: Mapped[list[FactSource]] = relationship(back_populates="fact", cascade="all, delete-orphan")


class FactSource(Base):
    __tablename__ = "fact_sources"

    fact_id: Mapped[str] = mapped_column(ForeignKey("fact_cards.id", ondelete="CASCADE"), primary_key=True)
    source_chunk_id: Mapped[str] = mapped_column(ForeignKey("source_chunks.id", ondelete="CASCADE"), primary_key=True)

    fact: Mapped[FactCard] = relationship(back_populates="sources")
    source_chunk: Mapped[SourceChunk] = relationship(back_populates="fact_links")


class TimelineItem(Base):
    __tablename__ = "timeline_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    time_label: Mapped[str] = mapped_column(String(120))
    event: Mapped[str] = mapped_column(Text)
    fact_ids: Mapped[list] = mapped_column(JSON, default=list)


class ReferenceCase(Base):
    __tablename__ = "reference_cases"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    input_type: Mapped[str] = mapped_column(String(32))
    raw_text: Mapped[str] = mapped_column(Text, default="")
    source_label: Mapped[str] = mapped_column(String(255), default="")
    status: Mapped[str] = mapped_column(String(32), default="PENDING")
    selected: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    project: Mapped[Project] = relationship(back_populates="references")
    analysis: Mapped[Optional[ReferenceAnalysis]] = relationship(back_populates="reference", cascade="all, delete-orphan", uselist=False)


class ReferenceAnalysis(Base):
    __tablename__ = "reference_analyses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    reference_id: Mapped[str] = mapped_column(ForeignKey("reference_cases.id", ondelete="CASCADE"), unique=True)
    hook: Mapped[str] = mapped_column(Text, default="")
    emotion: Mapped[str] = mapped_column(Text, default="")
    structure: Mapped[str] = mapped_column(Text, default="")
    image_role: Mapped[str] = mapped_column(Text, default="")
    transferable: Mapped[list] = mapped_column(JSON, default=list)
    avoid: Mapped[list] = mapped_column(JSON, default=list)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=True)

    reference: Mapped[ReferenceCase] = relationship(back_populates="analysis")


class Strategy(Base):
    __tablename__ = "strategies"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    angle: Mapped[str] = mapped_column(Text)
    opening: Mapped[str] = mapped_column(Text)
    structure: Mapped[str] = mapped_column(Text)
    fact_ids: Mapped[list] = mapped_column(JSON, default=list)
    method_summary: Mapped[str] = mapped_column(Text, default="")
    risk: Mapped[str] = mapped_column(Text, default="")
    selected: Mapped[bool] = mapped_column(Boolean, default=False)
    settings: Mapped[dict] = mapped_column(JSON, default=dict)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=True)


class Draft(Base):
    __tablename__ = "drafts"
    __table_args__ = (UniqueConstraint("project_id", "version", name="uq_draft_project_version"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    strategy_id: Mapped[str] = mapped_column(ForeignKey("strategies.id", ondelete="RESTRICT"))
    title: Mapped[str] = mapped_column(String(300), default="")
    outline: Mapped[list] = mapped_column(JSON, default=list)
    content: Mapped[str] = mapped_column(Text, default="")
    version: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(32), default="DRAFT")
    is_current: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    citations: Mapped[list[DraftCitation]] = relationship(back_populates="draft", cascade="all, delete-orphan")


class DraftCitation(Base):
    __tablename__ = "draft_citations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    draft_id: Mapped[str] = mapped_column(ForeignKey("drafts.id", ondelete="CASCADE"), index=True)
    fact_id: Mapped[str] = mapped_column(ForeignKey("fact_cards.id", ondelete="RESTRICT"))
    block_id: Mapped[str] = mapped_column(String(120))

    draft: Mapped[Draft] = relationship(back_populates="citations")


class QualityIssue(Base):
    __tablename__ = "quality_issues"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    draft_id: Mapped[str] = mapped_column(ForeignKey("drafts.id", ondelete="CASCADE"), index=True)
    type: Mapped[str] = mapped_column(String(48))
    severity: Mapped[str] = mapped_column(String(16), default="MEDIUM")
    block_id: Mapped[str] = mapped_column(String(120), default="")
    message: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="OPEN")


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    material_id: Mapped[Optional[str]] = mapped_column(ForeignKey("materials.id", ondelete="CASCADE"), nullable=True)
    type: Mapped[str] = mapped_column(String(48))
    status: Mapped[str] = mapped_column(String(32), default=JobStatus.QUEUED.value)
    progress: Mapped[int] = mapped_column(Integer, default=0)
    stage: Mapped[str] = mapped_column(String(120), default="")
    error_code: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    retryable: Mapped[bool] = mapped_column(Boolean, default=False)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class EventLog(Base):
    __tablename__ = "event_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    event_name: Mapped[str] = mapped_column(String(120))
    properties: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

from pathlib import Path

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from workbench.ai.faults import FaultInjector
from workbench.ai.envelope import AIEnvelope
from workbench.ai.mock_provider import MockAIProvider
from workbench.ai.schemas.reference import ReferenceAnalysisResult
from workbench.db.base import Base
from workbench.db.models import FactCard, Project, ReferenceAnalysis, ReferenceCase
from workbench.references.service import ReferenceCreate, analyze_reference, create_reference


def build_session(tmp_path: Path):
    engine = create_engine(f"sqlite:///{tmp_path / 'references.db'}")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)()


def test_reference_analysis_never_creates_activity_facts(tmp_path: Path) -> None:
    session = build_session(tmp_path)
    project = Project(name="隔离分析")
    session.add(project)
    session.commit()
    reference = create_reference(
        session,
        project.id,
        ReferenceCreate(input_type="TEXT", raw_text="用现场反差引出人物成长。", source_label="案例 A"),
    )

    analysis = analyze_reference(session, MockAIProvider(delay_ms=0), reference.id)

    assert analysis.reference_id == reference.id
    assert analysis.is_demo is True
    assert session.scalar(select(func.count(FactCard.id))) == 0


def test_failed_reanalysis_preserves_previous_analysis(tmp_path: Path) -> None:
    session = build_session(tmp_path)
    project = Project(name="保留结果")
    session.add(project)
    session.commit()
    reference = create_reference(session, project.id, ReferenceCreate(input_type="TEXT", raw_text="人物视角", source_label="案例 B"))
    previous = analyze_reference(session, MockAIProvider(delay_ms=0), reference.id)
    previous_hook = previous.hook
    failing = MockAIProvider(delay_ms=0, faults=FaultInjector({"reference": ["schema_error", "schema_error"]}))

    preserved = analyze_reference(session, failing, reference.id)

    assert preserved.hook == previous_hook
    assert session.get(ReferenceCase, reference.id).status == "NEEDS_REVIEW"
    assert session.scalar(select(func.count(ReferenceAnalysis.id))) == 1


def test_real_provider_provenance_is_persisted_as_not_demo(tmp_path: Path) -> None:
    class RealProviderStub:
        def analyze_reference(self, _raw_text: str, source_id: str):
            return AIEnvelope(
                result=ReferenceAnalysisResult(
                    hook="具体行动",
                    emotion="真实克制",
                    structure="现场到价值",
                    image_role="场景证据",
                    transferable=["从行动细节开篇"],
                    avoid=["照搬原句"],
                ),
                source_ids=[source_id],
                provider="real-provider-stub",
                is_demo=False,
            )

    session = build_session(tmp_path)
    project = Project(name="真实模型来源")
    session.add(project)
    session.commit()
    reference = create_reference(
        session,
        project.id,
        ReferenceCreate(input_type="TEXT", raw_text="志愿者先整理物资，再邀请居民参与。"),
    )

    analysis = analyze_reference(session, RealProviderStub(), reference.id)

    assert analysis.is_demo is False

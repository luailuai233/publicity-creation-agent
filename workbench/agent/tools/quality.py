from pydantic import BaseModel
from sqlalchemy import select

from workbench.agent.tools.base import AgentToolContext, AgentToolResult
from workbench.db.models import Draft
from workbench.quality.service import run_quality_check


class QualityToolInput(BaseModel):
    project_id: str


class CheckQualityTool:
    name = "check_quality"
    input_model = QualityToolInput

    def can_run(self, snapshot) -> bool:
        return snapshot.draft_id is not None

    def execute(self, context: AgentToolContext, data: QualityToolInput) -> AgentToolResult:
        draft = context.session.scalar(select(Draft).where(Draft.project_id == data.project_id, Draft.is_current.is_(True)))
        issues = run_quality_check(context.session, context.provider, draft.id)
        context.session.refresh(draft)
        return AgentToolResult(summary=f"质量检查完成，发现 {len(issues)} 个问题", result_ref=draft.id, artifacts=["quality_issues"])

from pydantic import BaseModel
from sqlalchemy import select

from workbench.agent.tools.base import AgentToolContext, AgentToolResult
from workbench.db.models import ReferenceCase
from workbench.references.service import analyze_reference


class ReferenceToolInput(BaseModel):
    project_id: str


class AnalyzeReferencesTool:
    name = "analyze_references"
    input_model = ReferenceToolInput

    def can_run(self, snapshot) -> bool:
        return bool(snapshot.unanalyzed_reference_ids)

    def execute(self, context: AgentToolContext, data: ReferenceToolInput) -> AgentToolResult:
        references = list(context.session.scalars(select(ReferenceCase).where(ReferenceCase.project_id == data.project_id, ReferenceCase.selected.is_(True))).all())
        analyzed = 0
        for reference in references:
            if reference.analysis is None:
                analyze_reference(context.session, context.provider, reference.id)
                analyzed += 1
        return AgentToolResult(summary=f"已分析 {analyzed} 个参考案例", artifacts=["reference_analyses"])

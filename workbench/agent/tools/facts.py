from pydantic import BaseModel

from workbench.agent.tools.base import AgentToolContext, AgentToolResult
from workbench.facts.extractor import extract_fact_candidates
from workbench.facts.service import auto_confirm_safe_facts


class FactToolInput(BaseModel):
    project_id: str


class ValidateFactsTool:
    name = "validate_facts"
    input_model = FactToolInput

    def can_run(self, snapshot) -> bool:
        return snapshot.source_chunk_count > 0

    def execute(self, context: AgentToolContext, data: FactToolInput) -> AgentToolResult:
        created = extract_fact_candidates(context.session, data.project_id)
        confirmed = auto_confirm_safe_facts(context.session, data.project_id)
        return AgentToolResult(summary=f"已提取 {len(created)} 条事实，自动确认 {len(confirmed)} 条", artifacts=["fact_cards"])

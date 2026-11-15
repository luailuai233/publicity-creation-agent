from pydantic import BaseModel

from workbench.agent.tools.base import AgentToolContext, AgentToolResult
from workbench.strategies.service import generate_strategies


class StrategyToolInput(BaseModel):
    project_id: str


class PlanStrategiesTool:
    name = "plan_strategies"
    input_model = StrategyToolInput

    def can_run(self, snapshot) -> bool:
        return len(snapshot.eligible_fact_ids) >= 4

    def execute(self, context: AgentToolContext, data: StrategyToolInput) -> AgentToolResult:
        strategies = generate_strategies(context.session, context.provider, data.project_id)
        selected = next(strategy for strategy in strategies if strategy.selected)
        return AgentToolResult(summary=f"已生成 3 个方向并推荐“{selected.name}”", result_ref=selected.id, artifacts=["strategies"])

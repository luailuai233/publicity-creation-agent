from pydantic import BaseModel

from workbench.agent.tools.base import AgentToolContext, AgentToolResult
from workbench.strategies.service import generate_strategies
from workbench.agent.planner import has_minimum_fact_set
from workbench.db.models import Project


class StrategyToolInput(BaseModel):
    project_id: str


class PlanStrategiesTool:
    name = "plan_strategies"
    input_model = StrategyToolInput

    def can_run(self, snapshot) -> bool:
        return has_minimum_fact_set(snapshot.eligible_fact_types) and snapshot.usable_reference_count > 0 and snapshot.usable_method_count > 0

    def execute(self, context: AgentToolContext, data: StrategyToolInput) -> AgentToolResult:
        strategies = generate_strategies(context.session, context.provider, data.project_id)
        recommended_id = (context.session.get(Project, data.project_id).decisions or {}).get("recommended_strategy_id")
        recommended = next(strategy for strategy in strategies if strategy.id == recommended_id)
        return AgentToolResult(
            summary=f"已生成 3 个方向并推荐“{recommended.name}”，等待用户主动选择",
            result_ref=recommended.id,
            artifacts=["strategies"],
        )

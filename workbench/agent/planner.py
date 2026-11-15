from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field

from workbench.agent.schemas import AgentQuestion
from workbench.agent.snapshot import FactEvidence, ProjectSnapshot


class AgentAction(str, Enum):
    CALL_TOOL = "CALL_TOOL"
    ASK_USER = "ASK_USER"
    COMPLETE = "COMPLETE"
    FAIL = "FAIL"


class AgentDecision(BaseModel):
    action: AgentAction
    tool_name: Optional[str] = None
    reason_summary: str
    expected_artifacts: list[str] = Field(default_factory=list)
    question: Optional[AgentQuestion] = None


def is_auto_confirmable(fact: FactEvidence, confidence_threshold: float = 0.7) -> bool:
    if fact.source_count < 1 or fact.conflict_group or fact.identity_inferred or fact.confidence < confidence_threshold:
        return False
    if fact.type == "QUOTE" and not {"INTERVIEW", "SPEECH"}.intersection(fact.source_categories):
        return False
    return True


def has_minimum_fact_set(fact_types: list[str]) -> bool:
    return len(fact_types) >= 4 and any(fact_type in {"TIME", "LOCATION"} for fact_type in fact_types)


def _question(code: str, prompt: str) -> AgentDecision:
    return AgentDecision(
        action=AgentAction.ASK_USER,
        reason_summary=prompt,
        question=AgentQuestion(code=code, prompt=prompt, allow_free_text=True),
    )


def decide_next(snapshot: ProjectSnapshot, run: Any) -> AgentDecision:
    if run.tool_call_count >= run.max_tool_calls:
        return AgentDecision(action=AgentAction.FAIL, reason_summary=f"已达到本次运行的 {run.max_tool_calls} 次工具调用上限")
    if snapshot.pending_material_ids:
        return AgentDecision(
            action=AgentAction.CALL_TOOL,
            tool_name="parse_materials",
            reason_summary="存在尚未解析的项目资料",
            expected_artifacts=["source_chunks"],
        )
    if snapshot.fact_count == 0:
        return AgentDecision(
            action=AgentAction.CALL_TOOL,
            tool_name="validate_facts",
            reason_summary="活动资料尚未形成事实卡",
            expected_artifacts=["fact_cards"],
        )
    if snapshot.conflict_groups:
        return _question("FACT_CONFLICT", "关键事实存在冲突，请确认后继续")
    if not has_minimum_fact_set(snapshot.eligible_fact_types):
        return _question("MISSING_FACTS", "已确认且有来源的活动事实不足，请确认候选事实或补充资料")
    if snapshot.unanalyzed_reference_ids:
        return AgentDecision(
            action=AgentAction.CALL_TOOL,
            tool_name="analyze_references",
            reason_summary="存在尚未分析的参考案例",
            expected_artifacts=["reference_analyses"],
        )
    if snapshot.usable_reference_count == 0 and not snapshot.allow_without_references:
        return _question("MISSING_REFERENCE", "没有可用参考案例，是否允许按通用写作原则继续？")
    if snapshot.strategy_count != 3 or snapshot.selected_strategy_id is None:
        return AgentDecision(
            action=AgentAction.CALL_TOOL,
            tool_name="plan_strategies",
            reason_summary="需要生成并自动采用推荐创作策略",
            expected_artifacts=["strategies", "recommended_strategy"],
        )
    if snapshot.draft_id is None or snapshot.draft_is_stale:
        return AgentDecision(
            action=AgentAction.CALL_TOOL,
            tool_name="generate_content",
            reason_summary="需要生成标题、大纲和完整正文",
            expected_artifacts=["draft", "citations"],
        )
    if snapshot.quality_status in {"NOT_CHECKED", "STALE", "FAILED"}:
        return AgentDecision(
            action=AgentAction.CALL_TOOL,
            tool_name="check_quality",
            reason_summary="当前稿件尚未完成质量检查",
            expected_artifacts=["quality_issues"],
        )
    if snapshot.blocking_issue_count:
        return _question("QUALITY_BLOCKERS", "稿件仍有事实来源或冲突问题，需要处理后才能完成")
    if snapshot.auto_fixable_issue_count and run.revision_count < run.max_revisions:
        return AgentDecision(
            action=AgentAction.CALL_TOOL,
            tool_name="generate_content",
            reason_summary="存在可自动修复的表达问题，将执行一次受控修订",
            expected_artifacts=["revised_draft"],
        )
    return AgentDecision(action=AgentAction.COMPLETE, reason_summary="策略、正文和质量检查均已完成")

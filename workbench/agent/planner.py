from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field

from workbench.agent.schemas import AgentQuestion, AgentQuestionGroup, AgentQuestionOption
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
    question: Optional[AgentQuestionGroup] = None


def is_auto_confirmable(fact: FactEvidence, confidence_threshold: float = 0.7) -> bool:
    if fact.source_count < 1 or fact.conflict_group or fact.identity_inferred or fact.confidence < confidence_threshold:
        return False
    if fact.type in {"PERSON", "ROLE"} or "PHOTO" in fact.source_categories:
        return False
    if fact.type == "QUOTE" and not {"INTERVIEW", "SPEECH"}.intersection(fact.source_categories):
        return False
    return True


def has_minimum_fact_set(fact_types: list[str]) -> bool:
    activity_types = {"EVENT", "ACTIVITY", "STEP", "FLOW"}
    detail_types = {"PERSON", "LOCATION", "OPINION", "QUOTE", "NUMBER", "RESULT"}
    return any(item in activity_types for item in fact_types) and any(item in detail_types for item in fact_types)


def _question(code: str, prompt: str) -> AgentDecision:
    item = AgentQuestion(code=code, prompt=prompt, reason=prompt, allow_free_text=True)
    return AgentDecision(
        action=AgentAction.ASK_USER,
        reason_summary=prompt,
        question=AgentQuestionGroup(questions=[item]),
    )


def _blocking_questions(snapshot: ProjectSnapshot) -> list[AgentQuestion]:
    type_labels = {"NUMBER": "人数信息", "TIME": "时间信息", "LOCATION": "地点信息", "QUOTE": "引语内容"}
    details = {item.id: item for item in snapshot.conflict_details}
    questions = []
    for group_id in sorted(snapshot.conflict_groups):
        detail = details.get(group_id)
        if detail is None:
            questions.append(
                AgentQuestion(
                    id=f"fact-conflict:{group_id}",
                    code="FACT_CONFLICT",
                    prompt="关键事实存在冲突，请前往事实确认页查看候选值",
                    reason="不同材料对同一事实给出了不一致的信息",
                    affected_fact_ids=[group_id],
                    answer_type="SINGLE_CHOICE",
                )
            )
            continue
        questions.append(
            AgentQuestion(
                id=f"fact-conflict:{group_id}",
                code="FACT_CONFLICT",
                prompt=f"{type_labels.get(detail.fact_type, '事实内容')}存在冲突，请选择正确的一项",
                reason="不同材料给出了不一致的信息；选择后，未选项会标记为无效。",
                affected_fact_ids=[option.id for option in detail.options],
                answer_type="SINGLE_CHOICE",
                options=[
                    AgentQuestionOption(
                        id=option.id,
                        label=option.content,
                        evidence=[f"{source.label}：{source.excerpt}" for source in option.sources],
                    )
                    for option in detail.options
                ],
            )
        )
    if not has_minimum_fact_set(snapshot.eligible_fact_types):
        questions.append(AgentQuestion(id="missing-facts", code="MISSING_FACTS", prompt="请补充活动事实和至少一条具体细节", reason="策略生成的最低事实集合不足"))
    if snapshot.usable_reference_count == 0:
        questions.append(AgentQuestion(id="missing-reference", code="MISSING_REFERENCE", prompt="请提供一个可分析的参考案例", reason="缺少有效参考案例"))
    if snapshot.usable_method_count == 0:
        questions.append(AgentQuestion(id="missing-method", code="MISSING_METHOD", prompt="请补充或修订案例方法卡", reason="缺少有效方法卡"))
    return questions


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
    if snapshot.unanalyzed_reference_ids:
        return AgentDecision(
            action=AgentAction.CALL_TOOL,
            tool_name="analyze_references",
            reason_summary="存在尚未分析的参考案例",
            expected_artifacts=["reference_analyses"],
        )
    blockers = _blocking_questions(snapshot)
    if blockers:
        return AgentDecision(
            action=AgentAction.ASK_USER,
            reason_summary=f"发现 {len(blockers)} 个需要一次确认的阻塞问题",
            question=AgentQuestionGroup(questions=blockers),
        )
    if snapshot.strategy_count != 3:
        return AgentDecision(
            action=AgentAction.CALL_TOOL,
            tool_name="plan_strategies",
            reason_summary="需要生成三个创作策略",
            expected_artifacts=["strategies", "recommended_strategy"],
        )
    if snapshot.selected_strategy_id is None:
        return _question("STRATEGY_SELECTION", "请选择一个创作策略后继续生成正文")
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
    if snapshot.auto_fixable_issue_count and snapshot.draft_revision == 0 and run.revision_count < run.max_revisions:
        return AgentDecision(
            action=AgentAction.CALL_TOOL,
            tool_name="generate_content",
            reason_summary="存在可自动修复的表达问题，将执行一次受控修订",
            expected_artifacts=["revised_draft"],
        )
    return AgentDecision(action=AgentAction.COMPLETE, reason_summary="策略、正文和质量检查均已完成")

from types import SimpleNamespace

import pytest

from workbench.agent.planner import AgentAction, decide_next, has_minimum_fact_set, is_auto_confirmable
from workbench.agent.snapshot import FactEvidence, ProjectSnapshot


def snapshot(**changes) -> ProjectSnapshot:
    data = {
        "project_id": "project-1",
        "project_revision": 1,
        "goal": "生成校园开放日长图文",
        "pending_material_ids": [],
        "source_chunk_count": 4,
        "fact_count": 4,
        "eligible_fact_ids": ["time", "event-1", "event-2", "location"],
        "eligible_fact_types": ["TIME", "EVENT", "EVENT", "LOCATION"],
        "conflict_groups": [],
        "pending_fact_count": 0,
        "selected_reference_count": 1,
        "unanalyzed_reference_ids": [],
        "usable_reference_count": 1,
        "allow_without_references": False,
        "strategy_count": 3,
        "selected_strategy_id": "strategy-1",
        "draft_id": "draft-1",
        "draft_revision": 1,
        "draft_is_stale": False,
        "quality_status": "PASSED",
        "blocking_issue_count": 0,
        "auto_fixable_issue_count": 0,
    }
    data.update(changes)
    return ProjectSnapshot(**data)


@pytest.mark.parametrize(
    ("state", "action", "tool_name", "question_code"),
    [
        ({"pending_material_ids": ["material-1"]}, "CALL_TOOL", "parse_materials", None),
        ({"fact_count": 0, "eligible_fact_ids": [], "eligible_fact_types": []}, "CALL_TOOL", "validate_facts", None),
        ({"conflict_groups": ["time-conflict"]}, "ASK_USER", None, "FACT_CONFLICT"),
        ({"selected_reference_count": 0, "usable_reference_count": 0}, "ASK_USER", None, "MISSING_REFERENCE"),
        (
            {"selected_reference_count": 0, "usable_reference_count": 0, "allow_without_references": True, "strategy_count": 0, "selected_strategy_id": None},
            "CALL_TOOL",
            "plan_strategies",
            None,
        ),
        ({"unanalyzed_reference_ids": ["reference-1"]}, "CALL_TOOL", "analyze_references", None),
        ({"strategy_count": 0, "selected_strategy_id": None}, "CALL_TOOL", "plan_strategies", None),
        ({"draft_id": None, "quality_status": "NOT_CHECKED"}, "CALL_TOOL", "generate_content", None),
        ({"quality_status": "NOT_CHECKED"}, "CALL_TOOL", "check_quality", None),
        ({}, "COMPLETE", None, None),
    ],
)
def test_planner_selects_next_action_from_current_project_state(state, action, tool_name, question_code) -> None:
    decision = decide_next(snapshot(**state), SimpleNamespace(tool_call_count=0, max_tool_calls=12, revision_count=0, max_revisions=1))

    assert decision.action == AgentAction(action)
    assert decision.tool_name == tool_name
    assert (decision.question.code if decision.question else None) == question_code


def test_planner_stops_when_tool_budget_is_exhausted() -> None:
    decision = decide_next(snapshot(quality_status="NOT_CHECKED"), SimpleNamespace(tool_call_count=12, max_tool_calls=12, revision_count=0, max_revisions=1))

    assert decision.action == AgentAction.FAIL
    assert decision.reason_summary == "已达到本次运行的 12 次工具调用上限"


def test_planner_does_not_overwrite_a_manually_edited_draft() -> None:
    decision = decide_next(
        snapshot(draft_revision=1, auto_fixable_issue_count=1),
        SimpleNamespace(tool_call_count=4, max_tool_calls=12, revision_count=0, max_revisions=1),
    )
    assert decision.action == AgentAction.COMPLETE


def test_sourced_unconflicted_high_confidence_fact_can_be_auto_confirmed() -> None:
    fact = FactEvidence(
        id="fact-1",
        type="EVENT",
        confidence=0.9,
        source_count=1,
        source_categories=["FLOW"],
    )

    assert is_auto_confirmable(fact) is True


@pytest.mark.parametrize(
    "fact",
    [
        FactEvidence(id="no-source", type="EVENT", confidence=0.9, source_count=0),
        FactEvidence(id="conflict", type="TIME", confidence=0.9, source_count=1, conflict_group="group-1"),
        FactEvidence(id="identity", type="PERSON", confidence=0.9, source_count=1, identity_inferred=True),
        FactEvidence(id="low", type="EVENT", confidence=0.69, source_count=1),
        FactEvidence(id="quote", type="QUOTE", confidence=0.9, source_count=1, source_categories=["FLOW"]),
    ],
)
def test_unsafe_fact_cannot_be_auto_confirmed(fact: FactEvidence) -> None:
    assert is_auto_confirmable(fact) is False


def test_minimum_fact_set_requires_time_or_scene_and_three_other_facts() -> None:
    assert has_minimum_fact_set(["TIME", "EVENT", "EVENT", "LOCATION"]) is True
    assert has_minimum_fact_set(["EVENT", "EVENT", "PERSON", "NUMBER"]) is False
    assert has_minimum_fact_set(["TIME", "EVENT", "LOCATION"]) is False


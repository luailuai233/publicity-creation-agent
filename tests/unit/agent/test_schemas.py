import pytest
from pydantic import ValidationError

from workbench.agent.schemas import AgentAnswer, AgentMessageCreate, AgentQuestion, AgentRunRead
from workbench.domain.enums import AgentMessageType, AgentRunStatus, AgentStepStatus


def test_agent_runtime_enums_expose_only_public_states() -> None:
    assert {item.value for item in AgentRunStatus} == {
        "QUEUED",
        "RUNNING",
        "PAUSED",
        "WAITING_USER",
        "COMPLETED",
        "PARTIAL",
        "FAILED",
        "CANCELLED",
    }
    assert {item.value for item in AgentStepStatus} == {"QUEUED", "PROCESSING", "DONE", "FAILED", "SKIPPED"}
    assert {item.value for item in AgentMessageType} == {"PLAN", "STATUS", "QUESTION", "USER_ANSWER", "RESULT"}


def test_agent_run_defaults_limit_calls_and_revisions() -> None:
    run = AgentRunRead(
        id="run-1",
        project_id="project-1",
        status="QUEUED",
        goal="完成活动长图文",
    )

    assert run.max_tool_calls == 12
    assert run.max_revisions == 1
    assert run.tool_call_count == 0
    assert run.revision_count == 0


def test_agent_question_and_answer_are_structured() -> None:
    question = AgentQuestion(
        code="FACT_CONFLICT",
        prompt="活动开始时间是哪一个？",
        options=[{"id": "a", "label": "09:00"}, {"id": "b", "label": "09:30"}],
        allow_free_text=True,
    )
    answer = AgentAnswer(question_code=question.code, selected_option_id="b", free_text="以现场流程为准")

    assert question.options[1].label == "09:30"
    assert answer.selected_option_id == "b"


def test_hidden_reasoning_message_type_is_rejected() -> None:
    with pytest.raises(ValidationError):
        AgentMessageCreate(type="CHAIN_OF_THOUGHT", content="hidden reasoning")


from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from workbench.domain.enums import AgentMessageType, AgentRunStatus, AgentStepStatus


class AgentQuestionOption(BaseModel):
    id: str = Field(min_length=1, max_length=120)
    label: str = Field(min_length=1, max_length=300)


class AgentQuestion(BaseModel):
    code: str = Field(min_length=1, max_length=120)
    prompt: str = Field(min_length=1, max_length=1000)
    options: list[AgentQuestionOption] = Field(default_factory=list)
    allow_free_text: bool = False


class AgentAnswer(BaseModel):
    question_code: str = Field(min_length=1, max_length=120)
    selected_option_id: Optional[str] = Field(default=None, max_length=120)
    free_text: Optional[str] = Field(default=None, max_length=2000)


class AgentMessageCreate(BaseModel):
    type: AgentMessageType
    content: str = Field(min_length=1, max_length=4000)
    payload: dict = Field(default_factory=dict)


class AgentRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    status: AgentRunStatus
    goal: str
    plan_summary: str = ""
    current_stage: str = ""
    tool_call_count: int = 0
    revision_count: int = 0
    max_tool_calls: int = 12
    max_revisions: int = 1
    waiting_reason: Optional[str] = None
    waiting_payload: Optional[dict] = None
    error_code: Optional[str] = None
    cancel_requested: bool = False
    pause_requested: bool = False
    started_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None


class AgentStepRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    run_id: str
    sequence: int
    tool_name: str
    status: AgentStepStatus
    input_summary: str = ""
    output_summary: str = ""
    result_ref: Optional[str] = None
    retry_count: int = 0
    error_code: Optional[str] = None

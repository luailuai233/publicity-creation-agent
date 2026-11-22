from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from workbench.domain.enums import AgentMessageType, AgentRunStatus, AgentStepStatus


class AgentQuestionOption(BaseModel):
    id: str = Field(min_length=1, max_length=120)
    label: str = Field(min_length=1, max_length=300)
    evidence: list[str] = Field(default_factory=list)


class AgentQuestion(BaseModel):
    id: Optional[str] = Field(default=None, max_length=180)
    code: str = Field(min_length=1, max_length=120)
    prompt: str = Field(min_length=1, max_length=1000)
    reason: str = Field(default="", max_length=1000)
    affected_fact_ids: list[str] = Field(default_factory=list)
    answer_type: str = Field(default="FREE_TEXT", max_length=80)
    options: list[AgentQuestionOption] = Field(default_factory=list)
    allow_free_text: bool = False

    @model_validator(mode="after")
    def set_stable_id(self):
        if not self.id:
            self.id = self.code.lower().replace("_", "-")
        return self


class AgentQuestionGroup(BaseModel):
    questions: list[AgentQuestion] = Field(min_length=1)

    @property
    def code(self) -> str:
        return self.questions[0].code


class AgentAnswer(BaseModel):
    question_code: Optional[str] = Field(default=None, max_length=120)
    selected_option_id: Optional[str] = Field(default=None, max_length=120)
    free_text: Optional[str] = Field(default=None, max_length=2000)
    project_revision: Optional[int] = Field(default=None, ge=0)
    answers: list["AgentAnswerItem"] = Field(default_factory=list)


class AgentAnswerItem(BaseModel):
    question_id: str = Field(min_length=1, max_length=180)
    selected_option_id: Optional[str] = Field(default=None, max_length=120)
    free_text: Optional[str] = Field(default=None, max_length=4000)


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
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None

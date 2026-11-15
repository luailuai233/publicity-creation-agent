from __future__ import annotations

from typing import Any, Optional, Protocol, Type

from pydantic import BaseModel, Field

from workbench.agent.snapshot import ProjectSnapshot


class AgentToolContext(BaseModel):
    model_config = {"arbitrary_types_allowed": True}

    run_id: str
    project_id: str
    session: Any
    provider: Any = None


class AgentToolResult(BaseModel):
    summary: str
    result_ref: Optional[str] = None
    artifacts: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class AgentTool(Protocol):
    name: str
    input_model: Type[BaseModel]

    def can_run(self, snapshot: ProjectSnapshot) -> bool:
        ...

    def execute(self, context: AgentToolContext, data: BaseModel) -> AgentToolResult:
        ...

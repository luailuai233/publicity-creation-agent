import pytest
from pydantic import BaseModel

from workbench.agent.tools.base import AgentToolContext, AgentToolResult
from workbench.agent.tools.registry import DuplicateAgentToolError, ToolRegistry, UnknownAgentToolError


class ToolInput(BaseModel):
    project_id: str


class ExampleTool:
    name = "example"
    input_model = ToolInput

    def can_run(self, _snapshot) -> bool:
        return True

    def execute(self, _context: AgentToolContext, data: ToolInput) -> AgentToolResult:
        return AgentToolResult(summary=data.project_id)


def test_registry_returns_registered_tool_and_rejects_unknown_name() -> None:
    registry = ToolRegistry()
    tool = ExampleTool()
    registry.register(tool)

    assert registry.get("example") is tool
    with pytest.raises(UnknownAgentToolError):
        registry.get("not-registered")


def test_registry_rejects_duplicate_tool_name() -> None:
    registry = ToolRegistry()
    registry.register(ExampleTool())

    with pytest.raises(DuplicateAgentToolError):
        registry.register(ExampleTool())


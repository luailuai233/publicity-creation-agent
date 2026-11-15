from __future__ import annotations

from workbench.agent.tools.base import AgentTool


class UnknownAgentToolError(LookupError):
    pass


class DuplicateAgentToolError(ValueError):
    pass


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, AgentTool] = {}

    def register(self, tool: AgentTool) -> None:
        if tool.name in self._tools:
            raise DuplicateAgentToolError(tool.name)
        self._tools[tool.name] = tool

    def get(self, name: str) -> AgentTool:
        try:
            return self._tools[name]
        except KeyError as exc:
            raise UnknownAgentToolError(name) from exc

    def names(self) -> tuple[str, ...]:
        return tuple(self._tools)


def build_default_registry() -> ToolRegistry:
    from workbench.agent.tools.content import GenerateContentTool
    from workbench.agent.tools.facts import ValidateFactsTool
    from workbench.agent.tools.materials import ParseMaterialsTool
    from workbench.agent.tools.quality import CheckQualityTool
    from workbench.agent.tools.references import AnalyzeReferencesTool
    from workbench.agent.tools.strategies import PlanStrategiesTool

    registry = ToolRegistry()
    for tool in (
        ParseMaterialsTool(),
        ValidateFactsTool(),
        AnalyzeReferencesTool(),
        PlanStrategiesTool(),
        GenerateContentTool(),
        CheckQualityTool(),
    ):
        registry.register(tool)
    return registry

from typing import Protocol

from workbench.ai.envelope import AIEnvelope
from workbench.ai.schemas.reference import ReferenceAnalysisResult
from workbench.ai.schemas.strategy import StrategySetResult


class AIProvider(Protocol):
    def analyze_reference(self, raw_text: str, source_id: str) -> AIEnvelope[ReferenceAnalysisResult]:
        ...

    def generate_strategies(self, facts: list[dict], method_summaries: list[str], project_name: str) -> AIEnvelope[StrategySetResult]:
        ...

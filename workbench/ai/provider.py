from typing import Protocol

from workbench.ai.envelope import AIEnvelope
from workbench.ai.schemas.reference import ReferenceAnalysisResult
from workbench.ai.schemas.strategy import StrategySetResult
from workbench.ai.schemas.draft import DraftResult, OutlineResult
from workbench.ai.schemas.quality import QualityResult


class AIProvider(Protocol):
    def analyze_reference(self, raw_text: str, source_id: str) -> AIEnvelope[ReferenceAnalysisResult]:
        ...

    def generate_strategies(self, facts: list[dict], method_summaries: list[str], project_name: str) -> AIEnvelope[StrategySetResult]:
        ...

    def generate_outline(self, strategy: dict, facts: list[dict]) -> AIEnvelope[OutlineResult]:
        ...

    def generate_draft(self, title: str, outline: list[str], strategy: dict, facts: list[dict]) -> AIEnvelope[DraftResult]:
        ...

    def check_quality(self, content: str, facts: list[dict], method_summaries: list[str]) -> AIEnvelope[QualityResult]:
        ...

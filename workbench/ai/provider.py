from typing import Protocol

from workbench.ai.envelope import AIEnvelope
from workbench.ai.schemas.reference import ReferenceAnalysisResult
from workbench.ai.schemas.strategy import StrategySetResult
from workbench.ai.schemas.draft import DraftResult, OutlineResult, ParagraphRewriteResult
from workbench.ai.schemas.quality import QualityResult
from workbench.ai.schemas.material import ImageUnderstandingResult


class AIProvider(Protocol):
    def analyze_image(self, image_bytes: bytes, mime_type: str) -> AIEnvelope[ImageUnderstandingResult]:
        ...

    def analyze_reference(self, raw_text: str, source_id: str) -> AIEnvelope[ReferenceAnalysisResult]:
        ...

    def generate_strategies(self, facts: list[dict], method_summaries: list[str], project_name: str) -> AIEnvelope[StrategySetResult]:
        ...

    def generate_outline(self, strategy: dict, facts: list[dict]) -> AIEnvelope[OutlineResult]:
        ...

    def generate_draft(self, title: str, outline: list[str], strategy: dict, facts: list[dict]) -> AIEnvelope[DraftResult]:
        ...

    def rewrite_paragraph(self, paragraph: str, goal: str, facts: list[dict], locked_fact_ids: list[str]) -> AIEnvelope[ParagraphRewriteResult]:
        ...

    def check_quality(self, content: str, facts: list[dict], method_summaries: list[str]) -> AIEnvelope[QualityResult]:
        ...

from typing import Protocol

from workbench.ai.envelope import AIEnvelope
from workbench.ai.schemas.reference import ReferenceAnalysisResult


class AIProvider(Protocol):
    def analyze_reference(self, raw_text: str, source_id: str) -> AIEnvelope[ReferenceAnalysisResult]:
        ...

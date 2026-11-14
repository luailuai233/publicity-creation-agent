import hashlib
import time
from typing import Optional

from pydantic import ValidationError

from workbench.ai.envelope import AIEnvelope
from workbench.ai.faults import FaultInjector
from workbench.ai.schemas.reference import ReferenceAnalysisResult


class MockAIProvider:
    provider_name = "mock-structured-v1"

    def __init__(self, delay_ms: int = 250, seed: int = 17, faults: Optional[FaultInjector] = None) -> None:
        self.delay_ms = max(0, delay_ms)
        self.seed = seed
        self.faults = faults or FaultInjector()

    def _reference_payload(self, raw_text: str, source_id: str) -> dict:
        digest = hashlib.sha256(f"{self.seed}:{source_id}:{raw_text}".encode("utf-8")).digest()
        hooks = ["以一个可见的现场细节开场", "先给出反差，再交代人物变化", "用一句克制提问建立悬念"]
        structures = ["现场细节—人物行动—变化—回到活动价值", "结果反差—追溯过程—关键选择—余韵", "时间线推进—多人物切面—共同主题"]
        return {
            "hook": hooks[digest[0] % len(hooks)],
            "emotion": "通过具体行动形成温暖但不过度煽情的情绪递进",
            "structure": structures[digest[1] % len(structures)],
            "image_role": "图片承担场景证据与节奏停顿，不承担身份推断",
            "transferable": ["从具体细节进入主题", "让价值判断落在行动之后"],
            "avoid": ["照搬原句", "虚构热度、身份或活动事实"],
        }

    def analyze_reference(self, raw_text: str, source_id: str) -> AIEnvelope[ReferenceAnalysisResult]:
        warnings = []
        for attempt in range(2):
            fault = self.faults.next("reference")
            if self.delay_ms:
                time.sleep(self.delay_ms / 1000)
            payload = {} if fault == "schema_error" else self._reference_payload(raw_text, source_id)
            try:
                if fault == "timeout":
                    raise TimeoutError("simulated timeout")
                result = ReferenceAnalysisResult.model_validate(payload)
                return AIEnvelope[ReferenceAnalysisResult](
                    result=result,
                    warnings=warnings,
                    source_ids=[source_id],
                    provider=self.provider_name,
                    duration_ms=self.delay_ms,
                    token_count=max(16, len(raw_text) // 2),
                    retries=attempt,
                )
            except (ValidationError, TimeoutError):
                if attempt == 0:
                    warnings.append("第 1 次模拟输出未通过结构校验，已重试")
        warnings.append("模拟输出连续两次未通过结构校验，请人工编辑")
        return AIEnvelope[ReferenceAnalysisResult](
            result=None,
            warnings=warnings,
            source_ids=[source_id],
            provider=self.provider_name,
            duration_ms=self.delay_ms,
            retries=1,
            status="NEEDS_REVIEW",
        )

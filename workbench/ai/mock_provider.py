import hashlib
import time
from typing import Optional

from pydantic import ValidationError

from workbench.ai.envelope import AIEnvelope
from workbench.ai.faults import FaultInjector
from workbench.ai.schemas.reference import ReferenceAnalysisResult
from workbench.ai.schemas.strategy import StrategySetResult
from workbench.ai.schemas.draft import DraftResult, OutlineResult
from workbench.ai.schemas.quality import QualityResult


class MockAIProvider:
    provider_name = "mock-structured-v1"

    def __init__(self, delay_ms: int = 250, seed: int = 17, faults: Optional[FaultInjector] = None) -> None:
        self.delay_ms = max(0, delay_ms)
        self.seed = seed
        self.faults = faults or FaultInjector()
        self.last_strategy_envelope = None
        self.last_draft_fact_ids = []

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

    def generate_strategies(self, facts: list[dict], method_summaries: list[str], project_name: str) -> AIEnvelope[StrategySetResult]:
        fact_ids = [fact["id"] for fact in facts]
        fact_sets = [fact_ids[:3], fact_ids[::2] or fact_ids[:1], fact_ids[1:4] or fact_ids[-1:]]
        names = ["人物故事型", "反差成长型", "现场纪实型"]
        openings = ["从一个人物动作切入", "先呈现结果与起点的反差", "从现场声音和时间切片切入"]
        structures = ["人物细节—行动—变化—价值回扣", "结果反差—过程追溯—关键选择—余韵", "时间线—多人物切面—共同主题"]
        warnings = []
        method_summary = "；".join(method_summaries[:3]) or "从具体细节进入，行动后再回扣价值"
        for attempt in range(2):
            fault = self.faults.next("strategy")
            payload = {} if fault == "schema_error" else {
                "strategies": [
                    {
                        "name": names[index],
                        "angle": f"围绕{names[index].replace('型', '')}组织已确认事实",
                        "opening": openings[index],
                        "structure": structures[index],
                        "fact_ids": fact_sets[index],
                        "method_summary": method_summary,
                        "risk": "避免扩大人物身份、数字和未确认因果",
                    }
                    for index in range(3)
                ]
            }
            try:
                if fault == "timeout":
                    raise TimeoutError("simulated timeout")
                result = StrategySetResult.model_validate(payload)
                envelope = AIEnvelope[StrategySetResult](
                    result=result,
                    warnings=warnings,
                    fact_ids=fact_ids,
                    provider=self.provider_name,
                    duration_ms=self.delay_ms,
                    token_count=max(80, len(facts) * 30),
                    retries=attempt,
                )
                self.last_strategy_envelope = envelope
                return envelope
            except (ValidationError, TimeoutError):
                if attempt == 0:
                    warnings.append("第 1 次模拟输出未通过结构校验，已重试")
        warnings.append("模拟输出连续两次未通过结构校验，请人工编辑")
        envelope = AIEnvelope[StrategySetResult](
            result=None,
            warnings=warnings,
            fact_ids=fact_ids,
            provider=self.provider_name,
            retries=1,
            status="NEEDS_REVIEW",
        )
        self.last_strategy_envelope = envelope
        return envelope

    def _validated_envelope(self, module: str, schema, payload: dict, fact_ids: list[str]):
        warnings = []
        for attempt in range(2):
            fault = self.faults.next(module)
            candidate = {} if fault == "schema_error" else payload
            try:
                if fault == "timeout":
                    raise TimeoutError("simulated timeout")
                result = schema.model_validate(candidate)
                return AIEnvelope(
                    result=result, warnings=warnings, fact_ids=fact_ids, provider=self.provider_name,
                    duration_ms=self.delay_ms, token_count=max(60, len(fact_ids) * 30), retries=attempt,
                )
            except (ValidationError, TimeoutError):
                if attempt == 0:
                    warnings.append("第 1 次模拟输出未通过结构校验，已重试")
        warnings.append("模拟输出连续两次未通过结构校验，请人工编辑")
        return AIEnvelope(result=None, warnings=warnings, fact_ids=fact_ids, provider=self.provider_name, retries=1, status="NEEDS_REVIEW")

    def generate_outline(self, strategy: dict, facts: list[dict]) -> AIEnvelope[OutlineResult]:
        name = strategy["name"]
        payload = {
            "titles": [
                f"在现场，看见每一次认真发生",
                f"从一个动作开始：{name.replace('型', '')}里的真实变化",
                "这一天，我们把答案写在行动里",
                "不只是一场活动：那些被看见的细节",
                "沿着时间线，重回那片温暖现场",
            ],
            "outline": ["现场细节与活动背景", "人物行动和关键事实", "变化与共同价值", "克制回扣与后续期待"],
        }
        return self._validated_envelope("outline", OutlineResult, payload, [fact["id"] for fact in facts])

    def generate_draft(self, title: str, outline: list[str], strategy: dict, facts: list[dict]) -> AIEnvelope[DraftResult]:
        self.last_draft_fact_ids = [fact["id"] for fact in facts]
        blocks = []
        for index, fact in enumerate(facts, start=1):
            section = outline[min(index - 1, len(outline) - 1)] if outline else "现场记录"
            blocks.append(f"<!-- block:block-{index} -->\n### {section}\n{fact['content']}。这条信息来自已确认的活动素材。")
        content = f"# {title}\n\n" + "\n\n".join(blocks) + "\n\n我们把判断留在事实之后，也把期待留给下一次真实行动。"
        payload = {"content": content, "cited_fact_ids": self.last_draft_fact_ids}
        return self._validated_envelope("draft", DraftResult, payload, self.last_draft_fact_ids)

    def check_quality(self, content: str, facts: list[dict], method_summaries: list[str]) -> AIEnvelope[QualityResult]:
        payload = {"issues": []}
        return self._validated_envelope("quality", QualityResult, payload, [fact["id"] for fact in facts])

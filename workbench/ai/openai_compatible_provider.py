from __future__ import annotations

import base64
import json
import time
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from workbench.ai.envelope import AIEnvelope
from workbench.ai.errors import AIRequestError, AIResponseSchemaError
from workbench.ai.http_transport import OpenAIHTTPTransport
from workbench.ai.schemas.draft import DraftResult, OutlineResult, ParagraphRewriteResult
from workbench.ai.schemas.quality import QualityResult
from workbench.ai.schemas.reference import ReferenceAnalysisResult
from workbench.ai.schemas.strategy import StrategySetResult
from workbench.ai.schemas.material import ImageUnderstandingResult
from workbench.settings import Settings
from workbench.strategies.difference import validate_strategy_set


T = TypeVar("T", bound=BaseModel)


class OpenAICompatibleProvider:
    provider_name = "openai-compatible"

    def __init__(self, settings: Settings, *, transport: OpenAIHTTPTransport | None = None) -> None:
        self.settings = settings
        self.model = settings.ai_model or ""
        self.transport = transport or OpenAIHTTPTransport(
            settings.ai_base_url or "",
            settings.ai_api_key or "",
            connect_timeout=settings.ai_connect_timeout_seconds,
            read_timeout=settings.ai_read_timeout_seconds,
            write_timeout=settings.ai_write_timeout_seconds,
            pool_timeout=settings.ai_pool_timeout_seconds,
            max_connections=settings.ai_max_connections,
        )

    def analyze_image(self, image_bytes: bytes, mime_type: str) -> AIEnvelope[ImageUnderstandingResult]:
        if not self.settings.ai_vision_model:
            return AIEnvelope(
                result=None,
                warnings=["未配置视觉模型，请人工补充图片说明"],
                provider=self.provider_name,
                status="NEEDS_REVIEW",
                is_demo=False,
            )
        encoded = base64.b64encode(image_bytes).decode("ascii")
        result, retries = self._request(
            "image understanding",
            "只描述可见文字与场景，不得从人脸推断身份；返回 description、summary、confidence、identity_inferred。",
            {"image_data_url": f"data:{mime_type};base64,{encoded}"},
            ImageUnderstandingResult,
            model=self.settings.ai_vision_model,
        )
        return AIEnvelope(result=result, provider=self.provider_name, retries=retries, is_demo=False)

    def _request(
        self,
        operation: str,
        instructions: str,
        payload: dict[str, Any],
        schema: type[T],
        *,
        model: str | None = None,
        json_example: dict[str, Any] | None = None,
    ) -> tuple[T, int]:
        output_contract = ""
        if json_example is not None:
            output_contract = f"\n严格沿用以下字段和数据类型，示例 JSON：\n{json.dumps(json_example, ensure_ascii=False)}"
        messages = [
            {
                "role": "system",
                "content": f"{instructions}\n只返回符合要求的 JSON 对象，不要使用 Markdown 代码块。{output_contract}",
            },
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ]
        use_response_format = True
        for attempt in range(2):
            request_payload = {
                "model": model or self.model,
                "messages": messages,
                "temperature": 0.2,
                "max_tokens": 4096,
            }
            if use_response_format:
                request_payload["response_format"] = {"type": "json_object"}
            try:
                response = self.transport.post_chat(request_payload)
            except AIRequestError:
                if not use_response_format:
                    raise
                use_response_format = False
                request_payload.pop("response_format")
                response = self.transport.post_chat(request_payload)
            content: Any = None
            try:
                content = response["choices"][0]["message"]["content"]
                candidate = json.loads(content) if isinstance(content, str) else content
                candidate = candidate.get("result", candidate)
                return schema.model_validate(candidate), attempt
            except (KeyError, IndexError, TypeError, ValueError, ValidationError) as exc:
                if attempt == 0:
                    content_text = content if isinstance(content, str) else json.dumps(content, ensure_ascii=False)
                    if content_text.strip():
                        messages.append({"role": "assistant", "content": content_text})
                    messages.append(
                        {
                            "role": "user",
                            "content": f"上一次输出不符合 {operation} 的 JSON 结构。校验错误：{exc}。请只返回修复后的完整 JSON。",
                        }
                    )
                    continue
                raise AIResponseSchemaError(f"{operation} response failed schema validation") from exc
        raise AIResponseSchemaError(f"{operation} response failed schema validation")

    def analyze_reference(self, raw_text: str, source_id: str) -> AIEnvelope[ReferenceAnalysisResult]:
        started = time.perf_counter()
        result, retries = self._request(
            "reference analysis",
            "只分析用户提供的参考案例，提取钩子、情绪、结构、图片作用、可迁移方法和禁用表达；不要引入活动事实。",
            {"reference_text": raw_text, "source_id": source_id},
            ReferenceAnalysisResult,
            json_example={
                "hook": "从具体细节或克制提问切入",
                "emotion": "真实、克制且温暖",
                "structure": "现场细节—人物行动—变化—价值回扣",
                "image_role": "提供场景证据并形成阅读停顿",
                "transferable": ["用具体细节开场", "用行动后的变化回扣价值"],
                "avoid": ["原句、人物设定、数字和案例事实不得照搬"],
            },
        )
        return AIEnvelope(result=result, source_ids=[source_id], provider=self.provider_name, retries=retries, is_demo=False, duration_ms=int((time.perf_counter()-started)*1000))

    def generate_strategies(self, facts: list[dict], method_summaries: list[str], project_name: str) -> AIEnvelope[StrategySetResult]:
        fact_ids = {str(item["id"]) for item in facts}
        ordered_fact_ids = [str(item["id"]) for item in facts]
        example_method = method_summaries[0] if method_summaries else "参考案例方法摘要"
        result, retries = self._request(
            "strategy generation",
            "仅使用给定的已确认事实和方法摘要，返回恰好三个策略；每项包含 protagonist，且主角、开头、结构至少两个维度不同，不得复述参考原文。",
            {"project_name": project_name, "facts": facts, "method_summaries": method_summaries},
            StrategySetResult,
            json_example={
                "strategies": [
                    {
                        "name": "人物行动线",
                        "protagonist": "一位参与者",
                        "angle": "用人物行动呈现活动价值",
                        "opening": "从一个具体动作开场",
                        "structure": "人物行动—现场变化—价值回扣",
                        "fact_ids": [ordered_fact_ids[0] if ordered_fact_ids else "fact-id-1"],
                        "method_summary": example_method,
                        "risk": "不扩大人物身份和未确认因果",
                    },
                    {
                        "name": "现场反差线",
                        "protagonist": "活动现场",
                        "angle": "通过前后反差呈现变化",
                        "opening": "先呈现结果再回溯过程",
                        "structure": "结果—回溯—关键选择—余韵",
                        "fact_ids": [ordered_fact_ids[min(1, len(ordered_fact_ids) - 1)] if ordered_fact_ids else "fact-id-2"],
                        "method_summary": example_method,
                        "risk": "不虚构数字或热度",
                    },
                    {
                        "name": "多切面时间线",
                        "protagonist": "参与群体",
                        "angle": "以多个现场切面还原活动",
                        "opening": "从时间节点和场景声音开场",
                        "structure": "时间推进—多人物切面—共同主题",
                        "fact_ids": [ordered_fact_ids[min(2, len(ordered_fact_ids) - 1)] if ordered_fact_ids else "fact-id-3"],
                        "method_summary": example_method,
                        "risk": "只使用已确认活动事实",
                    },
                ],
                "recommended_index": 0,
            },
        )
        if any(set(item.fact_ids) - fact_ids for item in result.strategies):
            raise AIResponseSchemaError("strategy response referenced an unknown fact id")
        if any(not item.method_summary.strip() for item in result.strategies):
            raise AIResponseSchemaError("strategy response omitted its method source")
        difference = validate_strategy_set(result.strategies)
        if not difference.valid:
            raise AIResponseSchemaError("; ".join(difference.errors))
        return AIEnvelope(result=result, fact_ids=sorted(fact_ids), provider=self.provider_name, retries=retries, is_demo=False)

    def generate_outline(self, strategy: dict, facts: list[dict]) -> AIEnvelope[OutlineResult]:
        result, retries = self._request(
            "title and outline generation",
            "返回一个推荐标题和一份可编辑大纲，不要添加人工确认步骤。",
            {"strategy": strategy, "facts": facts},
            OutlineResult,
        )
        if len(result.titles) != 1:
            raise AIResponseSchemaError("outline response must contain exactly one recommended title")
        return AIEnvelope(result=result, fact_ids=[str(item["id"]) for item in facts], provider=self.provider_name, retries=retries, is_demo=False)

    def generate_draft(self, title: str, outline: list[str], strategy: dict, facts: list[dict]) -> AIEnvelope[DraftResult]:
        allowed = {str(item["id"]) for item in facts}
        result, retries = self._request(
            "draft generation",
            "只使用给定事实 ID 生成 Markdown 正文，并返回实际引用的事实 ID；不要输出内部推理。",
            {"title": title, "outline": outline, "strategy": strategy, "facts": facts},
            DraftResult,
        )
        if set(result.cited_fact_ids) - allowed:
            raise AIResponseSchemaError("draft response referenced an unknown fact id")
        return AIEnvelope(result=result, fact_ids=result.cited_fact_ids, provider=self.provider_name, retries=retries, is_demo=False)

    def check_quality(self, content: str, facts: list[dict], method_summaries: list[str]) -> AIEnvelope[QualityResult]:
        result, retries = self._request(
            "quality check",
            "只返回事实来源、事实冲突、相似表达、隐私风险或一般语气问题，不得输出内部推理。",
            {"content": content, "facts": facts, "method_summaries": method_summaries},
            QualityResult,
        )
        allowed_types = {"MISSING_SOURCE", "FACT_CONFLICT", "SIMILAR_EXPRESSION", "PRIVACY_RISK", "TONE_RISK"}
        if any(item.type not in allowed_types for item in result.issues):
            raise AIResponseSchemaError("quality response used an unsupported issue type")
        return AIEnvelope(result=result, fact_ids=[str(item["id"]) for item in facts], provider=self.provider_name, retries=retries, is_demo=False)

    def rewrite_paragraph(self, paragraph: str, goal: str, facts: list[dict], locked_fact_ids: list[str]) -> AIEnvelope[ParagraphRewriteResult]:
        allowed = {str(item["id"]) for item in facts}
        result, retries = self._request(
            "paragraph rewrite",
            "只改写给定段落，不得修改锁定事实；返回 content 和实际引用的 fact ID。",
            {"paragraph": paragraph, "goal": goal, "facts": facts, "locked_fact_ids": locked_fact_ids},
            ParagraphRewriteResult,
        )
        if set(result.cited_fact_ids) - allowed:
            raise AIResponseSchemaError("rewrite response referenced an unknown fact id")
        return AIEnvelope(result=result, fact_ids=result.cited_fact_ids, provider=self.provider_name, retries=retries, is_demo=False)

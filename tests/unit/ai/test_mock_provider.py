import socket

from workbench.ai.faults import FaultInjector
from workbench.ai.mock_provider import MockAIProvider
from workbench.ai.schemas.reference import ReferenceAnalysisResult


def test_reference_analysis_is_deterministic_validated_and_demo_only(monkeypatch) -> None:
    monkeypatch.setattr(socket, "create_connection", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("network forbidden")))
    provider = MockAIProvider(delay_ms=0, seed=42)

    first = provider.analyze_reference("从一双沾泥的鞋写起，回到志愿服务现场。", "ref-1")
    second = provider.analyze_reference("从一双沾泥的鞋写起，回到志愿服务现场。", "ref-1")

    assert first == second
    assert first.is_demo is True
    assert first.status == "DONE"
    assert first.retries == 0
    assert isinstance(first.result, ReferenceAnalysisResult)
    assert first.source_ids == ["ref-1"]
    assert first.provider == "mock-structured-v1"
    assert not hasattr(first, "reasoning")


def test_schema_failure_retries_once_then_succeeds() -> None:
    provider = MockAIProvider(delay_ms=0, faults=FaultInjector({"reference": ["schema_error"]}))

    result = provider.analyze_reference("先写现场，再写人物变化。", "ref-2")

    assert result.status == "DONE"
    assert result.retries == 1
    assert result.warnings == ["第 1 次模拟输出未通过结构校验，已重试"]


def test_two_schema_failures_return_needs_review() -> None:
    provider = MockAIProvider(delay_ms=0, faults=FaultInjector({"reference": ["schema_error", "schema_error"]}))

    result = provider.analyze_reference("结构待拆解", "ref-3")

    assert result.status == "NEEDS_REVIEW"
    assert result.result is None
    assert result.retries == 1
    assert result.warnings[-1] == "模拟输出连续两次未通过结构校验，请人工编辑"

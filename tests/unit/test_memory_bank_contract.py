from pathlib import Path

import pytest


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
MEMORY_BANK = REPOSITORY_ROOT / "memory-bank"
REQUIRED_MEMORY_FILES = (
    "design-document.md",
    "tech-stack.md",
    "implementation.md",
    "architecture.md",
    "progress.md",
)
AUTHORITATIVE_DOCUMENTS = (
    "design-document.md",
    "tech-stack.md",
    "implementation.md",
)
REPOSITORY_RULES = (
    "写任何代码前必须完整阅读memory-bank/architecture.md",
    "写任何代码前必须完整阅读memory-bank/design-document.md",
    "每完成一个重大功能或里程碑后，必须更新memory-bank/architecture.md",
)


def test_required_memory_bank_files_exist_and_authoritative_documents_are_nonempty() -> None:
    assert {path.name for path in MEMORY_BANK.iterdir() if path.is_file()} >= set(REQUIRED_MEMORY_FILES)

    for name in AUTHORITATIVE_DOCUMENTS:
        assert (MEMORY_BANK / name).read_text(encoding="utf-8").strip()


def test_architecture_and_progress_memory_are_initialized() -> None:
    architecture = (MEMORY_BANK / "architecture.md").read_text(encoding="utf-8")
    progress = (MEMORY_BANK / "progress.md").read_text(encoding="utf-8")

    assert all(
        heading in architecture
        for heading in ("## 当前模块边界", "## 运行命令", "## 数据流", "## Agent 决策流", "## 已知缺口")
    )
    assert all(heading in progress for heading in ("## 里程碑状态", "## 最近验证", "## 下一任务"))


def test_architecture_records_verified_runtime_baseline() -> None:
    architecture = (MEMORY_BANK / "architecture.md").read_text(encoding="utf-8")

    for fact in ("Python 3.11", "Python 3.12", "0003_agent_runtime", r"scripts\test.ps1", "journal_mode=WAL", "busy_timeout=5000"):
        assert fact in architecture


def test_architecture_records_verified_provider_boundary() -> None:
    architecture = (MEMORY_BANK / "architecture.md").read_text(encoding="utf-8")

    for fact in ("MockAIProvider", "openai_compatible", "不会静默回退", "网络错误、429 与 5xx 重试一次", "Pydantic"):
        assert fact in architecture


def test_architecture_records_material_and_reference_boundaries() -> None:
    architecture = (MEMORY_BANK / "architecture.md").read_text(encoding="utf-8")

    for fact in ("SourceChunk", "文本、公开链接和截图", "拒绝内网", "NEEDS_REVIEW", "不能直接成为默认确认", "0005_fact_identity"):
        assert fact in architecture


def test_architecture_records_fact_interrupt_strategy_editing_and_quality_rules() -> None:
    architecture = (MEMORY_BANK / "architecture.md").read_text(encoding="utf-8")

    for fact in (
        "先持久化业务变更再恢复", "推荐不等于选择", "三个维度中至少两个", "段落级改写",
        "事实锁定", "最近一次", "硬问题", "软问题", "0007_quality_resolution",
        "非空说明标记 ACCEPTED", "Markdown 默认附创作说明", "纯文本默认仅含正文",
    ):
        assert fact in architecture


@pytest.mark.parametrize("guide_name", ["CLAUDE.md", "AGENTS.md"])
def test_repository_guides_end_with_current_memory_bank_rules(guide_name: str) -> None:
    guide = (REPOSITORY_ROOT / guide_name).read_text(encoding="utf-8").rstrip()

    assert guide.endswith("\n".join(REPOSITORY_RULES))

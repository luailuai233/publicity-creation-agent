from workbench.quality.scanner import scan_content


def test_scanner_finds_unsourced_entities_conflicts_pending_privacy_and_similarity() -> None:
    content = """<!-- block:block-1 -->
张老师在东区教学楼说：“我们帮助了 120 名同学。”活动时间是 10 月 18 日 9:00。

<!-- block:block-2 -->
未成年人小明的电话是 13812345678，住址为春风路 18 号。

<!-- block:block-3 -->
一双沾着泥点的鞋，把我们重新带回那个下雨的清晨。
"""

    issues = scan_content(
        content=content,
        sourced_terms={"10 月 18 日"},
        conflict_terms={"9:00"},
        pending_terms={"120 名"},
        reference_texts=["一双沾着泥点的鞋，把我们重新带回那个下雨的清晨。"],
    )

    assert any(item.type == "MISSING_SOURCE" and item.block_id == "block-1" for item in issues)
    assert any(item.type == "FACT_CONFLICT" and item.severity == "HIGH" and item.block_id == "block-1" for item in issues)
    assert any(item.type == "PRIVACY_RISK" and item.severity == "HIGH" and item.block_id == "block-2" for item in issues)
    assert any(item.type == "SIMILAR_EXPRESSION" and item.block_id == "block-3" for item in issues)
    assert any("待确认" in item.message for item in issues)


def test_scanner_does_not_treat_generic_in_scene_phrases_as_locations() -> None:
    issues = scan_content(
        content="# 在现场，看见每一次认真发生\n\n我们把判断留在事实之后。",
        sourced_terms=set(),
        conflict_terms=set(),
        pending_terms=set(),
        reference_texts=[],
    )

    assert [issue for issue in issues if issue.type == "MISSING_SOURCE"] == []

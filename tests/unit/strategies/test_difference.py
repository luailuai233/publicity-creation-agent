from workbench.ai.schemas.strategy import StrategyResult
from workbench.strategies.difference import validate_strategy_set


def strategy(name, opening, structure, fact_ids):
    return StrategyResult(
        name=name,
        angle=f"{name}视角",
        opening=opening,
        structure=structure,
        fact_ids=fact_ids,
        method_summary="从细节进入",
        risk="避免扩大事实",
    )


def test_three_substantively_different_strategies_are_valid() -> None:
    result = validate_strategy_set(
        [
            strategy("人物故事型", "人物动作", "细节—行动—变化", ["f1", "f2", "f3"]),
            strategy("反差成长型", "结果反差", "反差—追溯—选择", ["f1", "f3", "f4"]),
            strategy("现场纪实型", "现场声音", "时间线—多切面—回扣", ["f2", "f3", "f4"]),
        ]
    )

    assert result.valid is True
    assert result.errors == []


def test_homogeneous_strategies_report_each_broken_dimension() -> None:
    duplicated = strategy("同一种", "相同开头", "相同结构", ["f1", "f2"])

    result = validate_strategy_set([duplicated, duplicated, duplicated])

    assert result.valid is False
    assert set(result.errors) == {"叙事主角、开头方式和文章结构至少需要两个维度存在实质差异", "事实集合不能完全相同"}

from dataclasses import dataclass

from workbench.ai.schemas.strategy import StrategyResult


@dataclass(frozen=True)
class DifferenceResult:
    valid: bool
    errors: list[str]


def validate_strategy_set(strategies: list[StrategyResult]) -> DifferenceResult:
    errors = []
    if len(strategies) != 3:
        errors.append("需要恰好 3 个策略")
    dimensions = (
        len({item.protagonist for item in strategies}) > 1,
        len({item.opening for item in strategies}) > 1,
        len({item.structure for item in strategies}) > 1,
    )
    if sum(dimensions) < 2:
        errors.append("叙事主角、开头方式和文章结构至少需要两个维度存在实质差异")
    if len({tuple(sorted(item.fact_ids)) for item in strategies}) < 2:
        errors.append("事实集合不能完全相同")
    return DifferenceResult(valid=not errors, errors=errors)

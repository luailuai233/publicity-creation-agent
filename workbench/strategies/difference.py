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
    if len({item.name for item in strategies}) < 2:
        errors.append("叙事视角不足 2 种")
    if len({item.opening for item in strategies}) < 2:
        errors.append("开头方式不足 2 种")
    if len({item.structure for item in strategies}) < 2:
        errors.append("文章结构不足 2 种")
    if len({tuple(sorted(item.fact_ids)) for item in strategies}) < 2:
        errors.append("事实集合不能完全相同")
    return DifferenceResult(valid=not errors, errors=errors)

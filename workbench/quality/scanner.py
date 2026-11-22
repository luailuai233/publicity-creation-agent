from dataclasses import dataclass
import re

from workbench.quality.similarity import find_similar_fragments


@dataclass(frozen=True)
class IssueCandidate:
    type: str
    severity: str
    block_id: str
    message: str
    resolution_policy: str = "SOFT"
    resolution_note: str = ""
    fragment: str = ""
    suggestion: str = ""


BLOCK_MARKER = re.compile(r"<!--\s*block:([\w-]+)\s*-->")
ENTITY_PATTERNS = [
    ("人名或身份", re.compile(r"[\u4e00-\u9fff]{2,4}(?:老师|同学|校长|主任|志愿者)")),
    ("时间", re.compile(r"\d{1,2}\s*月\s*\d{1,2}\s*日|\d{1,2}[:：]\d{2}")),
    ("地点", re.compile(r"(?:地点[:：][^，。\n]{2,20}|在(?!现场|事实|行动|活动)[^，。\n]{2,20})")),
    ("数字", re.compile(r"\d+(?:\.\d+)?\s*(?:人|名|组|场|次|份|元)")),
    ("引语", re.compile(r"[“\"][^”\"]{4,120}[”\"]")),
]
PRIVACY_PATTERN = re.compile(r"1[3-9]\d{9}|未成年人|住址|身份证|联系方式")


def _blocks(content: str) -> list[tuple[str, str]]:
    markers = list(BLOCK_MARKER.finditer(content))
    if not markers:
        return [("document", content)]
    result = []
    if markers[0].start() > 0:
        result.append(("document", content[:markers[0].start()]))
    for index, marker in enumerate(markers):
        end = markers[index + 1].start() if index + 1 < len(markers) else len(content)
        result.append((marker.group(1), content[marker.end():end]))
    return result


def _normalize(value: str) -> str:
    return re.sub(r"\s+", "", value)


def scan_content(content: str, sourced_terms: set[str], conflict_terms: set[str], pending_terms: set[str], reference_texts: list[str]) -> list[IssueCandidate]:
    issues = []
    for block_id, block in _blocks(content):
        for label, pattern in ENTITY_PATTERNS:
            matches = [match.group(0) for match in pattern.finditer(block)]
            unsourced = [value for value in matches if not any(value in source or source in value for source in sourced_terms)]
            if unsourced:
                policy = "HARD" if label in {"人名或身份", "引语"} else "SOFT"
                issues.append(IssueCandidate("MISSING_SOURCE", "HIGH", block_id, f"{label}缺少已确认来源：{unsourced[0]}", resolution_policy=policy, fragment=unsourced[0], suggestion="补充并确认来源，或删除该表述"))
        for term in pending_terms:
            if term and term in block:
                issues.append(IssueCandidate("MISSING_SOURCE", "MEDIUM", block_id, f"包含待确认事实：{term}", resolution_policy="HARD", fragment=term, suggestion="先确认事实来源"))
        for term in conflict_terms:
            if term and term in block:
                issues.append(IssueCandidate("FACT_CONFLICT", "HIGH", block_id, f"正文使用了冲突事实：{term}", resolution_policy="HARD", fragment=term, suggestion="解决事实冲突后重新检查"))
        if PRIVACY_PATTERN.search(block):
            fragment = PRIVACY_PATTERN.search(block).group(0)
            issues.append(IssueCandidate("PRIVACY_RISK", "HIGH", block_id, "包含未成年人、联系方式或精确住址等隐私风险", resolution_policy="HARD", fragment=fragment, suggestion="删除、匿名化或取得有效授权"))
        matches = find_similar_fragments(block, reference_texts)
        if matches:
            match = matches[0]
            issues.append(IssueCandidate("SIMILAR_EXPRESSION", "MEDIUM", block_id, f"与参考案例存在过近表达（位置 {match['start']}-{match['end']}）", fragment=match["fragment"], suggestion="保留事实，换用自己的叙述结构与措辞"))
    return issues

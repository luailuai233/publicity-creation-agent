from dataclasses import dataclass
import re


@dataclass(frozen=True)
class IssueCandidate:
    type: str
    severity: str
    block_id: str
    message: str


BLOCK_MARKER = re.compile(r"<!--\s*block:([\w-]+)\s*-->")
ENTITY_PATTERNS = [
    ("人名或身份", re.compile(r"[\u4e00-\u9fff]{2,4}(?:老师|同学|校长|主任|志愿者)")),
    ("时间", re.compile(r"\d{1,2}\s*月\s*\d{1,2}\s*日|\d{1,2}[:：]\d{2}")),
    ("地点", re.compile(r"(?:在|地点[:：])[^，。\n]{2,20}")),
    ("数字", re.compile(r"\d+(?:\.\d+)?\s*(?:人|名|组|场|次|份|元)")),
    ("引语", re.compile(r"[“\"][^”\"]{4,120}[”\"]")),
]
PRIVACY_PATTERN = re.compile(r"1[3-9]\d{9}|未成年人|住址|身份证|联系方式")


def _blocks(content: str) -> list[tuple[str, str]]:
    markers = list(BLOCK_MARKER.finditer(content))
    if not markers:
        return [("document", content)]
    result = []
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
                issues.append(IssueCandidate("MISSING_SOURCE", "HIGH", block_id, f"{label}缺少已确认来源：{unsourced[0]}"))
        for term in pending_terms:
            if term and term in block:
                issues.append(IssueCandidate("MISSING_SOURCE", "MEDIUM", block_id, f"包含待确认事实：{term}"))
        for term in conflict_terms:
            if term and term in block:
                issues.append(IssueCandidate("FACT_CONFLICT", "HIGH", block_id, f"正文使用了冲突事实：{term}"))
        if PRIVACY_PATTERN.search(block):
            issues.append(IssueCandidate("PRIVACY_RISK", "HIGH", block_id, "包含未成年人、联系方式或精确住址等隐私风险"))
        normalized_block = _normalize(block)
        for reference in reference_texts:
            normalized_reference = _normalize(reference)
            if len(normalized_reference) >= 20 and normalized_reference in normalized_block:
                issues.append(IssueCandidate("SIMILAR_EXPRESSION", "MEDIUM", block_id, "与参考案例存在过近的连续表达"))
                break
    return issues

import re


def normalized_overlap(left: str, right: str) -> bool:
    left = re.sub(r"\s+", "", left)
    right = re.sub(r"\s+", "", right)
    return len(right) >= 20 and right in left

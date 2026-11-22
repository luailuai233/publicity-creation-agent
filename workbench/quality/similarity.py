import re
from difflib import SequenceMatcher


PUNCTUATION = re.compile(r"[\s，。！？；：、,.!?;:'\"“”‘’（）()【】\[\]—…-]+")


def normalize_expression(value: str) -> str:
    return PUNCTUATION.sub("", value)


def find_similar_fragments(left: str, references: list[str], min_length: int = 20) -> list[dict]:
    normalized_left = normalize_expression(left)
    matches: list[dict] = []
    for reference_index, reference in enumerate(references):
        normalized_reference = normalize_expression(reference)
        if len(normalized_reference) < min_length:
            continue
        match = SequenceMatcher(None, normalized_left, normalized_reference, autojunk=False).find_longest_match()
        if match.size >= min_length:
            matches.append({"fragment": normalized_left[match.a:match.a + match.size], "start": match.a, "end": match.a + match.size, "reference_index": reference_index})
    return matches


def normalized_overlap(left: str, right: str) -> bool:
    return bool(find_similar_fragments(left, [right]))

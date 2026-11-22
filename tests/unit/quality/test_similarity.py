from workbench.quality.similarity import find_similar_fragments


def test_similarity_ignores_punctuation_and_reports_position() -> None:
    matches = find_similar_fragments("这是一次温暖的行动，大家在雨中坚持完成了全部任务。", ["这是一次温暖的行动！大家在雨中坚持，完成了全部任务。"])
    assert matches and matches[0]["start"] == 0
    assert "温暖的行动" in matches[0]["fragment"]


def test_similarity_ignores_short_common_expression() -> None:
    assert find_similar_fragments("感谢大家积极参与", ["感谢大家积极参与"]) == []

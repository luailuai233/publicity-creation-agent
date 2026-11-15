from workbench.agent.fingerprints import fingerprint_for


def test_fingerprint_is_stable_for_semantically_identical_payloads() -> None:
    first = fingerprint_for("plan_strategies", {"facts": [{"id": "f1", "revision": 2}], "goal": "报道"})
    second = fingerprint_for("plan_strategies", {"goal": "报道", "facts": [{"revision": 2, "id": "f1"}]})

    assert first == second
    assert len(first) == 64


def test_fingerprint_changes_when_fact_revision_or_strategy_override_changes() -> None:
    original = fingerprint_for("generate_content", {"fact_revision": 2, "strategy_id": "s1"})

    assert fingerprint_for("generate_content", {"fact_revision": 3, "strategy_id": "s1"}) != original
    assert fingerprint_for("generate_content", {"fact_revision": 2, "strategy_id": "s2"}) != original

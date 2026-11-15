def unwrap(response):
    assert response.status_code < 400, response.text
    return response.json()["data"]


def test_resettable_demo_runs_from_sources_to_markdown_export(demo_client) -> None:
    client, root = demo_client
    demo = unwrap(client.post("/api/demo/reset"))
    project_id = demo["project_id"]
    assert len(demo["materials"]) == 3
    assert len(demo["references"]) == 3

    facts = unwrap(client.get(f"/api/projects/{project_id}/facts"))
    assert all(fact["sources"] for fact in facts)
    conflicting = [fact for fact in facts if fact["conflict_group"]]
    chosen = conflicting[0]
    unwrap(client.post(f"/api/facts/conflicts/{chosen['conflict_group']}/resolve", json={"fact_id": chosen["id"]}))

    for reference in demo["references"]:
        analyzed = unwrap(client.post(f"/api/references/{reference['id']}/analyze"))
        assert analyzed["analysis"]["transferable"]

    strategies = unwrap(client.post(f"/api/projects/{project_id}/strategies/generate"))
    selected = unwrap(client.patch(f"/api/strategies/{strategies[0]['id']}/select", json={}))
    assert selected["selected"] is True
    outline = unwrap(client.post(f"/api/projects/{project_id}/drafts/outline"))
    draft = unwrap(client.post(f"/api/projects/{project_id}/drafts/generate", json={"title": outline["titles"][0], "outline": outline["outline"]}))
    saved = unwrap(client.patch(f"/api/drafts/{draft['id']}", json={"content": draft["content"] + "\n\n人工复核完成。"}))
    assert saved["version"] == 1
    assert saved["content"].endswith("人工复核完成。")
    unwrap(client.post(f"/api/drafts/{saved['id']}/check"))
    exported = unwrap(client.post(f"/api/drafts/{saved['id']}/export", json={"confirm_high": True}))
    export_path = root / "exports" / exported["file_name"]
    assert export_path.is_file()
    assert export_path.parent == (root / "exports").resolve()
    text = export_path.read_text(encoding="utf-8")
    assert "provider" not in text and "fact_id" not in text


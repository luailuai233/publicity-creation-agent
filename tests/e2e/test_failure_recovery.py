def test_demo_faults_preserve_sibling_results_and_previous_analysis(demo_client) -> None:
    client, _ = demo_client
    data = client.post("/api/demo/reset").json()["data"]
    first, second, third = data["references"]
    assert client.post(f"/api/references/{first['id']}/analyze").status_code == 200

    configured = client.post("/api/demo/faults", json={"faults": {"reference": ["schema_error", "schema_error"]}})
    assert configured.status_code == 200
    failed = client.post(f"/api/references/{first['id']}/analyze")
    assert failed.status_code == 200
    assert failed.json()["data"]["analysis"] is not None
    assert failed.json()["data"]["status"] == "NEEDS_REVIEW"

    assert client.post(f"/api/references/{second['id']}/analyze").status_code == 200
    assert client.post(f"/api/references/{third['id']}/analyze").status_code == 200
    listed = client.get(f"/api/projects/{data['project_id']}/references").json()["data"]
    assert sum(item["analysis"] is not None for item in listed) == 3


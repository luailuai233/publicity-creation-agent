from sqlalchemy import select

from workbench.db.models import AgentRun, AgentStep
from tests.integration.agent.test_tools import seed_ready_project


def test_http_one_start_completes_agent_and_workspace_survives_refresh(demo_client) -> None:
    client, _root = demo_client
    app = client.app
    with app.state.session_factory() as session:
        project, _reference, _facts = seed_ready_project(session)
        project_id = project.id

    started = client.post(f"/api/projects/{project_id}/agent-runs", json={"goal": "生成一篇可溯源活动长图文"})
    run_id = started.json()["data"]["id"]
    waiting_workspace = client.get(f"/project/{project_id}/agent")

    assert started.status_code == 201
    with app.state.session_factory() as session:
        waiting = session.get(AgentRun, run_id)
        assert waiting.status == "WAITING_USER"
        assert waiting.waiting_reason == "STRATEGY_SELECTION"
    strategies = client.get(f"/api/projects/{project_id}/strategies").json()["data"]
    selected = client.patch(f"/api/strategies/{strategies[0]['id']}/select", json={"tone": "真实、温暖、克制", "length": "1200-1600", "focus_fact_ids": []})
    refreshed = client.get(f"/project/{project_id}/agent")

    with app.state.session_factory() as session:
        run = session.get(AgentRun, run_id)
        steps = list(session.scalars(select(AgentStep).where(AgentStep.run_id == run_id).order_by(AgentStep.sequence)).all())

    assert selected.status_code == 200
    assert run.status == "COMPLETED"
    assert [step.tool_name for step in steps] == ["analyze_references", "plan_strategies", "generate_content", "check_quality"]
    for step in steps:
        assert step.tool_name in (waiting_workspace.text + refreshed.text)
    assert "COMPLETED" in refreshed.text

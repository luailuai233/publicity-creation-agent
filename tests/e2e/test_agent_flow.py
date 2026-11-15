from sqlalchemy import select

from workbench.agent.repository import create_run
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
    workspace = client.get(f"/project/{project_id}/agent")
    refreshed = client.get(f"/project/{project_id}/agent")

    with app.state.session_factory() as session:
        run = session.get(AgentRun, run_id)
        steps = list(session.scalars(select(AgentStep).where(AgentStep.run_id == run_id).order_by(AgentStep.sequence)).all())

    assert started.status_code == 201
    assert run.status == "COMPLETED"
    assert [step.tool_name for step in steps] == ["analyze_references", "plan_strategies", "generate_content", "check_quality"]
    for step in steps:
        assert step.tool_name in workspace.text
    assert "COMPLETED" in refreshed.text

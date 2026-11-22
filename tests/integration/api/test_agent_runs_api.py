from pathlib import Path

from fastapi.testclient import TestClient

from workbench.db.base import Base
from workbench.db.models import AgentRun, ReferenceCase, Strategy
from workbench.main import create_app
from workbench.settings import Settings


def build_client(tmp_path: Path):
    app = create_app(Settings(project_root=tmp_path))
    Base.metadata.create_all(app.state.engine)
    app.state.agent_runner.run = lambda _run_id: None
    return app, TestClient(app)


def test_agent_run_api_start_get_steps_and_reuses_active_run(tmp_path: Path) -> None:
    app, client = build_client(tmp_path)
    with client:
        project = client.post("/api/projects", json={"name": "Agent API"}).json()["data"]
        started = client.post(f"/api/projects/{project['id']}/agent-runs", json={"goal": "完成一篇活动报道"})
        duplicate = client.post(f"/api/projects/{project['id']}/agent-runs", json={"goal": "重复启动"})
        run_id = started.json()["data"]["id"]
        fetched = client.get(f"/api/agent-runs/{run_id}")
        steps = client.get(f"/api/agent-runs/{run_id}/steps")

    assert started.status_code == 201
    assert duplicate.status_code == 200
    assert duplicate.json()["data"]["id"] == run_id
    assert fetched.json()["data"]["goal"] == "完成一篇活动报道"
    assert steps.json()["data"] == []
    for response in (started, duplicate, fetched, steps):
        assert set(response.json()) == {"data", "error", "requestId"}


def test_agent_run_api_controls_answers_retry_and_rejects_invalid_transition(tmp_path: Path) -> None:
    app, client = build_client(tmp_path)
    with client:
        project = client.post("/api/projects", json={"name": "Agent 控制"}).json()["data"]
        run_id = client.post(f"/api/projects/{project['id']}/agent-runs", json={"goal": "生成报道"}).json()["data"]["id"]
        paused = client.post(f"/api/agent-runs/{run_id}/pause")
        invalid_answer = client.post(
            f"/api/agent-runs/{run_id}/answers",
            json={"question_code": "MISSING_REFERENCE", "selected_option_id": "continue"},
        )
        resumed = client.post(f"/api/agent-runs/{run_id}/resume")
        cancelled = client.post(f"/api/agent-runs/{run_id}/cancel")
        invalid_resume = client.post(f"/api/agent-runs/{run_id}/resume")

        with app.state.session_factory() as session:
            run = session.get(AgentRun, run_id)
            run.status = "PARTIAL"
            run.active_key = None
            session.commit()
        retried = client.post(f"/api/projects/{project['id']}/agent-runs/latest/retry")

    assert paused.json()["data"]["status"] == "PAUSED"
    assert invalid_answer.status_code == 409
    assert resumed.json()["data"]["status"] == "QUEUED"
    assert cancelled.json()["data"]["status"] == "CANCELLED"
    assert invalid_resume.status_code == 409
    assert retried.status_code == 201
    assert retried.json()["data"]["tool_call_count"] == 0


def test_waiting_run_accepts_answer_and_persists_project_decision(tmp_path: Path) -> None:
    app, client = build_client(tmp_path)
    with client:
        project = client.post("/api/projects", json={"name": "无参考项目"}).json()["data"]
        run_id = client.post(f"/api/projects/{project['id']}/agent-runs", json={"goal": "生成报道"}).json()["data"]["id"]
        with app.state.session_factory() as session:
            run = session.get(AgentRun, run_id)
            run.status = "WAITING_USER"
            run.waiting_reason = "MISSING_REFERENCE"
            run.waiting_payload = {"project_revision": run.project.revision, "questions": [{"id": "reference-text", "code": "MISSING_REFERENCE", "affected_fact_ids": []}]}
            waiting_revision = run.project.revision
            session.commit()

        answered = client.post(
            f"/api/agent-runs/{run_id}/answers",
            json={"project_revision": waiting_revision, "answers": [{"question_id": "reference-text", "free_text": "用户主动提供的案例正文"}]},
        )

        with app.state.session_factory() as session:
            run = session.get(AgentRun, run_id)
            reference = session.query(ReferenceCase).filter_by(project_id=project["id"]).one()

    assert answered.status_code == 200
    assert answered.json()["data"]["status"] == "QUEUED"
    assert reference.raw_text == "用户主动提供的案例正文"


def test_run_status_exposes_next_action_and_step_duration(tmp_path: Path) -> None:
    app, client = build_client(tmp_path)
    with client:
        project = client.post("/api/projects", json={"name": "状态恢复"}).json()["data"]
        run_id = client.post(f"/api/projects/{project['id']}/agent-runs", json={"goal": "生成报道"}).json()["data"]["id"]
        with app.state.session_factory() as session:
            run = session.get(AgentRun, run_id); run.status = "WAITING_USER"; run.waiting_reason = "MISSING_FACTS"; session.commit()
        payload = client.get(f"/api/agent-runs/{run_id}").json()["data"]

    assert payload["next_action"] == "请一次回答全部待确认问题"
    assert isinstance(payload["elapsed_ms"], int)


def test_selecting_strategy_resumes_waiting_agent(tmp_path: Path) -> None:
    app, client = build_client(tmp_path)
    with client:
        project = client.post("/api/projects", json={"name": "策略门禁"}).json()["data"]
        run_id = client.post(f"/api/projects/{project['id']}/agent-runs", json={"goal": "生成报道"}).json()["data"]["id"]
        with app.state.session_factory() as session:
            strategy = Strategy(project_id=project["id"], name="人物", protagonist="志愿者", angle="现场", opening="动作", structure="时间线", fact_ids=[], method_summary="细节", risk="", selected=False)
            session.add(strategy); session.flush()
            run = session.get(AgentRun, run_id); run.status = "WAITING_USER"; run.waiting_reason = "STRATEGY_SELECTION"; run.waiting_payload = {"questions": [{"id": "strategy-selection", "code": "STRATEGY_SELECTION"}]}; session.commit(); strategy_id = strategy.id
        response = client.patch(f"/api/strategies/{strategy_id}/select", json={"tone": "克制", "length": "1200-1600", "focus_fact_ids": []})
        with app.state.session_factory() as session:
            run = session.get(AgentRun, run_id)

    assert response.status_code == 200
    assert run.status == "QUEUED"
    assert run.waiting_reason is None

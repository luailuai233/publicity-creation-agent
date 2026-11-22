from pathlib import Path


def test_ci_covers_three_operating_systems_and_release_gates() -> None:
    root = Path(__file__).resolve().parents[2]
    workflow = (root / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

    for runner in ("ubuntu-latest", "windows-latest", "macos-latest"):
        assert runner in workflow
    for requirement in ("requirements.lock.txt", "alembic upgrade head", "pytest", "ruff check", "playwright install", "tests/e2e", "gitleaks"):
        assert requirement in workflow
    assert "AI_PROVIDER: mock" in workflow
    assert "runner.temp" in workflow
    assert "DATABASE_URL:" in workflow
    assert "Prepare runtime directories" in workflow
    assert "D:\\aipm\\demo" not in workflow

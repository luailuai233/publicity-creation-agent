from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _requirements(name: str) -> list[str]:
    return [line.strip() for line in (ROOT / name).read_text(encoding="utf-8").splitlines() if line.strip() and not line.startswith("#")]


def test_runtime_and_development_dependencies_are_separated_and_locked() -> None:
    runtime = _requirements("requirements.txt")
    development = _requirements("requirements-dev.txt")
    locked = _requirements("requirements.lock.txt")

    assert any(line.startswith("httpx") for line in runtime)
    assert any(line.startswith("ruff") for line in development)
    assert not any(line.startswith(("langgraph", "celery", "redis", "psycopg")) for line in runtime + development)
    assert all("==" in line for line in locked)
    for package in ("fastapi", "sqlalchemy", "httpx", "pytest", "playwright", "ruff"):
        assert any(line.lower().startswith(f"{package}==") for line in locked)

from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from workbench.runtime_paths import RuntimePaths, get_runtime_paths


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="", extra="ignore")

    app_env: str = "development"
    app_host: str = "127.0.0.1"
    app_port: int = 8000
    mock_ai_delay_ms: int = Field(default=250, ge=0, le=5000)
    project_root: Optional[Path] = None

    @property
    def paths(self) -> RuntimePaths:
        return get_runtime_paths(self.project_root)

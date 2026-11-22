from pathlib import Path
from typing import Optional

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from workbench.runtime_paths import RuntimePaths, get_runtime_paths


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="", extra="ignore")

    app_env: str = "development"
    app_host: str = "127.0.0.1"
    app_port: int = 8000
    mock_ai_delay_ms: int = Field(default=250, ge=0, le=5000)
    ai_provider: str = "mock"
    ai_base_url: Optional[str] = None
    ai_api_key: Optional[SecretStr] = None
    ai_model: Optional[str] = None
    ai_vision_model: Optional[str] = None
    ai_connect_timeout_seconds: float = Field(default=10, gt=0)
    ai_read_timeout_seconds: float = Field(default=120, gt=0)
    ai_write_timeout_seconds: float = Field(default=30, gt=0)
    ai_pool_timeout_seconds: float = Field(default=10, gt=0)
    ai_max_connections: int = Field(default=10, ge=1, le=100)
    image_max_pixels: int = Field(default=40_000_000, ge=1)
    max_request_body_bytes: int = Field(default=25 * 1024 * 1024, ge=1024, le=250 * 1024 * 1024)
    project_root: Optional[Path] = None

    @model_validator(mode="after")
    def validate_provider_configuration(self):
        if self.ai_provider == "openai_compatible":
            missing = [
                name
                for name, value in (("AI_BASE_URL", self.ai_base_url), ("AI_API_KEY", self.ai_api_key), ("AI_MODEL", self.ai_model))
                if not value
            ]
            if missing:
                raise ValueError(f"openai_compatible provider requires: {', '.join(missing)}")
        return self

    @property
    def paths(self) -> RuntimePaths:
        return get_runtime_paths(self.project_root)

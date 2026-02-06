"""
Congress Twin configuration — single source of truth.

NVS-GenAI: Pydantic BaseSettings, load at startup, fail fast on invalid.
"""

from typing import Optional

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    """Central config; single initialization."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # SQLite database (embedded, no server required)
    sqlite_db_path: str = Field(
        default="congress_twin.db",
        description="Path to SQLite database file (relative to project root or absolute)"
    )

    # MS Graph API (Phase 1 — optional; when set, sync uses live Planner)
    graph_client_id: Optional[str] = Field(default=None)
    graph_client_secret: Optional[str] = Field(default=None)
    graph_tenant_id: Optional[str] = Field(default=None)
    graph_scope: str = Field(default="https://graph.microsoft.com/.default")

    cors_allow_all: bool = Field(default=True)
    cors_origins: str = Field(
        default="http://localhost:3000,http://127.0.0.1:3000,http://localhost:3003,http://127.0.0.1:3003"
    )
    # Optional: direct link to open the plan in MS Planner / Teams
    planner_plan_url: Optional[str] = Field(default=None, description="URL to open plan in MS Planner (e.g. Teams task list)")

    @property
    def sqlite_conn(self) -> str:
        """SQLite connection string for SQLAlchemy."""
        import os
        db_path = self.sqlite_db_path
        if not os.path.isabs(db_path):
            # Relative to project root (congress-twin/)
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            db_path = os.path.join(project_root, db_path)
        return f"sqlite:///{db_path}"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


_settings: Optional[AppSettings] = None


def get_settings() -> AppSettings:
    """Return settings singleton. Fail fast on first load if invalid."""
    global _settings
    if _settings is None:
        _settings = AppSettings()
    return _settings

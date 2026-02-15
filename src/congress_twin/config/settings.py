"""
Congress Twin configuration — single source of truth.

NVS-GenAI: Pydantic BaseSettings, load at startup, fail fast on invalid.
"""

import os
from typing import Optional

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve .env from project root (congress-twin/) so Groq/LLM creds load regardless of cwd
_CONFIG_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(_CONFIG_DIR)))
_DOTENV_PATH = os.path.join(_PROJECT_ROOT, ".env")


class AppSettings(BaseSettings):
    """Central config; single initialization. LLM/Groq creds are driven only from .env / env vars."""

    model_config = SettingsConfigDict(
        env_file=_DOTENV_PATH,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # SQLite database (embedded, no server required) — used when PostgreSQL not configured
    sqlite_db_path: str = Field(
        default="congress_twin.db",
        description="Path to SQLite database file (relative to project root or absolute)"
    )

    # PostgreSQL (shared infra; when set, overrides SQLite)
    postgres_host: Optional[str] = Field(default=None, description="PostgreSQL host (e.g. 192.168.0.100)")
    postgres_port: int = Field(default=5432, description="PostgreSQL port")
    postgres_user: str = Field(default="admin", description="PostgreSQL user")
    postgres_password: str = Field(default="admin", description="PostgreSQL password")
    postgres_database: str = Field(default="tpcds", description="PostgreSQL database name")
    postgres_schema: str = Field(default="congress_twin", description="PostgreSQL schema for Congress Twin tables")

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

    # Chat semantic layer (Phase 1 Hybrid): optional LLM for intent extraction
    # All values from .env / env only (no hardcoding). Prefer Groq if GROQ_API_KEY set.
    groq_api_key: Optional[str] = Field(
        default=None,
        description="Groq API key; set in .env as GROQ_API_KEY",
        validation_alias="GROQ_API_KEY",
    )
    groq_model: str = Field(
        default="llama-3.1-8b-instant",
        description="Groq model; set in .env as GROQ_MODEL",
        validation_alias="GROQ_MODEL",
    )
    chat_llm_api_key: Optional[str] = Field(
        default=None,
        description="OpenAI/other API key when not using Groq; set in .env as CHAT_LLM_API_KEY",
        validation_alias="CHAT_LLM_API_KEY",
    )
    chat_llm_model: str = Field(
        default="gpt-4o-mini",
        description="Model when using CHAT_LLM; set in .env as CHAT_LLM_MODEL",
        validation_alias="CHAT_LLM_MODEL",
    )
    chat_llm_base_url: Optional[str] = Field(
        default=None,
        description="Optional base URL; set in .env as CHAT_LLM_BASE_URL",
        validation_alias="CHAT_LLM_BASE_URL",
    )

    # Optional: path to SQLite file for chat traces (few-shot / RAG). If unset, trace store is no-op.
    chat_trace_store_path: Optional[str] = Field(default=None, description="Path to chat_traces.db for storing successful chat turns")

    @property
    def sqlite_conn(self) -> str:
        """SQLite connection string for SQLAlchemy."""
        db_path = self.sqlite_db_path
        if not os.path.isabs(db_path):
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            db_path = os.path.join(project_root, db_path)
        return f"sqlite:///{db_path}"

    @property
    def database_url(self) -> str:
        """Primary database URL: PostgreSQL when configured, else SQLite."""
        if self.postgres_host:
            return (
                f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}"
                f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_database}"
            )
        return self.sqlite_conn

    @property
    def is_postgres(self) -> bool:
        """True when using PostgreSQL (postgres_host configured)."""
        return bool(self.postgres_host)

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

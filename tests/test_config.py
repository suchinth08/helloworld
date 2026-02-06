"""
Tests for Congress Twin configuration.

NVS-GenAI: Config = single source of truth, Pydantic BaseSettings.
"""

import pytest

from congress_twin.config import AppSettings, get_settings


class TestConfigLoads:
    def test_get_settings_returns_app_settings(self) -> None:
        s = get_settings()
        assert isinstance(s, AppSettings)

    def test_pg_conn_is_connection_string(self) -> None:
        s = get_settings()
        assert "postgresql" in s.pg_conn.lower()
        assert s.pg_host in s.pg_conn
        assert s.pg_database in s.pg_conn

    def test_neo_uri_set(self) -> None:
        s = get_settings()
        assert s.neo_uri
        assert "bolt" in s.neo_uri.lower() or "neo4j" in s.neo_uri.lower()

    def test_cors_origins_list(self) -> None:
        s = get_settings()
        assert isinstance(s.cors_origins_list, list)
        assert all(isinstance(o, str) for o in s.cors_origins_list)


class TestConfigSingleton:
    def test_get_settings_same_instance(self) -> None:
        a = get_settings()
        b = get_settings()
        assert a is b

import json

from dell_ai.mcp.client import _resolve_token
from dell_ai.mcp.config import (
    MCPConfig,
    load_config,
)


def test_mcp_config_defaults():
    cfg = MCPConfig()
    assert cfg.transport == "stdio"
    assert cfg.host == "127.0.0.1"
    assert cfg.port == 8000
    assert cfg.allow_destructive is False
    assert cfg.capabilities.tools is True
    assert cfg.capabilities.resources is True
    assert cfg.capabilities.prompts is True


def test_mcp_config_ignores_unknown_fields():
    cfg = MCPConfig(unknown_field="ignored")
    assert not hasattr(cfg, "unknown_field")


def test_load_config_from_path(tmp_path):
    config_file = tmp_path / "mcp.json"
    config_file.write_text(json.dumps({"transport": "streamable-http", "port": 3000}))
    cfg = load_config(config_file)
    assert cfg.transport == "streamable-http"
    assert cfg.port == 3000


def test_load_config_local_overrides_global(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "dell_ai.mcp.config.get_global_mcp_path", lambda: tmp_path / "global.json"
    )
    monkeypatch.setattr(
        "dell_ai.mcp.config.get_local_mcp_path", lambda: tmp_path / "local.json"
    )
    (tmp_path / "global.json").write_text(json.dumps({"host": "0.0.0.0", "port": 1111}))
    (tmp_path / "local.json").write_text(json.dumps({"port": 2222}))
    cfg = load_config()
    assert cfg.host == "0.0.0.0"
    assert cfg.port == 2222


def test_resolve_token_env(monkeypatch):
    monkeypatch.setenv("TEST_HF_TOKEN", "abc123")
    assert _resolve_token("env:TEST_HF_TOKEN") == "abc123"
    assert _resolve_token("TEST_HF_TOKEN") == "abc123"
    assert _resolve_token("env:MISSING") is None


def test_resolve_token_file(tmp_path):
    token_file = tmp_path / "token.txt"
    token_file.write_text("filetoken\n")
    assert _resolve_token(f"file:{token_file}") == "filetoken"
    assert _resolve_token("file:/nonexistent") is None

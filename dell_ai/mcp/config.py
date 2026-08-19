import json
from pathlib import Path
from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, Field

LOCAL_MCP_FILENAME = ".dell-ai-mcp.json"


class CapabilitiesConfig(BaseModel):
    tools: bool = True
    resources: bool = True
    prompts: bool = True


class MCPConfig(BaseModel):
    transport: Literal["stdio", "streamable-http", "sse"] = "stdio"
    host: str = "127.0.0.1"
    port: int = 8000
    streamable_http_path: str = "/mcp"
    stateless_http: bool = True
    json_response: bool = False
    allow_destructive: bool = False
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    hf_token_source: Optional[str] = None
    api_base_url: Optional[str] = None
    capabilities: CapabilitiesConfig = Field(default_factory=CapabilitiesConfig)

    model_config = {"extra": "ignore"}


def get_global_mcp_path() -> Path:
    return Path.home() / ".config" / "dell-ai" / "mcp.json"


def get_local_mcp_path() -> Path:
    return Path.cwd() / LOCAL_MCP_FILENAME


def _load_config_file(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def load_config(config_path: Optional[Path] = None) -> MCPConfig:
    if config_path:
        data = _load_config_file(config_path)
        return MCPConfig(**data)
    data = _load_config_file(get_global_mcp_path())
    data.update(_load_config_file(get_local_mcp_path()))
    return MCPConfig(**data)

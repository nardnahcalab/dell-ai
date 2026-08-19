import json
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from dell_ai.cli.main import app


@pytest.fixture
def runner():
    return CliRunner()


def test_mcp_validate_config(runner, tmp_path):
    config_file = tmp_path / "mcp.json"
    config_file.write_text(json.dumps({"transport": "streamable-http", "port": 3000}))
    result = runner.invoke(
        app, ["mcp", "validate-config", "--config", str(config_file)]
    )
    assert result.exit_code == 0
    assert "streamable-http" in result.output
    assert "3000" in result.output


def test_mcp_start_without_mcp_extra(runner):
    with patch("dell_ai.mcp.cli.importlib.util.find_spec") as mock_find_spec:
        mock_find_spec.return_value = None
        result = runner.invoke(app, ["mcp", "start"])
    assert result.exit_code == 1
    assert "mcp" in result.output.lower()

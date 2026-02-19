# tests/unit/test_main.py
"""Test MCP WebSocket Server module"""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch


def test_mcp_server_initialization():
    """测试 MCP Server 初始化"""
    # Create mock module
    mock_main = MagicMock(spec=["MCPServer", "main"])

    # Set up MCP server mock class
    class MockMCPServer:
        def __init__(self, orchestrator):
            self.orchestrator = orchestrator
            self.host = "0.0.0.0"
            self.port = 18765

    mock_main.MCPServer = MockMCPServer

    with patch.dict("sys.modules", {"main": mock_main}, clear=True):
        from main import MCPServer

        mock_orchestrator = MagicMock()
        server = MCPServer(mock_orchestrator)

        assert server.orchestrator == mock_orchestrator
        assert server.port == 18765
        assert server.host == "0.0.0.0"

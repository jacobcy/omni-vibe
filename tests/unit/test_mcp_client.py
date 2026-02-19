"""
MCP Client tests
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.mcp_client import MCPClient


class TestMCPClient:
    """Test MCP client functionality"""

    @pytest.mark.asyncio
    async def test_connect_to_server(self):
        """Should connect to MCP server successfully"""
        client = MCPClient("ws://127.0.0.1:18789")

        with patch("src.mcp_client.websocket_client") as mock_ws:
            mock_ws.return_value.__aenter__ = AsyncMock(return_value=(AsyncMock(), AsyncMock()))

            with patch("src.mcp_client.ClientSession") as mock_session:
                mock_session.return_value.__aenter__ = AsyncMock()
                mock_session.return_value.initialize = AsyncMock()

                await client.connect()

                assert client.session is not None
                mock_session.return_value.initialize.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_tools(self):
        """Should retrieve list of available tools"""
        client = MCPClient("ws://127.0.0.1:18789")

        # Create mock tools with proper spec
        tool1 = MagicMock()
        tool1.name = "tool1"
        tool1.description = "Tool 1"
        tool2 = MagicMock()
        tool2.name = "tool2"
        tool2.description = "Tool 2"

        with patch("src.mcp_client.websocket_client") as mock_ws:
            mock_ws.return_value.__aenter__ = AsyncMock(return_value=(AsyncMock(), AsyncMock()))

            with patch("src.mcp_client.ClientSession") as mock_session:
                mock_session.return_value.__aenter__ = AsyncMock()
                mock_session.return_value.initialize = AsyncMock()
                mock_session.return_value.list_tools = AsyncMock(
                    return_value=MagicMock(tools=[tool1, tool2])
                )

                await client.connect()
                tools = await client.list_tools()

                assert len(tools) == 2
                assert tools[0].name == "tool1"
                assert tools[1].name == "tool2"

    @pytest.mark.asyncio
    async def test_call_tool(self):
        """Should call a tool with parameters and return result"""
        client = MCPClient("ws://127.0.0.1:18789")

        with patch("src.mcp_client.websocket_client") as mock_ws:
            mock_ws.return_value.__aenter__ = AsyncMock(return_value=(AsyncMock(), AsyncMock()))

            with patch("src.mcp_client.ClientSession") as mock_session:
                mock_session.return_value.__aenter__ = AsyncMock()
                mock_session.return_value.initialize = AsyncMock()
                mock_session.return_value.call_tool = AsyncMock(
                    return_value=MagicMock(content="Tool execution result")
                )

                await client.connect()
                result = await client.call_tool("test_tool", param1="value1")

                assert result.content == "Tool execution result"
                # MCP client passes kwargs as arguments dict
                mock_session.return_value.call_tool.assert_called_once_with(
                    "test_tool", arguments={'param1': 'value1'}
                )

    @pytest.mark.asyncio
    async def test_disconnect(self):
        """Should disconnect from server cleanly"""
        client = MCPClient("ws://127.0.0.1:18789")

        with patch("src.mcp_client.websocket_client") as mock_ws:
            mock_ws.return_value.__aenter__ = AsyncMock(return_value=(AsyncMock(), AsyncMock()))
            mock_ws.return_value.__aexit__ = AsyncMock()

            with patch("src.mcp_client.ClientSession") as mock_session:
                mock_session.return_value.__aenter__ = AsyncMock()
                mock_session.return_value.__aexit__ = AsyncMock()
                mock_session.return_value.initialize = AsyncMock()

                await client.connect()
                await client.disconnect()

                mock_session.return_value.__aexit__.assert_called_once()
                mock_ws.return_value.__aexit__.assert_called_once()

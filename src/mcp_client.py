"""
MCP Client module

功能:
- 連接到 MCP Server (OpenClaw, Claude Code 等)
- 列出可用工具
- 調用工具並獲取結果
"""

from typing import Any, Dict, List, Optional
from mcp import ClientSession
from mcp.client.websocket import websocket_client


class MCPClient:
    """MCP 客戶端類"""

    def __init__(self, server_url: str):
        """
        初始化 MCP 客戶端

        Args:
            server_url: MCP Server URL (e.g., ws://127.0.0.1:18789)
        """
        self.server_url = server_url
        self.session: Optional[ClientSession] = None
        self._connection_context = None

    async def connect(self):
        """連接到 MCP Server"""
        # 創建 WebSocket 連接
        self._connection_context = websocket_client(self.server_url)
        # 進入異步上下文管理器
        read_stream, write_stream = await self._connection_context.__aenter__()

        # 創建並初始化會話
        self.session = ClientSession(read_stream, write_stream)
        await self.session.__aenter__()
        await self.session.initialize()

    async def list_tools(self) -> List[Any]:
        """
        列出所有可用工具

        Returns:
            工具列表
        """
        if not self.session:
            raise RuntimeError("Not connected to server")

        response = await self.session.list_tools()
        return response.tools

    async def call_tool(self, tool_name: str, **kwargs) -> Any:
        """
        調用指定工具

        Args:
            tool_name: 工具名稱
            **kwargs: 工具參數

        Returns:
            工具執行結果
        """
        if not self.session:
            raise RuntimeError("Not connected to server")

        result = await self.session.call_tool(tool_name, arguments=kwargs)
        return result

    async def disconnect(self):
        """斷開連接"""
        if self.session:
            await self.session.__aexit__(None, None, None)
            self.session = None

        if self._connection_context:
            await self._connection_context.__aexit__(None, None, None)
            self._connection_context = None

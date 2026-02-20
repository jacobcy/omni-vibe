# src/main.py
"""
Omni-Orchestrator MCP WebSocket Server

启动 MCP WebSocket 服务，监听 18765 端口，
接收客户端连接并处理任务。
"""

import asyncio
import os
import logging

from websockets.server import serve
from src.config import Config
from src.orchestrator import Orchestrator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MCPServer:
    """MCP WebSocket 服务器"""

    def __init__(self, orchestrator):
        """
        Args:
            orchestrator: Orchestrator 实例
        """

        self.orchestrator = orchestrator
        self.host = os.getenv("OMNI_HOST", "0.0.0.0")
        self.port = int(os.getenv("OMNI_PORT", "18765"))

    async def handle_client(self, websocket):
        """处理客户端连接"""
        client_id = websocket.remote_address
        logger.info(f"客户端连接: {client_id}")

        try:
            async for message in websocket:
                logger.debug(f"收到消息: {message[:100] if len(message) > 100 else message}")
                response = await self.orchestrator.process_mcp_message(message)
                await websocket.send(response)
        except Exception as e:
            logger.error(f"客户端错误: {e}")
        finally:
            logger.info(f"客户端断开: {client_id}")

    async def start(self):
        """启动服务"""
        logger.info(f"启动 MCP Server: {self.host}:{self.port}")

        async with serve(self.handle_client, self.host, self.port) as server:
            logger.info(f"服务已启动，等待连接...")
            await server.serve_forever()


async def main():
    """主入口"""
    config = Config()
    orchestrator = Orchestrator(config)

    server = MCPServer(orchestrator)
    await server.start()


if __name__ == "__main__":
    asyncio.run(main())

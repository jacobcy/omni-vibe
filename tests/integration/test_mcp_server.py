# tests/integration/test_mcp_server.py
"""Test MCP Server integration"""
import pytest
import json
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_process_mcp_ping_message():
    """测试处理 MCP ping 消息"""
    with patch("src.orchestrator.Config"):
        from src.orchestrator import Orchestrator

        orchestrator = Orchestrator()
        message = json.dumps({"method": "ping"})
        response = json.loads(await orchestrator.process_mcp_message(message))

        assert response["result"] == "pong"


@pytest.mark.asyncio
async def test_process_mcp_create_task():
    """测试处理 create_task 消息"""
    with patch("src.orchestrator.Config"):
        from src.orchestrator import Orchestrator

        orchestrator = Orchestrator()
        orchestrator.process_task = AsyncMock(return_value={"task_id": "test-123", "status": "completed"})

        message = json.dumps({
            "method": "create_task",
            "params": {"description": "Test task"}
        })
        response = json.loads(await orchestrator.process_mcp_message(message))

        assert "result" in response
        assert response["result"]["task_id"] == "test-123"


@pytest.mark.asyncio
async def test_process_mcp_invalid_json():
    """测试无效 JSON"""
    with patch("src.orchestrator.Config"):
        from src.orchestrator import Orchestrator

        orchestrator = Orchestrator()
        message = "not valid json"
        response = json.loads(await orchestrator.process_mcp_message(message))

        assert "error" in response

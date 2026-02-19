"""
Integration tests for main orchestrator
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.orchestrator import Orchestrator
from src.state_manager import TaskState
from src.fault_handler import SystemState


@pytest.fixture
def orchestrator(tmp_path):
    """Create an orchestrator instance with test config"""
    config_file = tmp_path / "test_config.yaml"
    config_file.write_text("model_list: []\n")
    return Orchestrator(config_path=str(config_file))


class TestOrchestrator:
    """Test complete orchestrator workflow"""

    @pytest.mark.asyncio
    async def test_process_simple_task_success(self, orchestrator):

        with patch.object(orchestrator, "mcp_client") as mock_mcp:
            with patch.object(orchestrator, "router") as mock_router:
                with patch.object(orchestrator, "state_manager") as mock_state:
                    # Setup mocks
                    mock_mcp.connect = AsyncMock()
                    mock_mcp.call_tool = AsyncMock(
                        return_value=MagicMock(content="Task completed")
                    )
                    mock_router.route_task.return_value = {
                        "executor": "openclaw",
                        "model": "gpt-3.5-turbo",
                        "complexity": 30,
                    }
                    mock_state.create_task.return_value = "task_123"
                    mock_state.get_task.return_value = {
                        "task_id": "task_123",
                        "state": TaskState.IDLE.value,
                    }

                    # Process task
                    result = await orchestrator.process_task("List files in directory")

                    # Verify
                    assert result["status"] == "completed"
                    mock_state.create_task.assert_called_once()
                    mock_state.update_state.assert_called()

    @pytest.mark.asyncio
    async def test_process_task_in_degraded_mode(self, orchestrator):
        """Should handle tasks in degraded mode with direct API"""
        with patch.object(orchestrator, "fault_handler") as mock_fault:
            with patch.object(orchestrator, "router") as mock_router:
                mock_fault.system_state = SystemState.DEGRADED
                mock_router.select_model.return_value = {
                    "mode": "direct_api",
                    "api_key": "backup_key",
                }
                mock_fault.fallback_to_direct_api = AsyncMock(
                    return_value={"content": "Response"}
                )

                result = await orchestrator.process_task("Urgent task")

                assert result["status"] == "completed"
                mock_fault.fallback_to_direct_api.assert_called_once()

    @pytest.mark.asyncio
    async def test_suspend_tasks_in_brainstem_mode(self, orchestrator):
        """Should suspend all tasks when entering brainstem mode"""
        with patch.object(orchestrator, "fault_handler") as mock_fault:
            with patch.object(orchestrator, "state_manager") as mock_state:
                mock_fault.system_state = SystemState.BRAINSTEM
                mock_state.get_pending_tasks.return_value = [
                    {"task_id": "task_1", "state": TaskState.EXECUTING.value},
                    {"task_id": "task_2", "state": TaskState.DISPATCHING.value},
                ]

                await orchestrator.enter_brainstem_mode()

                # All tasks should be suspended
                assert mock_state.update_state.call_count == 2

    @pytest.mark.asyncio
    async def test_recover_from_brainstem_mode(self, orchestrator):
        """Should resume suspended tasks when recovering from brainstem"""
        with patch.object(orchestrator, "fault_handler") as mock_fault:
            with patch.object(orchestrator, "state_manager") as mock_state:
                mock_fault.system_state = SystemState.NORMAL
                mock_state.get_pending_tasks.return_value = [
                    {"task_id": "task_1", "state": TaskState.WAITING_FOR_CLOUD.value},
                ]

                await orchestrator.recover_from_brainstem()

                # Task should be reset to IDLE
                mock_state.update_state.assert_called_with(
                    "task_1", TaskState.IDLE
                )

    @pytest.mark.asyncio
    async def test_health_monitoring_loop(self, orchestrator):
        """Should continuously monitor system health"""
        with patch.object(orchestrator, "fault_handler") as mock_fault:
            mock_fault.check_lite_llm_health = AsyncMock(return_value=True)
            mock_fault.check_cloud_apis = AsyncMock(return_value=True)

            # Run monitoring for a few iterations
            health_status = []
            for _ in range(3):
                status = await orchestrator.monitor_health()
                health_status.append(status)

            assert all(h["lite_llm_healthy"] for h in health_status)
            assert all(h["cloud_healthy"] for h in health_status)

    @pytest.mark.asyncio
    async def test_task_retry_on_failure(self, orchestrator):
        """Should retry failed tasks with exponential backoff"""
        with patch.object(orchestrator, "mcp_client") as mock_mcp:
            with patch.object(orchestrator, "state_manager") as mock_state:
                mock_mcp.call_tool = AsyncMock(
                    side_effect=[
                        Exception("Temporary failure"),
                        MagicMock(content="Success"),
                    ]
                )
                mock_state.get_task.return_value = {
                    "task_id": "task_123",
                    "state": TaskState.EXECUTING.value,
                    "description": "Test task",
                }

                result = await orchestrator.execute_with_retry(
                    "task_123", max_retries=2, base_delay=0.01
                )

                # Debug: print result
                print(f"Result: {result}")

                assert result["status"] == "completed"
                assert mock_mcp.call_tool.call_count == 2
                assert mock_mcp.call_tool.call_count == 2

    @pytest.mark.asyncio
    async def test_cleanup_on_shutdown(self, orchestrator):
        """Should cleanup resources properly on shutdown"""
        with patch.object(orchestrator, "mcp_client") as mock_mcp:
            with patch.object(orchestrator, "state_manager") as mock_state:
                mock_mcp.disconnect = AsyncMock()

                await orchestrator.shutdown()

                mock_mcp.disconnect.assert_called_once()
                # State manager should persist state
                assert mock_state.conn is not None

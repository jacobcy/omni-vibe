"""
Router decision tests
"""

import pytest
from unittest.mock import MagicMock
from src.router_decision import RouterDecision
from src.state_manager import TaskState


class TestRouterDecision:
    """Test routing decision logic"""

    def test_select_executor_for_coding_task(self):
        """Should select Claude Code for programming tasks"""
        router = RouterDecision(mcp_client=MagicMock(), lite_llm_router=MagicMock())

        task = {
            "description": "Implement a REST API endpoint",
            "type": "programming"
        }

        executor = router.select_executor(task)

        assert executor == "claude_code"

    def test_select_executor_for_general_task(self):
        """Should select OpenClaw for general tasks"""
        router = RouterDecision(mcp_client=MagicMock(), lite_llm_router=MagicMock())

        task = {
            "description": "Search for information about Python",
            "type": "general"
        }

        executor = router.select_executor(task)

        assert executor == "openclaw"

    def test_select_executor_for_cloud_task(self):
        """Should select Moltworker for 24/7 tasks"""
        router = RouterDecision(mcp_client=MagicMock(), lite_llm_router=MagicMock())

        task = {
            "description": "Monitor server health continuously",
            "type": "24/7"
        }

        executor = router.select_executor(task)

        assert executor == "moltworker"

    def test_select_model_normal_mode(self):
        """Should use LiteLLM routing in normal mode"""
        mock_router = MagicMock()
        mock_router.route.return_value = {"model": "gpt-4", "provider": "openai"}

        router = RouterDecision(mcp_client=MagicMock(), lite_llm_router=mock_router)

        task = {"description": "Complex analysis task"}
        model = router.select_model(task, mode="normal")

        assert model["provider"] == "openai"
        mock_router.route.assert_called_once()

    def test_select_model_degraded_mode(self):
        """Should use direct API with backup key in degraded mode"""
        router = RouterDecision(
            mcp_client=MagicMock(),
            lite_llm_router=MagicMock(),
            backup_api_key="backup_key_123"
        )

        task = {"description": "Urgent task during degradation"}
        model = router.select_model(task, mode="degraded")

        assert model["mode"] == "direct_api"
        assert model["api_key"] == "backup_key_123"

    def test_select_model_brainstem_mode(self):
        """Should not execute tasks in brainstem mode"""
        router = RouterDecision(mcp_client=MagicMock(), lite_llm_router=MagicMock())

        task = {"description": "Any task"}
        model = router.select_model(task, mode="brainstem")

        assert model is None

    def test_calculate_task_complexity_simple(self):
        """Should identify simple tasks"""
        router = RouterDecision(mcp_client=MagicMock(), lite_llm_router=MagicMock())

        simple_task = {
            "description": "List files in directory",
            "conversation_history": []
        }

        complexity = router.calculate_complexity(simple_task)

        assert complexity < 50  # Simple threshold

    def test_calculate_task_complexity_complex(self):
        """Should identify complex tasks"""
        router = RouterDecision(mcp_client=MagicMock(), lite_llm_router=MagicMock())

        complex_task = {
            "description": "Implement a distributed caching system with fault tolerance",
            "conversation_history": ["msg1", "msg2", "msg3", "msg4", "msg5", "msg6"]
        }

        complexity = router.calculate_complexity(complex_task)

        assert complexity >= 50  # Complex threshold

    def test_route_to_lightweight_model_for_simple_task(self):
        """Should route to lightweight model for simple tasks"""
        mock_router = MagicMock()
        mock_router.get_lightweight_model.return_value = "gpt-3.5-turbo"

        router = RouterDecision(mcp_client=MagicMock(), lite_llm_router=mock_router)

        task = {"description": "What time is it?"}
        route = router.route_task(task)

        assert route["model"] == "gpt-3.5-turbo"
        mock_router.get_lightweight_model.assert_called_once()

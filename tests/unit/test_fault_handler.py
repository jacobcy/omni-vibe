"""
Fault handler tests
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.fault_handler import FaultHandler, SystemState


class TestFaultHandler:
    """Test fault handling and system recovery"""

    @pytest.mark.asyncio
    async def test_detect_lite_llm_health_success(self):
        """Should detect LiteLLM is healthy"""
        handler = FaultHandler(
            lite_llm_url="http://localhost:4000",
            github_key="test_key"
        )

        with patch("src.fault_handler.httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.elapsed.total_seconds.return_value = 0.5

            mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_client.return_value)
            mock_client.return_value.get = AsyncMock(return_value=mock_response)

            is_healthy = await handler.check_lite_llm_health()

            assert is_healthy is True
            assert handler.consecutive_failures == 0

    @pytest.mark.asyncio
    async def test_detect_lite_llm_timeout(self):
        """Should detect LiteLLM timeout as failure"""
        handler = FaultHandler(
            lite_llm_url="http://localhost:4000",
            github_key="test_key"
        )

        with patch("src.fault_handler.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__ = AsyncMock()
            mock_client.return_value.get = AsyncMock(side_effect=Exception("Timeout"))

            is_healthy = await handler.check_lite_llm_health()

            assert is_healthy is False
            assert handler.consecutive_failures == 1

    @pytest.mark.asyncio
    async def test_trigger_degradation_mode(self):
        """Should trigger degradation mode after consecutive failures"""
        handler = FaultHandler(
            lite_llm_url="http://localhost:4000",
            github_key="test_key",
            consecutive_failures_threshold=2
        )

        # Simulate 2 consecutive failures
        with patch("src.fault_handler.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__ = AsyncMock()
            mock_client.return_value.get = AsyncMock(side_effect=Exception("Failed"))

            await handler.check_lite_llm_health()
            await handler.check_lite_llm_health()

        assert handler.system_state == SystemState.DEGRADED

    @pytest.mark.asyncio
    async def test_enter_brainstem_mode_on_cloud_failure(self):
        """Should enter brainstem mode when cloud APIs fail"""
        handler = FaultHandler(
            lite_llm_url="http://localhost:4000",
            github_key="test_key"
        )

        # Simulate cloud API failure
        with patch("src.fault_handler.httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 503  # Service Unavailable
            mock_client.return_value.__aenter__ = AsyncMock()
            mock_client.return_value.get = AsyncMock(return_value=mock_response)
            mock_client.return_value.post = AsyncMock(return_value=mock_response)

            # Trigger 3 consecutive cloud failures
            for _ in range(3):
                cloud_healthy = await handler.check_cloud_apis()
                assert cloud_healthy is False

        assert handler.system_state == SystemState.BRAINSTEM

    @pytest.mark.asyncio
    async def test_fallback_to_direct_api(self):
        """Should use direct API with backup key in degraded mode"""
        handler = FaultHandler(
            lite_llm_url="http://localhost:4000",
            github_key="backup_key_123"
        )

        handler.system_state = SystemState.DEGRADED

        with patch("src.fault_handler.httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"content": "response"}
            mock_response.raise_for_status = MagicMock()

            mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_client.return_value)
            mock_client.return_value.post = AsyncMock(return_value=mock_response)

            result = await handler.fallback_to_direct_api(
                messages=[{"role": "user", "content": "test"}]
            )

            assert result is not None
            # Verify backup key was used
            call_args = mock_client.return_value.post.call_args
            headers = call_args[1]["headers"]
            assert "backup_key_123" in headers["x-api-key"]

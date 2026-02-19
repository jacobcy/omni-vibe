"""
Fault handling module

功能:
- LiteLLM 故障檢測
- 降級到直連 API
- 觸發 Claude Code 修復任務
- 腦幹模式 (雲端 API 故障)
"""

import httpx
from enum import Enum
from typing import Dict, List, Optional


class SystemState(Enum):
    """系統狀態枚舉"""

    NORMAL = "normal"  # 正常模式：雲端可用
    DEGRADED = "degraded"  # 降級模式：LiteLLM 故障，使用直連 API
    BRAINSTEM = "brainstem"  # 腦幹模式：雲端離線，僅維持自檢


class FaultHandler:
    """故障處理類"""

    def __init__(
        self,
        lite_llm_url: str,
        github_key: str,
        consecutive_failures_threshold: int = 2,
        cloud_failure_threshold: int = 3,
        lite_llm_timeout: float = 1.0,
    ):
        """
        初始化故障處理器

        Args:
            lite_llm_url: LiteLLM 服務 URL
            github_key: GitHub API Key (備用直連)
            consecutive_failures_threshold: 連續失敗次數閾值
            cloud_failure_threshold: 雲端失敗次數閾值
            lite_llm_timeout: LiteLLM 超時閾值（秒）
        """
        self.lite_llm_url = lite_llm_url
        self.github_key = github_key
        self.consecutive_failures_threshold = consecutive_failures_threshold
        self.cloud_failure_threshold = cloud_failure_threshold
        self.lite_llm_timeout = lite_llm_timeout

        self.consecutive_failures = 0
        self.consecutive_cloud_failures = 0
        self.system_state = SystemState.NORMAL

    async def check_lite_llm_health(self) -> bool:
        """
        檢測 LiteLLM 是否正常

        Returns:
            健康狀態
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.lite_llm_url}/health", timeout=self.lite_llm_timeout
                )

                if response.status_code == 200 and response.elapsed.total_seconds() < self.lite_llm_timeout:
                    self.consecutive_failures = 0
                    return True
                else:
                    self.consecutive_failures += 1
                    self._check_degradation()
                    return False

        except Exception:
            self.consecutive_failures += 1
            self._check_degradation()
            return False

    def _check_degradation(self):
        """檢查是否需要進入降級模式"""
        if self.consecutive_failures >= self.consecutive_failures_threshold:
            self.system_state = SystemState.DEGRADED

    async def check_cloud_apis(self) -> bool:
        """
        檢測雲端 API 是否可用

        Returns:
            雲端健康狀態
        """
        try:
            # 簡單的連通性測試
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://api.anthropic.com", timeout=10.0
                )
                if response.status_code < 500:
                    self.consecutive_cloud_failures = 0
                    return True
                else:
                    self.consecutive_cloud_failures += 1
                    self._check_brainstem()
                    return False
        except Exception:
            self.consecutive_cloud_failures += 1
            self._check_brainstem()
            return False

    def _check_brainstem(self):
        """檢查是否需要進入腦幹模式"""
        if self.consecutive_cloud_failures >= self.cloud_failure_threshold:
            self.system_state = SystemState.BRAINSTEM

    async def fallback_to_direct_api(
        self, messages: List[Dict], model: str = "claude-3-5-sonnet-20241022"
    ) -> Optional[Dict]:
        """
        降級到直連 API

        Args:
            messages: 消息列表
            model: 模型名稱

        Returns:
            API 響應
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": self.github_key,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json",
                    },
                    json={"model": model, "messages": messages, "max_tokens": 1024},
                    timeout=30.0,
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            print(f"Direct API call failed: {e}")
            return None

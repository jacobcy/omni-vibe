"""
Main Orchestrator module

功能:
- 整合所有模塊的協調器
- 處理完整的任務生命週期
- 健康監控與故障恢復
"""

import asyncio
from typing import Dict, Optional
from unittest.mock import MagicMock
from src.config import Config
from src.state_manager import StateManager, TaskState
from src.mcp_client import MCPClient
from src.fault_handler import FaultHandler, SystemState
from src.router_decision import RouterDecision


class Orchestrator:
    """主協調器類"""

    def __init__(self, config_path: str = "config.yaml"):
        """
        初始化協調器

        Args:
            config_path: 配置文件路徑
        """
        self.config = Config(config_path)

        # 初始化各個模塊
        self.state_manager = StateManager()
        self.mcp_client = MCPClient(
            server_url=self.config.config.get("mcp_server_url", "ws://127.0.0.1:18789")
        )
        self.fault_handler = FaultHandler(
            lite_llm_url=self.config.config.get("lite_llm_url", "http://localhost:4000"),
            github_key=self.config.config.get("github_key"),
        )
        self.router = RouterDecision(
            mcp_client=self.mcp_client,
            lite_llm_router=self._create_lite_llm_router(),
            backup_api_key=self.config.config.get("github_key"),
        )

    def _create_lite_llm_router(self):
        """創建 LiteLLM 路由器（簡化版本）"""
        # 這裡返回一個模擬的路由器
        # 實際實現中會連接到真實的 LiteLLM
        return MagicMock(
            route=lambda task: {"model": "gpt-4", "provider": "openai"},
            get_lightweight_model=lambda: "gpt-3.5-turbo",
            get_model=lambda: "gpt-4",
        )

    async def process_task(self, description: str) -> Dict:
        """
        處理任務的完整流程

        Args:
            description: 任務描述

        Returns:
            處理結果
        """
        # 1. 創建任務
        task_id = self.state_manager.create_task(description)

        try:
            # 2. 檢查系統狀態
            if self.fault_handler.system_state == SystemState.BRAINSTEM:
                self.state_manager.update_state(task_id, TaskState.WAITING_FOR_CLOUD)
                return {
                    "task_id": task_id,
                    "status": "suspended",
                    "message": "Cloud unavailable, task suspended",
                }

            # 3. 路由決策
            self.state_manager.update_state(task_id, TaskState.DISPATCHING)
            task = {"description": description, "conversation_history": []}
            route = self.router.route_task(task)

            # 4. 執行任務
            self.state_manager.update_state(task_id, TaskState.EXECUTING)

            # 根據系統狀態選擇執行方式
            if self.fault_handler.system_state == SystemState.DEGRADED:
                # 降級模式：使用直連 API
                result = await self.fault_handler.fallback_to_direct_api(
                    messages=[{"role": "user", "content": description}]
                )
            else:
                # 正常模式：通過 MCP 調用執行器
                await self.mcp_client.connect()
                result = await self.mcp_client.call_tool(
                    "execute_task",
                    executor=route["executor"],
                    model=route["model"],
                    description=description,
                )

            # 5. 完成任務
            self.state_manager.update_state(task_id, TaskState.COMPLETED)
            return {
                "task_id": task_id,
                "status": "completed",
                "result": result.content if hasattr(result, "content") else result,
            }

        except Exception as e:
            self.state_manager.update_state(task_id, TaskState.FAILED)
            return {"task_id": task_id, "status": "failed", "error": str(e)}

    async def enter_brainstem_mode(self):
        """進入腦幹模式"""
        self.fault_handler.system_state = SystemState.BRAINSTEM

        # 掛起所有正在執行的任務
        pending_tasks = self.state_manager.get_pending_tasks()
        for task in pending_tasks:
            if task["state"] in [TaskState.EXECUTING.value, TaskState.DISPATCHING.value]:
                self.state_manager.update_state(
                    task["task_id"], TaskState.WAITING_FOR_CLOUD
                )

    async def recover_from_brainstem(self):
        """從腦幹模式恢復"""
        self.fault_handler.system_state = SystemState.NORMAL

        # 恢復所有掛起的任務
        pending_tasks = self.state_manager.get_pending_tasks()
        for task in pending_tasks:
            if task["state"] == TaskState.WAITING_FOR_CLOUD.value:
                self.state_manager.update_state(task["task_id"], TaskState.IDLE)

    async def monitor_health(self) -> Dict:
        """
        監控系統健康狀態

        Returns:
            健康狀態字典
        """
        lite_llm_healthy = await self.fault_handler.check_lite_llm_health()
        cloud_healthy = await self.fault_handler.check_cloud_apis()

        return {
            "lite_llm_healthy": lite_llm_healthy,
            "cloud_healthy": cloud_healthy,
            "system_state": self.fault_handler.system_state.value,
        }

    async def execute_with_retry(
        self, task_id: str, max_retries: int = 3, base_delay: float = 1.0
    ) -> Dict:
        """
        帶重試的任務執行

        Args:
            task_id: 任務 ID
            max_retries: 最大重試次數
            base_delay: 基礎延遲（秒）

        Returns:
            執行結果
        """
        task = self.state_manager.get_task(task_id)
        if not task:
            return {"status": "failed", "error": "Task not found"}

        for attempt in range(max_retries):
            try:
                result = await self.mcp_client.call_tool(
                    "execute_task", description=task["description"]
                )

                self.state_manager.update_state(task_id, TaskState.COMPLETED)
                return {
                    "status": "completed",
                    "result": result.content if hasattr(result, "content") else result,
                }

            except Exception as e:
                if attempt < max_retries - 1:
                    # 指數退避
                    delay = base_delay * (2**attempt)
                    await asyncio.sleep(delay)
                else:
                    self.state_manager.update_state(task_id, TaskState.FAILED)
                    return {"status": "failed", "error": str(e)}

    async def shutdown(self):
        """關閉協調器並清理資源"""
        # 斷開 MCP 連接
        if self.mcp_client.session:
            await self.mcp_client.disconnect()

        # 保持狀態管理器連接（用於持久化）
        # 實際實現中可能需要顯式關閉

"""
Router decision module

功能:
- 根據任務特徵選擇執行器
- 根據成本/質量選擇模型
- 處理降級模式下的路由
"""

from typing import Dict, Optional, Any


class RouterDecision:
    """路由決策類"""

    # 執行器類型
    EXECUTOR_CLAUDE_CODE = "claude_code"
    EXECUTOR_OPENCLAW = "openclaw"
    EXECUTOR_MOLTWORKER = "moltworker"

    # 任務複雜度閾值
    COMPLEXITY_THRESHOLD = 50

    def __init__(
        self,
        mcp_client: Any,
        lite_llm_router: Any,
        backup_api_key: Optional[str] = None,
    ):
        """
        初始化路由決策器

        Args:
            mcp_client: MCP 客戶端實例
            lite_llm_router: LiteLLM 路由器實例
            backup_api_key: 備用 API Key（降級模式使用）
        """
        self.mcp_client = mcp_client
        self.lite_llm_router = lite_llm_router
        self.backup_api_key = backup_api_key

    def select_executor(self, task: Dict) -> str:
        """
        選擇執行器

        Args:
            task: 任務字典

        Returns:
            執行器名稱
        """
        task_type = task.get("type", "general")

        # 編程任務 → Claude Code
        if task_type == "programming" or self._is_programming_task(task):
            return self.EXECUTOR_CLAUDE_CODE

        # 24/7 任務 → Moltworker
        if task_type == "24/7":
            return self.EXECUTOR_MOLTWORKER

        # 通用任務 → OpenClaw
        return self.EXECUTOR_OPENCLAW

    def _is_programming_task(self, task: Dict) -> bool:
        """判斷是否為編程任務"""
        programming_keywords = [
            "implement",
            "code",
            "debug",
            "refactor",
            "API",
            "function",
            "class",
            "bug",
            "fix",
        ]
        description = task.get("description", "").lower()
        return any(keyword in description for keyword in programming_keywords)

    def select_model(self, task: Dict, mode: str = "normal") -> Optional[Dict]:
        """
        選擇模型

        Args:
            task: 任務字典
            mode: 運行模式 (normal, degraded, brainstem)

        Returns:
            模型配置字典
        """
        if mode == "brainstem":
            # 腦幹模式不執行任務
            return None

        if mode == "degraded":
            # 降級模式：直連 API
            return {
                "mode": "direct_api",
                "api_key": self.backup_api_key,
                "provider": "anthropic",
                "model": "claude-3-5-sonnet-20241022",
            }

        # 正常模式：LiteLLM 路由
        return self.lite_llm_router.route(task)

    def calculate_complexity(self, task: Dict) -> int:
        """
        計算任務複雜度

        Args:
            task: 任務字典

        Returns:
            複雜度分數 (0-100)
        """
        score = 0
        description = task.get("description", "")
        history = task.get("conversation_history", [])

        # 消息長度
        if len(description) > 100:
            score += 30
        elif len(description) > 50:
            score += 15

        # 對話歷史長度
        if len(history) > 5:
            score += 30
        elif len(history) > 2:
            score += 15

        # 簡單關鍵詞
        simple_keywords = ["list", "show", "what", "when", "how many"]
        for keyword in simple_keywords:
            if keyword in description.lower():
                score -= 20

        # 複雜關鍵詞
        complex_keywords = [
            "implement",
            "design",
            "architecture",
            "distributed",
            "algorithm",
            "optimize",
        ]
        for keyword in complex_keywords:
            if keyword in description.lower():
                score += 25

        return max(0, min(100, score + 50))  # 標準化到 0-100

    def route_task(self, task: Dict) -> Dict:
        """
        完整路由決策

        Args:
            task: 任務字典

        Returns:
            路由配置
        """
        complexity = self.calculate_complexity(task)
        executor = self.select_executor(task)

        # 簡單任務使用輕量級模型
        if complexity < self.COMPLEXITY_THRESHOLD:
            model = self.lite_llm_router.get_lightweight_model()
        else:
            model = self.lite_llm_router.get_model()

        return {
            "executor": executor,
            "model": model,
            "complexity": complexity,
        }

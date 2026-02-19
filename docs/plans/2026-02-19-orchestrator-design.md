# Omni-Orchestrator 实施设计文档

> **日期**: 2026-02-19
> **版本**: v1.0
> **基于**: [litellm-vibe-router](https://github.com/jacobcy/litellm-vibe-router)

---

## 1. 项目概述

**目标**: 在现有 LiteLLM 项目基础上，扩展为「轻量级任务调度中间件」，通过 MCP 协议连接各种执行器。

**核心原则**:
- **接口隔离**: 只依赖 MCP 协议
- **可插拔设计**: 执行器通过 MCP 即插即用
- **最小侵入**: 不修改现有开源组件

---

## 2. 现有项目分析

### 2.1 项目结构（假设）

基于标准 LiteLLM 项目，预期的结构：

```
litellm-vibe-router/
├── README.md
├── config.yaml                 # LiteLLM 配置
├── requirements.txt
├── src/
│   ├── __init__.py
│   ├── main.py                 # 主程序
│   ├── router.py               # LiteLLM 路由逻辑
│   └── ...
├── tests/
└── .gitignore
```

### 2.2 配置文件（现有）

```yaml
# config.yaml (现有)
model_list:
  - model_name: claude-3-5-sonnet
    api_base: https://api.anthropic.com
    api_key: ${ANTHROPIC_API_KEY}  # 环境变量

litellm_settings:
  drop_params: true
  temperature: 0.7
```

### 2.3 扩展点

**我们需要添加的模块**:
1. **MCP Client** - 连接外部执行器
2. **状态管理** - SQLite 任务状态机
3. **故障处理** - 脑干模式 + LiteLLM 降级
4. **路由决策** - 选择执行器和模型的逻辑

---

## 3. 架构扩展设计

### 3.1 系统架构（新增部分）

```
┌─────────────────────────────────────────────────┐
│  现有 LiteLLM Router                   │
│  (保持不变）                            │
└──────────────┬──────────────────────────────┘
             │
             ▼ 扩展为 Omni-Orchestrator
    ┌─────────────────────────────────────────┐
    │  Omni-Orchestrator (新增模块）      │
    │                                   │
    │  ┌─────────────────────────────┐    │
    │  │ MCP Client (新增）          │    │
    │  └─────────────────────────────┘    │
    │                                   │
    │  ┌─────────────────────────────┐    │
    │  │ 状态管理 (新增）           │    │
    │  └─────────────────────────────┘    │
    │                                   │
    │  ┌─────────────────────────────┐    │
    │  │ 故障处理 (新增）           │    │
    │  └─────────────────────────────┘    │
    │                                   │
    │  ┌─────────────────────────────┐    │
    │  │ 路由决策 (新增）           │    │
    │  └─────────────────────────────┘    │
    └─────────────────────────────────────────┘
             │
    ┌─────┼────────────────────────────┬───────────┐
    │     │                        │           │
    │     ▼                        ▼           ▼
┌───────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐
│LiteLLM│ │执行器 1 │ │执行器 2 │ │执行器 3 │
│Router │ │OpenClaw │ │Claude   │ │Molt    │
│(现有）│ │         │ │Code     │ │worker   │
└───────┘ └─────────┘ └─────────┘ └─────────┘
```

### 3.2 数据流

**正常任务流程**:
```
用户任务
  │
  ├─ LiteLLM Router (现有) → 选择模型
  │     ↓
  ├─ 路由决策 (新增) → 选择执行器
  │     ↓
  ├─ 状态管理 (新增) → 记录状态
  │     ↓
  └─ MCP Client (新增) → 调用执行器
        ↓
      执行结果返回
```

**故障降级流程**:
```
LiteLLM 故障检测
  │
  ├─ 检测超时 (连续 2 次 < 1s)
  │     ↓
  ├─ 切换到直连 API (使用 GitHub Key)
  │     ↓
  ├─ 触发 Claude Code 修复任务
  │     ↓
  └─ 恢复检测 → 尝试 LiteLLM 或保持直连
```

---

## 4. 模块设计

### 4.1 MCP Client (mcp_client.py)

```python
"""
MCP 客户端模块

功能:
- 连接到 MCP Server (OpenClaw, Claude Code 等)
- 列出可用工具
- 调用工具并获取结果
"""

class MCPClient:
    def __init__(self, server_url: str):
        self.server_url = server_url
        self.tools = {}

    async def connect(self):
        """连接到 MCP Server"""
        pass

    async def list_tools(self):
        """列出所有可用工具"""
        pass

    async def call_tool(self, tool_name: str, **kwargs):
        """调用指定工具"""
        pass

    async def disconnect(self):
        """断开连接"""
        pass
```

### 4.2 状态管理 (state_manager.py)

```python
"""
状态管理模块

功能:
- SQLite 状态存储
- 任务状态机 (IDLE → DISPATCHING → EXECUTING → COMPLETED/FAILED)
- 断点恢复
"""

import sqlite3
from enum import Enum

class TaskState(Enum):
    IDLE = "idle"
    DISPATCHING = "dispatching"
    EXECUTING = "executing"
    WAITING_FOR_CLOUD = "waiting"
    COMPLETED = "completed"
    FAILED = "failed"

class StateManager:
    def __init__(self, db_path: str = "state.db"):
        self.conn = sqlite3.connect(db_path)
        self._init_db()

    def _init_db(self):
        """初始化数据库表"""
        pass

    def create_task(self, description: str) -> str:
        """创建新任务，返回 task_id"""
        pass

    def update_state(self, task_id: str, state: TaskState):
        """更新任务状态"""
        pass

    def get_task(self, task_id: str) -> dict:
        """获取任务信息"""
        pass

    def get_pending_tasks(self) -> list:
        """获取待恢复的任务"""
        pass
```

### 4.3 故障处理 (fault_handler.py)

```python
"""
故障处理模块

功能:
- LiteLLM 故障检测
- 降级到直连 API
- 触发 Claude Code 修复任务
- 脑干模式 (云端 API 故障)
"""

class FaultHandler:
    def __init__(self, lite_llm_router, github_key: str):
        self.router = lite_llm_router
        self.github_key = github_key
        self.consecutive_failures = 0

    async def check_lite_llm_health(self) -> bool:
        """检测 LiteLLM 是否正常"""
        pass

    async def fallback_to_direct_api(self):
        """降级到直连 API"""
        pass

    async def trigger_repair_task(self):
        """触发 Claude Code 修复任务"""
        pass

    async def enter_brainstem_mode(self):
        """进入脑干模式"""
        pass

    async def monitor_cloud_apis(self):
        """监控云端 API 可用性"""
        pass
```

### 4.4 路由决策 (router_decision.py)

```python
"""
路由决策模块

功能:
- 根据任务特征选择执行器
- 根据成本/质量选择模型
- 处理降级模式下的路由
"""

class RouterDecision:
    def __init__(self, mcp_client: MCPClient, lite_llm_router):
        self.mcp_client = mcp_client
        self.router = lite_llm_router

    def select_executor(self, task: dict) -> str:
        """
        选择执行器

        规则:
        - 编程任务 → Claude Code
        - 通用任务 → OpenClaw 自身执行
        - 24/7 任务 → Moltworker (Phase 5)
        """
        pass

    def select_model(self, task: dict, mode: str = "normal") -> dict:
        """
        选择模型

        规则:
        - 正常模式: LiteLLM 路由
        - 降级模式: 直连 API (使用 GitHub Key)
        - 脑干模式: 不执行任务，仅系统自检
        """
        pass
```

### 4.5 API Key 管理 (config.py - 扩展)

```python
"""
配置管理模块

扩展现有 config.yaml:
- 添加 GitHub Key 作为备用
- 支持环境变量覆盖
"""

import yaml
import os

class Config:
    def __init__(self, config_path: str = "config.yaml"):
        self.config = self._load_config(config_path)

    def _load_config(self, path: str) -> dict:
        """加载配置文件"""
        with open(path, 'r') as f:
            config = yaml.safe_load(f)

        # GitHub Key: 配置优先，环境变量兜底
        github_key = config.get('github_key')
        if not github_key:
            github_key = os.getenv('GITHUB_LITELLM_KEY',
                '${GITHUB_LITELLM_KEY}')

        config['github_key'] = github_key
        return config

    def get_primary_keys(self) -> dict:
        """获取主 API Key"""
        pass

    def get_backup_keys(self) -> dict:
        """获取备用 API Key"""
        pass
```

---

## 5. 目录结构

```
litellm-vibe-router/
├── README.md
├── config.yaml                 # 扩展：添加 github_key
├── requirements.txt             # 扩展：添加 mcp, pytest-asyncio
├── pyproject.toml             # 扩展：添加依赖声明
├── src/
│   ├── __init__.py
│   ├── main.py                 # 现有主程序
│   ├── router.py               # 现有 LiteLLM 路由
│   ├── mcp_client.py           # 新增：MCP 客户端
│   ├── state_manager.py         # 新增：状态管理
│   ├── fault_handler.py         # 新增：故障处理
│   └── config.py              # 新增：配置管理
├── tests/
│   ├── unit/
│   │   ├── test_mcp_client.py
│   │   ├── test_state_manager.py
│   │   ├── test_fault_handler.py
│   │   └── test_config.py
│   └── integration/
│       └── test_full_flow.py
└── .gitignore
```

---

## 6. 依赖扩展

```txt
# requirements.txt (扩展)
litellm==1.50.0              # 现有
mcp==0.10.0                   # 新增
pyyaml==6.0.1                  # 新增（如果未安装）
pytest-asyncio==0.23.0         # 新增
pylint==3.1.0                   # 新增
```

---

## 7. 配置文件示例

```yaml
# config.yaml (扩展示例)
# LiteLLM 配置 (保持现有)
model_list:
  - model_name: claude-3-5-sonnet
    api_base: https://api.anthropic.com
    api_key: ${ANTHROPIC_API_KEY}

litellm_settings:
  drop_params: true
  temperature: 0.7

# 新增：GitHub Key (备用直连)
github_key: ${GITHUB_LITELLM_KEY}
# 或直接写死（不推荐）：
# github_key: "${GITHUB_LITELLM_KEY}"

# 新增：MCP Servers 配置
mcp_servers:
  openclaw:
    url: "ws://127.0.0.1:18789"
    name: "OpenClaw"
  claude_code:
    url: "stdio"
    name: "Claude Code"

# 新增：故障处理配置
fault_handler:
  lite_llm_timeout: 1.0      # LiteLLM 超时阈值（秒）
  consecutive_failures: 2       # 连续失败次数阈值
  check_interval: 30           # 脑干模式检测间隔（秒）
  cloud_check_timeout: 10       # 云端 API 超时阈值（秒）
```

---

## 8. 测试策略

### 8.1 单元测试

```python
# tests/unit/test_mcp_client.py
import pytest

@pytest.mark.asyncio
async def test_connect():
    """测试连接功能"""
    pass

@pytest.mark.asyncio
async def test_list_tools():
    """测试工具列表"""
    pass

@pytest.mark.asyncio
async def test_call_tool():
    """测试工具调用"""
    pass
```

### 8.2 集成测试

```python
# tests/integration/test_full_flow.py
import pytest

@pytest.mark.asyncio
async def test_full_task_flow():
    """测试完整任务流程"""
    # 1. 创建任务
    # 2. 选择执行器
    # 3. 选择模型
    # 4. 调用执行器
    # 5. 更新状态
    pass

@pytest.mark.asyncio
async def test_fault_fallback():
    """测试故障降级流程"""
    # 1. 模拟 LiteLLM 故障
    # 2. 验证切到直连 API
    # 3. 验证触发修复任务
    pass
```

---

## 9. 部署方案

### 9.1 本地部署

```bash
# 1. 克隆/拉取现有项目
git clone https://github.com/jacobcy/litellm-vibe-router.git
cd litellm-vibe-router

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置 API Key
cp config.yaml.example config.yaml
# 编辑 config.yaml，设置 API Key

# 4. 运行
python -m src.main
```

### 9.2 Docker 部署（可选）

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src
COPY config.yaml .

CMD ["python", "-m", "src.main"]
```

---

## 10. 风险与缓解

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|----------|
| LiteLLM API 变更 | 中 | 功能失效 | 定期检查 API 文档 |
| MCP 协议不兼容 | 低 | 集成失败 | 使用官方 SDK |
| 状态丢失 | 低 | 任务无法恢复 | 定期备份 SQLite |
| API Key 泄露 | 中 | 安全风险 | 使用环境变量，不提交到 git |

---

## 11. 成功指标

- [ ] 单元测试通过率 100%
- [ ] 集成测试通过率 100%
- [ ] pylint 零警告
- [ ] 任务处理延迟 < 2s (P1 模型)
- [ ] 故障降级时间 < 5s
- [ ] 可用性 > 99%

---

## 文档版本

| 版本 | 日期 | 变动 |
|------|------|------|
| v1.0 | 2026-02-19 | 初始设计，基于现有 LiteLLM 项目 |

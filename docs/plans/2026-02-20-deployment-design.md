# Omni-Orchestrator 部署设计

> **日期**: 2026-02-20
> **版本**: v1.0

---

## 1. 部署架构

### 1.1 整体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                      Mac mini M4 (Docker)                       │
│                                                                 │
│  ┌─────────────────┐  ┌─────────────────────────────────────┐  │
│  │ LiteLLM         │  │ Omni-Orchestrator                   │  │
│  │ :4000           │  │ :18765 (MCP WebSocket)              │  │
│  │                 │  │                                     │  │
│  │ • 模型路由       │  │ • Task Pool (SQLite)               │  │
│  │ • 成本追踪       │  │ • 路由决策                          │  │
│  │ • 降级切换       │  │ • 故障处理                          │  │
│  └────────┬────────┘  └────────────┬────────────────────────┘  │
│           │                        │                            │
│           ▼                        ▼                            │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  客户端: OpenClaw / Claude Code / Cursor / IM Bot       │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 服务角色

| 服务 | 端口 | 协议 | 说明 |
|------|------|------|------|
| LiteLLM | 4000 | HTTP | 模型路由服务（已部署） |
| Omni-Orchestrator | 18765 | WebSocket (MCP) | 任务调度中间件 |

---

## 2. 容器配置

### 2.1 docker-compose.yml

```yaml
name: omni-orchestrator

services:
  omni-orchestrator:
    build: .
    container_name: omni-orchestrator
    ports:
      - "18765:18765"
    volumes:
      - ./config.yaml:/app/config.yaml:ro
      - omni-data:/app/data
    environment:
      - GITHUB_LITELLM_KEY=${GITHUB_LITELLM_KEY}
      - OMNI_HOST=0.0.0.0
      - OMNI_PORT=18765
      - LITELLM_URL=http://litellm-vibe-router:4000
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "python", "-c", "import socket; s=socket.socket(); s.connect(('localhost', 18765)); s.close()"]
      interval: 30s
      timeout: 10s
      retries: 3
    depends_on:
      - litellm-vibe-router

volumes:
  omni-data:
    driver: local
```

### 2.2 Dockerfile 修改

**更新入口点：**

```dockerfile
# Run main program (updated)
CMD ["["python", "-m", "src.main"]
```

### 2.3 .dockerignore

```
__pycache__
*.pyc
.env
state.db
*.db
.git
.gitignore
.DS_Store
.venv
.pytest_cache
.coverage
htmlcov
tests/
docs/
*.md
.vscode
.idea
```

---

## 3. 服务入口实现

### 3.1 新增 src/main.py

```python
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

    def __init__(self, orchestrator: Orchestrator):
        self.orchestrator = orchestrator
        self.host = os.getenv("OMNI_HOST", "0.0.0.0")
        self.port = int(os.getenv("OMNI_PORT", "18765"))

    async def handle_client(self, websocket):
        """处理客户端连接"""
        client_id = websocket.remote_address
        logger.info(f"客户端连接: {client_id}")

        try:
            async for message in websocket:
                logger.debug(f"收到消息: {message[:100]}")
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
```

### 3.2 Orchestrator 新增方法

**需要在 `src/orchestrator.py` 添加：**

```python
async def process_mcp_message(self, message: str) -> str:
    """
    处理 MCP 消息

    Args:
        message: MCP 协议消息 (JSON 字符串)

    Returns:
        str: MCP 响应消息 (JSON 字符串)
    """
    # 解析消息
    import json
    data = json.loads(message)

    method = data.get("method")

    if method == "ping":
        return json.dumps({"result": "pong"})

    elif method == "create_task":
        # 从任务池创建新任务
        description = data["params"]["description"]
        result = await self.process_task(description)
        return json.dumps({"result": result})

    elif method == "get_task_status":
        # 查询任务状态
        task_id = data["params"]["task_id"]
        result = self.state_manager.get_task(task_id)
        return json.dumps({"result": result})

    else:
        return json.dumps({"error": f"Unknown method: {method}")
```

---

## 4. 部署流程

### 4.1 本地部署（Docker Context）

```bash
# 切换到 Docker Context（指向 Mac mini）
docker context use macmini-frps

# 1. 构建镜像
docker compose build

# 2. 启动服务
docker compose up -d

# 3. 查看日志
docker compose logs -f omni-orchestrator

# 4. 健康检查
docker compose ps

# 5. 测试连接
python -c "
import asyncio
import websockets

async def test():
    async with websockets.connect('ws://localhost:18765') as ws:
        await ws.send('{\"method\": \"ping\"}')
        print(await ws.recv())

asyncio.run(test())
"
```

### 4.2 Tailscale 远程访问

**前提条件：** Mac mini 上运行 Tailscale 服务

```bash
# 在 Mac mini 上启动 Tailscale 服务
ssh chenyi@bghunt.cn "tailscale serve --background"

# 确认服务状态
ssh chenyi@bghunt.cn "tailscale serve status"
```

**客户端连接地址：**

```
ws://macmini.tailed323a.ts.net:18765
```

**测试远程连接：**

```python
import asyncio
import websockets

async def test():
    async with websockets.connect('ws://macmini.tailed323a.ts.net:18765') as ws:
        await ws.send('{\"method\": \"ping\"}')
        print(await ws.recv())

asyncio.run(test())
```

---

## 5. 配置文件模板

### 5.1 config.yaml.example

```yaml
# LiteLLM 配置
lite_llm_url: "http://litellm-vibe-router:4000"

# GitHub 备用 Key (可通过环境变量覆盖)
# github_key: "${GITHUB_LITELLM_KEY}"

# MCP Servers 配置
mcp_servers:
  openclaw:
    url: "ws://127.0.0.1:18789"
    name: "OpenClaw"
  claude_code:
    url: "stdio"
    name: "Claude Code"

# 故障处理配置
fault_handler:
  consecutive_failures_threshold: 2
  cloud_failure_threshold: 3
  brainstem_model: "qwen:7b-instruct"

# 路由配置
router:
  complexity_threshold: 50
  lightweight_model: "claude-3-5-haiku"
  heavyweight_model: "claude-3-5-sonnet"
```

---

## 6. 目录结构

```
omni-vibe/
├── docker-compose.yml     # 新增
├── Dockerfile             # 修改 CMD
├── .dockerignore          # 已有
├── config.yaml.example    # 已有
├── src/
│   ├── __init__.py        # 已有
│   ├── main.py            # 新增 - 服务入口
│   ├── orchestrator.py    # 已有 - 需添加 process_mcp_message
│   ├── config.py         # 已有
│   ├── state_manager.py  # 已有
│   ├── mcp_client.py     # 已有
│   ├── fault_handler.py  # 已有
│   └── router_decision.py # 已有
├── tests/
│   ├── unit/
│   └── integration/
└── docs/
    └── plans/
```

---

## 7. 部署检查清单

部署完成后验证：

- [ ] 容器成功启动 (`docker compose ps`)
- [ ] 健康检查通过 (`docker compose ps` 显示 healthy)
- [ ] 本地 WebSocket 连接成功 (`ws://localhost:18765`)
- [ ] Tailscale 服务运行 (`ssh macmini "tailscale serve status"`)
- [ ] 远程 WebSocket 连接成功 (`ws://macmini.tailed323a.ts.net:18765`)
- [ ] MCP ping/pong 响应正常
- [ ] 任务创建和状态查询功能正常
- [ ] SQLite 数据用 Volume 持久化

---

## 设计完成

下一步：调用 `writing-plans` 技能创建实施计划。

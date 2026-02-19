# Omni-Orchestrator

> ARES - Autonomous Reasoning & Execution System
>
> 轻量级任务调度中间件，通过 MCP 协议连接各种执行器

## Features

- Task routing (根据任务特征选择执行器: Claude Code / OpenClaw / Moltworker)
- LiteLLM model routing (免费/付费模型优先级)
- SQLite state management (任务状态机，支持断点恢复)
- Dual fault handling (LiteLLM 降级模式 + 脑干模式)
- MCP protocol integration (连接 OpenClaw, Claude Code 等)

## Quick Start

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (Python package manager)

### Local Setup

```bash
# Clone
git clone <repo-url>
cd omni-vibe

# Install dependencies
uv sync

# Configure
cp config.yaml.example config.yaml
# Edit config.yaml with your API keys

# Run tests
uv run pytest

# Run main program
uv run python -m src.main
```

### Docker

```bash
# Build
docker build -t omni-orchestrator .

# Run
docker run --rm omni-orchestrator
```

## Configuration

Copy `config.yaml.example` to `config.yaml` and configure:

| Key | Description |
|-----|-------------|
| `github_key` | Backup API key (env: `GITHUB_LITELLM_KEY`) |
| `lite_llm_url` | LiteLLM proxy URL |
| `mcp_servers` | MCP server connections |
| `fault_handler` | Failure thresholds |
| `router` | Routing settings |

## Architecture

```
┌─────────────────────────────────────────┐
│  Omni-Orchestrator                      │
│  ┌───────────┐  ┌──────────────────┐    │
│  │ MCP Client│  │ State Manager    │    │
│  └───────────┘  └──────────────────┘    │
│  ┌───────────┐  ┌──────────────────┐    │
│  │ Fault     │  │ Router Decision  │    │
│  │ Handler   │  │                  │    │
│  └───────────┘  └──────────────────┘    │
└──────┬──────────────┬──────────┬────────┘
       │              │          │
       ▼              ▼          ▼
┌──────────┐  ┌───────────┐  ┌──────────┐
│ OpenClaw │  │Claude Code│  │Moltworker│
└──────────┘  └───────────┘  └──────────┘
```

### System States

| State | Trigger | Behavior |
|-------|---------|----------|
| **Normal** | All systems healthy | Route via LiteLLM + MCP |
| **Degraded** | LiteLLM fails | Direct API with backup key |
| **Brainstem** | Cloud APIs down | Suspend tasks, local-only |

## Testing

```bash
# All tests
uv run pytest

# Unit tests only
uv run pytest tests/unit/

# Integration tests only
uv run pytest tests/integration/

# With coverage
uv run pytest --cov=src --cov-report=html
```

### Docker 部署到 Mac mini

```bash
# 切换 Docker Context（指向 Mac mini）
docker context use macmini-frps

# 构建并启动
docker compose up -d

# 查看日志
docker compose logs -f omni-orchestrator

# 停康检查
docker compose ps
```

### Tailscale 远程访问

```bash
# 确保 Tailscale 服务在 Mac mini 上运行
ssh chenyi@bghunt.cn "tailscale serve --background"

# 客户端连接地址
ws://macmini.tailed323a.ts.net:18765
```

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Language | Python 3.11+ |
| Package Manager | uv |
| Model Routing | LiteLLM |
| Protocol | MCP (Model Context Protocol) |
| State Storage | SQLite |
| Testing | pytest + pytest-asyncio |

## License

MIT

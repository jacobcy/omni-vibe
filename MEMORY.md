
# Project Memory

## Project Metadata

| Field | Value |
|-------|-------|
| **Name** | AI Personal Assistant Command Center |
| **Codename** | ARES (Autonomous Reasoning & Execution System) |
| **Language** | Python 3.11+ |
| **Framework** | LiteLLM (LLM 路由與抽象層) |
| **Protocol** | MCP (Model Context Protocol) |
| **Testing** | pytest + pytest-asyncio |
| **Linting** | pylint |
| **Package Manager** | uv (现代 Python 包管理器) |
| **Core Hardware** | Mac mini M4 |

## Architecture Decisions

### 1. MCP Protocol Choice
- **Decision**: 採用 Model Context Protocol 作為核心通信協議
- **Rationale**: 解耦 LLM 與工具執行，支持異構部署
- **Date**: 2025-02-19

### 2. LiteLLM as Router
- **Decision**: 使用 LiteLLM 統一管理多模型路由
- **Rationale**: 支持 100+ LLM providers，統一接口，成本追蹤
- **Date**: 2025-02-19

### 3. Hybrid Execution Model
- **Decision**: 雲端 (推理) + 本地 (執行)
- **Rationale**: 平衡智能與成本，保護隱私
- **Date**: 2025-02-19

### 4. uv Package Manager
- **Decision**: 使用 uv 作为 Python 包管理器和项目管理工具
- **Rationale**: 现代、快速、可靠的依赖管理，比 pip 快 10-100 倍
- **Date**: 2026-02-19

### 5. Docker 部署架构
- **Decision**: 使用 Docker Compose + Docker Context 远程部署
- **Rationale**: 容器化部署便于管理和扩展，Docker Context 允许从本地直接部署到 Mac mini
- **Date**: 2026-02-20

### 6. Tailscale 远程访问
- **Decision**: 使用 Tailscale VPN 提供 Mac mini 的远程访问
- **Rationale**: 安全、无需公网 IP，支持多平台
- **Details**:
  - Mac mini 地址: `macmini.tailed323a.ts.net`
  - 内网 IP: `100.112.203.89`
- **Date**: 2026-02-20

## Tech Stack

```
┌─────────────────────────────────────┐
│           Client Layer              │
│    (Claude Desktop / CLI / Web)     │
└─────────────┬───────────────────────┘
              │ MCP Protocol
┌─────────────▼───────────────────────┐
│        Gateway Layer                │
│    (LiteLLM + MCP Router)           │
├─────────────────────────────────────┤
│        MCP Server Layer             │
│  ┌─────────┐ ┌─────────┐ ┌───────┐ │
│  │ Memory  │ │ Tools   │ │ Files │ │
│  │ Server  │ │ Server  │ │Server │ │
│  └─────────┘ └─────────┘ └───────┘ │
└─────────────────────────────────────┘
```

## Key Dependencies
- litellm: LLM 統一接口與路由
- mcp: Model Context Protocol SDK
- pytest: 測試框架
- pylint: 代碼質量檢查
- pydantic: 數據驗證
- asyncio: 異步執行

---


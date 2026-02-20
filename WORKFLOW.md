
# Workflow Documentation

## Development Workflow

### 1. Feature Development

```bash
# 1. 創建功能分支
git checkout -b feature/<feature-name>

# 2. 編寫測試 (TDD)
# 文件: tests/test_<module>.py

# 3. 實現功能
# 文件: src/<module>.py

# 4. 運行測試
pytest tests/test_<module>.py -v

# 5. 代碼檢查
pylint src/<module>.py

# 6. 提交 (遵循約定式提交)
git commit -m "feat: add <feature description>"
```

### 2. MCP Server Development

```bash
# 1. 繼承 BaseMCPServer
# 2. 實現 @tool 裝飾器方法
# 3. 註冊到 Server Registry
# 4. 編寫單元測試
# 5. 編寫集成測試
```

### 3. Testing Workflow

```bash
# 運行所有測試
pytest

# 運行特定測試
pytest tests/test_specific.py::test_function -v

# 生成覆蓋率報告
pytest --cov=src --cov-report=html

# 持續測試模式
pytest -f  # 或 --looponfail
```

### 4. Code Quality Workflow

```bash
# 檢查所有代碼
pylint src/

# 自動修復 (部分)
black src/  # 如果使用

# 類型檢查 (可選)
mypy src/
```

### 5. Deployment Workflow

```bash
# 1. 版本標記
git tag -a v0.1.0 -m "Release v0.1.0"

# 2. 構建
python -m build

# 3. 部署到 Mac mini
scp dist/* user@mac-mini:~/ares/

# 4. 重啟服務
ssh user@mac-mini "cd ~/ares && ./restart.sh"
```

### 6. Docker Deployment Workflow

```bash
# 切換 Docker Context (指向 Mac mini)
docker context use macmini-frps

# 構建並啟動
docker compose up -d

# 查看日誌
docker compose logs -f omni-orchestrator

# 健康檢查
docker compose ps

# 重啟服務
docker compose restart

# 停止服務
docker compose down
```

### 7. Tailscale 遠程訪問

```bash
# 確保 Tailscale 服務在 Mac mini 上運行
ssh chenyi@bghunt.cn "tailscale serve --background"

# 客戶端連接地址
ws://macmini.tailed323a.ts.net:18765

# 測試 WebSocket 連接
python -c "
import asyncio
import websockets
import json

async def test():
    async with websockets.connect('ws://localhost:18765') as ws:
        await ws.send(json.dumps({'method': 'ping'}))
        print(await ws.recv())

asyncio.run(test())
"
```

## Git Commit Convention

```
<type>(<scope>): <subject>

<body>

<footer>
```

Types:
- **feat**: 新功能
- **fix**: 修復
- **docs**: 文檔
- **test**: 測試
- **refactor**: 重構
- **perf**: 性能優化
- **chore**: 構建/工具

---


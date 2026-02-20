# Omni-Vibe 2026 系統架構設計文檔 (v1.1 - 優化版)

> **核心理念**：Omni-Orchestrator 是輕量級任務調度中間件，通過 **MCP 協議**連接開源組件，只做「路由決策」而非「具體執行」。

---

## 1. 項目願景與定位

打造以 **Mac mini** 為核心指揮部、**MCP** 為通信神經的「高韌性 AI 協作系統」。核心矛盾在於：如何在利用雲端廉價/頂級算力的同時，保持本地環境的安全隔離與斷網自檢能力。

**關鍵決策（v1.1 更新）**：
- **接口隔離**：Omni-Orchestrator 只依賴 MCP 協議，不耦合任何組件的內部實現
- **可插拔設計**：任何支持 MCP 的執行器都可以即插即用
- **最小侵入**：不修改現有組件，只通過 MCP 調用它們暴露的工具

---

## 2. 系統架構圖 (System Architecture)

```mermaid
graph TD
    User([用戶]) -- IM: WeChat/Discord/Telegram --> OpenClaw[OpenClaw: 統一入口]

    subgraph Omni_Orchestrator [Omni-Orchestrator: 任務調度中間件]
        OpenClaw --任務--> Orchestrator[路由決策 + 成本控制]
        Orchestrator --狀態--> StateDB[(SQLite: 任務狀態)]
        Orchestrator --模型--> LiteLLM[LiteLLM: 模型路由]
        Orchestrator --降級--> LocalLLM[Qwen 7B: 冷啟動]

        subgraph 執行器層 [可插拔執行器 - MCP]
            Orchestrator --MCP--> |通用任務| OpenClawExec[OpenClaw 自身執行]
            Orchestrator --MCP--> |編程任務| ClaudeCode[Claude Code]
            Orchestrator --MCP--> |雲端執行| Moltworker[Moltworker: Cloudflare]
        end
    end

    subgraph 模型路由層 [LiteLLM 渠道]
        LiteLLM -- P1: 免費|--> CLIProxy[CLIProxyAPI]
        LiteLLM -- P2: 付費|--> OpenRouter[OpenRouter API]
    end

    subgraph 冷啟動腦幹 [僅在雲端故障時啟動]
        Qwen7B[Qwen 7B: 腦幹模式]
        -.->|保持冷啟動狀態|
        Note[僅 LiteLLM 檢測斷網時啟動<br/>作為系統自檢的「腦幹」<br/>執行最小任務並等待雲端恢復]
    end
```

---

## 3. 核心組件職能定義

### 3.1 Omni-Orchestrator（你們要做的）

| 職責 | 說明 |
|------|------|
| **任務接收** | 從 OpenClaw MCP 接口接收任務描述 |
| **路由決策** | 根據任務特徵選擇執行器（本地/雲端）和模型（免費/付費/本地） |
| **成本控制** | 記錄每次調用的成本，優先使用免費渠道 |
| **狀態追蹤** | SQLite 記錄任務狀態，支持斷點恢復 |
| **冷啟動感知** | 檢測雲端故障，自動切換到本地模型 |
| **MCP 調用** | 通過 MCP 協議調用各組件的工具 |

**不負責的內容：**
- ❌ 執行器的具體實現（交給 OpenClaw、Claude Code 等）
- ❌ 記憶的具體存儲（交給 MemOS，Phase 5+）
- ❌ 瀏覽器自動化（交給 OpenClaw）

### 3.2 開源組件集成

| 組件 | 項目 | 作用 | MCP 支持 |
|------|------|------|----------|
| **OpenClaw** | IM 網關 + 意圖識別 | 統一用戶入口，支持 WeChat/Discord/Telegram 等 | ✅ |
| **Claude Code** | 編程執行器 | 處理編程相關任務、系統修復 | ✅ |
| **Moltworker** | 雲端執行器 | Cloudflare Workers 上的 24/7 執行 | ✅ |
| **MemOS** | 記憶管理（可選） | 長期記憶與上下文管理 | ✅ |
| **LiteLLM** | 模型路由 | 統一 100+ LLM providers | ✅（集成） |
| **CLIProxyAPI** | 免費 API 代理 | OAuth 統一 CLI 工具，提供免費算力 | ✅（LiteLLM 渠道） |

### 3.3 備用 API Key 管理

**存儲方式**：配置文件（`config.yaml`）```yaml
# config.yaml
api_keys:
  primary:
    claude: "sk-ant-xxx"      # 主渠道
    openrouter: "sk-or-xxx"
  backup:
    claude: "sk-ant-yyy"      # 備用 Key（LiteLLM 故障時用）
    openrouter: "sk-or-yyy"
```

**使用規則**：
- 正常狀態：通過 LiteLLM 路由調用（使用 Primary Key）
- LiteLLM 故障：繞過 LiteLLM，直連底層 API（使用 Backup Key）

---

## 4. 路由決策邏輯

### 4.1 執行器選擇規則

```
任務接收
    │
    ├─ 任務類型判斷
    │   ├─ 編程任務 → Claude Code（優先）
    │   ├─ 通用任務 → OpenClaw 自身執行
    │   └─ 24/7 任務 → Moltworker（Phase 5+）
    │
    ├─ 資源約束判斷
    │   ├─ 需要 GPU/高算力 → Moltworker
    │   └─ 可本地執行 → 優先本地
    │
    └─ 網絡狀態判斷
        ├─ 雲端正常 → 按上述規則
        └─ 雲端故障 → 僅用本地 OpenClaw + Qwen 7B
```

### 4.2 模型選擇規則（LiteLLM）

| 優先級 | 目標 | 觸發條件 | 預期延遲 |
| --- | --- | --- | --- |
| **P1** | CLIProxyAPI | 默認狀態，免費 Claude/Gemini | < 2s |
| **P2** | OpenRouter | P1 限流或檢測到複雜需求 | < 1.5s |
| **P3** | 本地 Qwen 7B | 僅斷網腦幹模式（不執行任務） | N/A |

### 4.3 狀態機定義

```python
class TaskState(Enum):
    IDLE = "idle"               # 任務已創建，等待開始
    DISPATCHING = "dispatching"     # 正在選擇執行器和模型
    EXECUTING = "executing"         # 執行器正在處理
    WAITING_FOR_CLOUD = "waiting"   # 雲端故障，任務已掛起（腦幹模式）
    COMPLETED = "completed"         # 任務成功完成
    FAILED = "failed"              # 任務失敗
```

### 4.4 腦幹模式狀態

```python
class SystemState(Enum):
    NORMAL = "normal"             # 正常模式：雲端可用
    BRAINSTEM = "brainstem"         # 腦幹模式：雲端離線，僅維持自檢
```

---

## 5. 故障處理機制

### 5.1 腦幹模式（雲端 API 離可用）

> **設計理念**：本地 Qwen 7B 是「腦幹」——保持系統最小可用性，等待雲端恢復。

| ✅ 做 | ❌ 不做 |
|------|--------|
| 檢測網絡狀態 | 執行複雜任務 |
| 將所有任務標記為 `WAITING_FOR_CLOUD` | 代替雲端模型回答問題 |
| 通知用戶當前系統狀態 | 處理編程任務 |
| 監測雲端恢復信號 | 長時間獨立運行 |
| 恢復時協助系統回到正常狀態 | 做任何「思考」工作 |

### 5.2 LiteLLM 故障降級（路由服務雜可用）

> **設計理念**：LiteLLM 本身故障時，自動降級到直連 API + 觸發修復任務。

```
正常狀態
    │
    ├─ Omni-Orchestrator 偵測 LiteLLM 故障（連續 2 次超時 < 1s）
    │   - LiteLLM 進程無響應
    │   - LiteLLM 返回錯誤
    │
    ▼
進入降級模式
    │
    ├─ 1. 啟動「直連 API」：
    │      - 繞過 LiteLLM，使用 Backup Key 直連 Claude/OpenRouter
    │      - 保持任務處理，不受 LiteLLM 故障影響
    │
    ├─ 2. 觸發 Claude Code 修復任務：
    │      - 任務類型：系統修復
    │      - 目標：修復 LiteLLM 服務
    │      - Claude Code 執行腳本重啟/日誌診斷
    │
    └─ 3. 等待修復完成：
        - Claude Code 完成 → 嘗試 LiteLLM
        - LiteLLM 恢復 → 切換回 LiteLLM 路由
        - 仍舊敗 → 保持直連模式，通知用戶
```

### 5.3 腦幹模式的觸發與恢復

**觸發條件**：
- LiteLLM 報測到雲端 API 連續 3 次超時（每次超時 > 10s）

**啟動腦幹**：
1. 喚醒本地 Qwen 7B（從冷啟動狀態）
2. 執行「系統掛起腳本」：
   - 將所有 `EXECUTING` 任務 → `WAITING_FOR_CLOUD`
   - 保存當前狀態快照到 SQLite
   - 通過 OpenClaw 通知用戶：「雲端離線，任務已掛起」
3. 進入「監測循環」：
   - 每 30s 嘗試 ping 雲端 API
   - 不執行任何用戶任務

**恢復條件**：
- LiteLLM 偵測到雲端恢復（連續 2 次成功）

**執行恢復**：
1. 執行「系統恢復腳本」：
   - 讀取 SQLite 中的掛起任務
   - 將 `WAITING_FOR_CLOUD` 任務 → `IDLE`（等待重新調度）
   - 通過 OpenClaw 通知用戶：「雲端已恢復，任務恢復中」
2. 關閉本地 Qwen 7B（Release VRAM）
3. 恢復正常路由（LiteLLM 或直連 API）

---

## 6. 技術棧

| 組件 | 選項 | 說明 |
|------|------|------|
| **語言** | Python 3.11+ | 與 MCP SDK、LiteLLM 兼容 |
| **狀態儲** | sqlite3（標準庫） | 輕量可靠，依賴少 |
| **異步** | asyncio | 所有 IO 操作使用 async/await |
| **協議** | MCP (Model Context Protocol) | 統一組件接口 |
| **日誌** | logging (標準庫) + 結構化 JSON | 便於 RCA 分析 |

---

## 7. 本地開發環境清單

| 組件 | 選項 | 版本/配置 |
|------|------|------------|
| **宿主機** | Mac mini | M-series (M1/M2/M4) |
| **運行時** | Python 3.11+ | 虛擬環境 (venv 或 poetry) |
| **依賴** | litellm, mcp, pytest, pylint | 核心依賴 |
| **狀態儲** | sqlite3 | Python 標準庫 |

**開源組件配置：**
- **OpenClaw**: 按官方文檔安裝，啟用 MCP Server
- **Claude Code**: 按 MCP 文檔配置本地連接
- **Moltworker**: 按需配置 Cloudflare Workers

---

## 8. 必須避免的模式 (Anti-Patterns)

1. **深入組件內部**：嚴禁深入 OpenClaw/MemOS/Moltworker 的內部實現
   * **原則**：只使用 MCP 接口，不耦合內部邏輯
2. **狀態重復**：組件本身有狀態管理時，不要在 Orchestrator 重復
   * **原則**：只追蹤「路由決策」相關的狀態
3. **緊密耦合**：避免對特定組件的硬編碼依賴
   * **原則**：所有執行器通過 MCP 抽象統一對待
4. **單點故障**：LiteLLM 故障時不要僅等，要自動降級
   * **原則**：降級 + 修復雙管齊進，保證可用性
5. **API Key 硬編碼**：嚴禁將 API Key 寫在代碼中
   * **原則**：使用配置文件或環境變量

---

## 9. 實施階段建議

### Phase 1: 基礎設施 (1 週) ✅
1. 項建項目目錄結構
2. 初始化 Python 虛擬環境
3. 安裝核心依賴 (litellm, mcp, pytest, pylint)
4. 配置 pylint 與 pytest

### Phase 2: CLI 路由基礎 (1 週) ✅
1. 命令行接口接收任務
2. LiteLLM 集成（P1: CLIProxyAPI, P2: OpenRouter）
3. 基礎路由邏輯（簡單規則優先級）
4. 單元測試

### Phase 3: MCP 集成 (3-5 天) ✅
1. OpenClaw MCP 接口集成
2. Claude Code MCP 接口集成
3. 任務分發邏輯（編程 vs 通用）
4. 集成測試

### Phase 4: 狀態機與降級 (3-5 天) ✅
1. SQLite 狀態存儲
2. 斷點恢復邏輯
3. 冷啟動檢測（雲端連續 3 次失敗）
4. E2E 測試（完整流程）

### Phase 5: 可選增強（後續）
1. MemOS 集成（長期記憶）
2. Moltworker 集成（雲端執行）
3. 成本追蹤 Dashboard
4. OpenClaw 自定義通知配置

---

## 10. 局限性分析

* **組件依賴**：依賴 OpenClaw、Claude Code 等開源組件的穩定性
* **調試複雜度**：多組件協同時，問題可能來源於任何一方
* **MCP 協議變更**：如果 MCP 規範變更，可能需要適配
* **網絡依賴**：雲端降級時，本地模式能力有限

---

## 11. 改進建議

* **影子 Workspace 預熱**：提前在後台準備乾淨的 Claude Code 工作區
* **結構化日誌**：所有 MCP 調用輸出 JSON 格式，便於自動化 RCA
* **配置驅證**：啟動時驗證所有開源組件的 MCP 配置
* **降級通知**：優化降級時的用戶提示，讓用戶了解當前狀態
* **LiteLLM 健康檢查**：定期執行健康檢查，提前發現潛在問題

---

## 文檔版本資訊

| 欄本 | 日期 | 變動 |
|------|------|------|
| v1.0 | 2026-02-19 | 統合原兩個版本，形成統一方案 |
| v1.1 | 2026-02-19 | 優化為「輕量協度中間件」，明確接口隔離原則 |

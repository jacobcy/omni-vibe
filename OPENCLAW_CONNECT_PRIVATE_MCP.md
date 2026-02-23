# OpenClaw 执行任务：接入已部署的私有 MCP（omni-orchestrator）

你是执行代理。请严格按本文件执行，不要发散。

## 0) 背景与目标

`omni-vibe` 已经部署完成，`omni-orchestrator` 正在运行。

你的目标不是安装项目，而是让 OpenClaw 成功接入这个私有 MCP 服务，并通过最小协议验证。

---

## 1) 输入参数（先读再执行）

请先设置并打印以下变量：

- `OMNI_MCP_URL`（必填，占位符）：`<ASK_USER_OMNI_MCP_URL>`
- `OMNI_MCP_NAME`（可选）：默认 `omni-private`（这是 OpenClaw 里显示/引用该 MCP 连接的别名，不是协议字段）
- `OMNI_MCP_AUTH_TOKEN`（可选）：若网关要求鉴权则使用

若任一必填信息缺失，不允许猜测：必须先向用户询问并等待确认后再执行。

推荐询问模板（仅缺失时）：

1. `请提供 OMNI_MCP_URL（例如 ws://<host>:18765）`
2. `是否使用默认 MCP 名称 omni-private？如需自定义请提供 OMNI_MCP_NAME`
3. `是否需要鉴权 token？如需要请提供 OMNI_MCP_AUTH_TOKEN`

---

## 2) 安全约束（必须遵守）

1. 不执行任何系统安装、卸载、重装操作。
2. 不修改与 MCP 配置无关的 OpenClaw 设置。
3. 若存在同名 MCP 配置，先备份再更新。
4. 所有步骤失败必须停止并返回失败 JSON。

---

## 3) 执行步骤（幂等）

按顺序执行：

### Step A: 发现并备份 OpenClaw MCP 配置

1. 查找 OpenClaw 的 MCP 配置入口（UI 或配置文件）。
2. 若已存在 `OMNI_MCP_NAME`，先导出/备份原配置。
3. 记录备份位置到结果中。

### Step B: 添加/更新私有 MCP 连接

为 OpenClaw 添加一个 MCP Provider，字段要求如下：

- `name`: `OMNI_MCP_NAME`（默认 `omni-private`）
- `transport`: `websocket`
- `url`: `OMNI_MCP_URL`
- `enabled`: `true`
- `auth`: 仅当 `OMNI_MCP_AUTH_TOKEN` 提供时再配置

保存后触发 OpenClaw 重载 MCP Providers（仅重载，不重装软件）。

### Step C: 连接验证（协议级）

通过 OpenClaw 对该 MCP 发起以下请求并记录原始响应：

1. `ping`
2. `create_task`（description: `health-check from openclaw`）
3. `get_task_status`（使用上一步返回的 `task_id`）

判定通过条件：

- `ping` 返回 `pong`
- `create_task` 返回 `status` 为 `completed` 或 `suspended`（脑干模式也算联通成功）
- `get_task_status` 返回非空结果

### Step D: 失败回滚（仅失败时）

若 Step C 任一步失败：

1. 恢复 Step A 的备份配置
2. 重载 OpenClaw MCP Providers
3. 返回失败 JSON（包含失败点和排查建议）

---

## 4) 交付格式（必须）

执行完成后，仅输出一个 JSON：

```json
{
  "success": true,
  "mcp_name": "omni-private",
  "mcp_url": "<OMNI_MCP_URL>",
  "backup_path": "<path-or-null>",
  "checks": {
    "ping": "passed",
    "create_task": "passed",
    "get_task_status": "passed"
  },
  "raw_responses": {
    "ping": "<raw>",
    "create_task": "<raw>",
    "get_task_status": "<raw>"
  }
}
```

失败时输出：

```json
{
  "success": false,
  "failed_step": "<Step A|B|C|D>",
  "error": "<错误信息>",
  "rollback": "done|skipped",
  "hint": "<修复建议>"
}
```

---

## 5) 给 OpenClaw 的调用语句（可直接复制）

请读取该 Markdown，目标是“接入已部署的私有 MCP”，不是安装项目。按文档步骤执行，并仅返回 JSON 结果。
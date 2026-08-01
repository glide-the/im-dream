# Task: Story Workspace 工作流状态与错误恢复体验

> **Task ID**: `task_213_frontend_story_workspace_status`
> **源 Issue**: `DECK-012` (from `SUO-223` / `SUO-218`)
> **类型**: `frontend`（**TaskDesignAgent 负责 task 设计**，前端实现 Agent 负责代码实现）
> **优先级**: `P1`
> **生成日期**: 2026-08-01
> **状态**: `draft`

---

## 1. 任务标题

DECK-012: Story Workspace 工作流状态与错误恢复体验

---

## 2. 关联 Issue

| 关联 | ID | 说明 |
|---|---|---|
| 源 Issue | `DECK-012` | Story Workspace 工作流状态与错误恢复体验 |
| 父 Issue | `SUO-217` | 组织 Deck 插件业务设计与 ClaudeAgent 交互方案分派 |
| Design Issue | `SUO-218` | Voice Decks × Ink Dream Deck Plugin 与 ClaudeAgent 集成设计 |
| Issue 清单 | `SUO-223` | Deck Plugin 前端/后端 Issue 拆解 |
| 上游 design | `docs/design/deck-plugin-voice-ink-dream-integration.md` §13.1 | 前端负责范围 |
| 上游 layout | `docs/design/story-workspace/story-workspace-layout-design.md` §2.3, §4.5 | 既有布局设计 |
| 上游 delta | `docs/design/story-workspace/story-workspace-deck-integration-delta.md` §7.2 | 工作流运行状态 |

---

## 3. 任务目标

实现 story-workspace 中工作流执行状态的完整展示和错误恢复体验：

1. Dashboard/创作入口展示工作流上下文条（Deck 插件、Desk 状态、运行进度）。
2. 覆盖所有运行状态：未选择、不可用、Desk 未就绪、预检中、运行中、待审阅、失败、完成。
3. Preflight 进度可观察，失败时展示结构化错误和恢复入口。
4. 运行中展示步骤进度与 `workflow_run_id`。
5. 历史剧本可追溯来源（`workflow_run_id`、`deck_plugin_version`、`desk_config_snapshot_id`）。
6. 结构化错误码映射为用户可理解的恢复动作。

本 task 与 story-workspace 既有布局、审阅 UI 增量集成，不推翻既有设计。

> **命名隔离原则**：本 task 涉及的插件标识必须使用 `deck_plugin_id` + `deck_plugin_version` 前缀，禁止与 `claude_code_plugin_id` 混用。来源追溯展示必须区分 Deck Plugin（业务工作流）和 Claude Code Plugin（运行时能力包）。

### 3.1 UI 状态适用性矩阵

| 状态组 | 适用性 | 本 task 的 UI 边界 | 依赖方与原因 |
|---|---|---|---|
| `installation/compatibility` | 部分适用（只读执行门禁） | 在上下文条和 preflight 结果中展示不可用、兼容性失败、runtime 未就绪及恢复去向；不安装插件、不推进 installation 状态机、不自行计算兼容性 | `DECK-003` / `DECK-004` / `DECK-006` 提供权威结果，`task_211_frontend_plugin_admin_ui` 负责管理态恢复 |
| `binding/version` | 部分适用（只读来源） | 展示当前 binding、精确版本和不可变运行来源，并提供“更换工作流”入口；选择、保存和 `binding_revision` 并发处理 N/A | `DECK-005`、`task_210_shared_deck_plugin_binding` 与 `task_212_frontend_deck_editor_plugin_binding` 负责 binding/version 编辑 |
| `preflight/run` | 适用（核心） | 展示 8 步 preflight、Workflow Run 状态/进度、取消、审阅、重试与历史来源；只消费后端合同，不实现运行服务 | `DECK-006` / `DECK-007` 提供权威 preflight/run 状态机、token、幂等与 mutation |
| `error/recovery` | 适用（执行态） | 将 preflight/run 错误映射为安全文案与重试、取消、更换、申请授权等动作；安装修复与 binding 编辑通过 owner 入口转交 | `DECK-014` 提供错误码；安装恢复由 `task_211_frontend_plugin_admin_ui` 承担，binding 恢复由 `task_212_frontend_deck_editor_plugin_binding` 承担 |

---

## 4. 实现步骤

### 步骤 1：工作流上下文条（Dashboard/创作入口）

1.1 在 Dashboard 或创作入口顶部新增 `WorkflowContextBar`：

```
┌─────────────────────────────────────────────────────────────────────┐
│  🧩 悬疑短剧工作流 v3.1.0  │  Desk: ✅ Ready  │  运行: ⏳ 预检中...    │
│  [更换工作流]              │  [查看配置]      │  [取消]               │
└─────────────────────────────────────────────────────────────────────┘
```

1.2 展示内容：
- 当前绑定的 Deck Plugin：`display_name` + `deck_plugin_version`
- Desk 就绪状态：基于 `desk_config_snapshot_id` 的校验结果
- 当前运行状态：
  - 未选择插件 → "未选择工作流"
  - 插件不可用 → "工作流不可用"
  - Desk 未就绪 → "配置未就绪"
  - 预检中 → "预检中…" + 进度
  - 运行中 → "运行中…" + 步骤进度
  - 待审阅 → "待审阅"
  - 失败 → "运行失败" + 错误摘要
  - 完成 → "已完成"

1.3 操作按钮（按状态条件展示）：
- 「更换工作流」→ 跳转到 Deck 选择
- 「查看配置」→ 展示 Desk 配置摘要（脱敏）
- 「开始运行」→ 触发 preflight
- 「取消」→ 取消当前运行（queued/running 时）
- 「重试」→ 按原版本创建新 run
- 「审阅结果」→ 打开 Review Panel

### 步骤 2：Preflight 进度与状态展示

2.1 实现 `PreflightProgressPanel`：
- 触发 preflight 后展示进度
- 步骤列表（设计稿 §10.2 8 步检查）：
  1. 身份、workspace、Deck 使用权限
  2. binding revision 与精确 release 可用性
  3. manifest/hash、workflow definition、输入/输出 schema
  4. host、ClaudeAgent、Claude Code、Desk contract 兼容性
  5. 能力交集与来源策略
  6. 创建或复用不可变 `desk_config_snapshot_id`
  7. 验证 runtime lock 的 declared/materialized/digest/load smoke
  8. 计算输入 hash、过期时间并签发 `preflight_token`

2.2 每步展示：
- 步骤序号 + 名称
- 状态：⏳ 等待 / 🔄 检查中 / ✅ 通过 / ❌ 失败
- 失败时展示：error_code + 安全文案 + 恢复动作

2.3 Preflight 结果：
- 全部通过 → 展示「开始运行」按钮（携带 `preflight_token`）
- 任一步失败 → 停止后续展示，聚焦错误恢复

### 步骤 3：运行状态展示

3.1 实现 `WorkflowRunStatusPanel`：

| 状态 | UI 表现 | 展示内容 |
|---|---|---|
| `workflow_unselected` | 空状态卡片 | "选择工作流以开始创作" + 选择入口 |
| `workflow_unavailable` | 警告卡片 | "当前工作流不可用" + reason + 更换入口 |
| `desk_config_not_ready` | 警告卡片 | "Desk 配置未就绪" + 配置 owner + 修复入口 |
| `preflight_checking` | 进度面板 | PreflightProgressPanel |
| `running` | 运行面板 | 步骤进度条、当前步骤、已运行时间、`workflow_run_id` |
| `awaiting_review` | 成功面板 | 结果摘要 + 「开始审阅」按钮 |
| `failed` | 错误面板 | 失败步骤、error_code、恢复动作（重试/更换/报告） |
| `completed` | 完成面板 | 结果摘要 + 来源追溯 |

3.2 运行中展示：
- 步骤进度条（按 manifest 声明的 steps）
- 当前步骤名称
- 已运行时间
- `workflow_run_id`（小字，用于诊断）
- 「取消运行」按钮（queued/running 时）

3.3 事件驱动更新：
- 通过 SSE/WebSocket 消费 `workflow.run.status_changed` 事件
- 按 `event_id` 去重
- 按 `aggregate_version` 保证顺序

### 步骤 4：错误恢复体验

4.1 结构化错误码映射（设计稿 §12.1）：

| 错误码 | 用户可见文案 | 恢复动作 |
|---|---|---|
| `WORKFLOW_SELECTION_REQUIRED` | "请先选择工作流插件" | 「选择工作流」按钮 |
| `PLUGIN_VERSION_UNAVAILABLE` | "工作流版本不可用" | 「更换版本」按钮 |
| `DESK_CONFIG_INVALID` | "Desk 配置缺失或未激活" | 展示配置 owner + 「查看配置」 |
| `DESK_UNAVAILABLE` | "Desk 暂时不可访问" | 「重试」按钮（保留输入） |
| `WORKFLOW_PERMISSION_DENIED` | "权限不足" | 「申请授权」或「选择其他插件」 |
| `AGENT_EXECUTION_FAILED` | "运行失败" | 「重试」按钮（同版本新 run） |
| `OUTPUT_VALIDATION_FAILED` | "结果格式不符合预期" | 「重试」或「更换工作流」 |
| `RUNTIME_PLUGIN_NOT_READY` | "运行时插件未就绪" | 「等待物化」或「联系管理员」 |
| `BINDING_REVISION_CONFLICT` | "工作流选择已被修改" | 「刷新」按钮 |
| `IDEMPOTENCY_CONFLICT` | "重复请求" | 「查看运行状态」 |

4.2 错误卡片设计：
- 错误图标 + 标题
- 安全文案（无堆栈/路径/prompt/secret）
- `workflow_run_id` / `operation_id`（小字，用于诊断）
- 恢复动作按钮（1-2 个主操作）
- 折叠的「详细信息」（仅展示非敏感的技术摘要）

4.3 重试流程：
- 点击「重试」→ 携带 `idempotency_key` 创建新 run
- 默认沿用原 `deck_plugin_version` + `desk_config_snapshot_id`
- 显示新 `workflow_run_id`

### 步骤 5：历史来源追溯

5.1 在故事/角色/场景数据表和 Review Panel 中展示来源：
- `workflow_run_id`（可点击跳转运行详情）
- `deck_plugin_id` + `deck_plugin_version`
- `desk_config_snapshot_id`（脱敏摘要）
- 生成时间
- 运行状态（完成/失败）

5.2 运行详情弹窗：
- 不可变来源字段（只读）
- 运行状态历史（时间线）
- 结果引用
- 重试链（`retry_of_run_id` 追溯）

---

## 5. 涉及文件路径

### 前端（新增/修改）

```
frontend/src/components/story-workspace/
  workflow/
    WorkflowContextBar.tsx           -- 工作流上下文条（新增）
    PreflightProgressPanel.tsx       -- 预检进度面板（新增）
    WorkflowRunStatusPanel.tsx       -- 运行状态面板（新增）
    WorkflowErrorCard.tsx            -- 错误恢复卡片（新增）
    WorkflowRunTimeline.tsx          -- 运行时间线（新增）
    ProvenanceBadge.tsx              -- 来源追溯标签（新增）
    index.ts

frontend/src/hooks/
  useWorkflowPreflight.ts          -- preflight 状态管理（新增）
  useWorkflowRun.ts                -- run 状态管理（新增）
  useWorkflowEvents.ts             -- SSE 事件消费（新增）

frontend/src/api/
  storyWorkspaceApi.ts             -- story-workspace API（新增/扩展）

frontend/src/components/story-workspace/layout/
  StoryWorkspaceLayout.tsx         -- 集成上下文条（修改）
  StoryWorkspaceReviewPanel.tsx    -- 集成来源追溯（修改）
```

### 后端 API 消费（由 BackendTaskAgent 提供）

```
POST /api/story-workspace/workflow-preflights
GET  /api/story-workspace/workflow-preflights/{id}
POST /api/story-workspace/workflow-runs
GET  /api/story-workspace/workflow-runs/{workflow_run_id}
POST /api/story-workspace/workflow-runs/{workflow_run_id}/retry
POST /api/story-workspace/workflow-runs/{workflow_run_id}/cancel
```

---

## 6. 输入 / 输出说明

### 输入

| 来源 | 内容 | 格式 |
|---|---|---|
| 后端 API | 当前 binding | `DeckPluginBinding` |
| 后端 API | Preflight 状态 | `WorkflowPreflight` |
| 后端 API | Run 状态 | `WorkflowRun` |
| 后端 SSE | 事件流 | `workflow.run.status_changed` 等 |
| 用户交互 | 开始运行 / 取消 / 重试 | mutation 请求 |

### 输出

| 去向 | 内容 | 格式 |
|---|---|---|
| 后端 API | preflight / run 请求 | POST 请求 |
| UI | 状态面板、进度、错误、来源 | React 组件 |

---

## 7. 依赖项

| 依赖 | 状态 | 说明 |
|---|---|---|
| `DECK-006` | 需稳定 | Preflight 服务 |
| `DECK-007` | 需稳定 | Workflow Run 服务 |
| `DECK-005` | 需稳定 | binding 选择 |
| `task_202e` | 已存在 | Dashboard 基础 |
| `task_202a`~`task_202f` | 已存在 | story-workspace 布局组件 |
| 后端 API | 由后端 task 文档定义 | TaskDesignAgent 引用合同，前端实现消费；§14.3 逻辑路由 |

---

## 8. 测试策略

1. **状态渲染测试**：
   - 各状态（未选择/不可用/预检中/运行中/待审阅/失败/完成）正确渲染
   - 状态切换动画平滑

2. **Preflight 进度测试**：
   - 8 步检查顺序展示
   - 失败时停止并聚焦错误
   - 通过时展示「开始运行」

3. **错误恢复测试**：
   - 各 error_code 映射正确文案和动作
   - 重试创建新 run
   - 取消运行发送 cancel 请求

4. **事件处理测试**：
   - SSE 事件驱动状态更新
   - 重复事件去重
   - 顺序保证

5. **来源追溯测试**：
   - 数据表展示 `workflow_run_id`
   - 点击跳转运行详情
   - 重试链正确追溯

6. **E2E 测试**：
   - 选择工作流 → preflight → 运行 → 审阅 → 重试 完整流程

---

## 9. 完成标志

- [ ] Dashboard 工作流上下文条展示 Deck 插件名称/版本、工作流摘要、Desk 就绪标记
- [ ] 各状态（未选择/不可用/Desk 未就绪/预检中/运行中/待审阅/失败/完成）均有明确 UI 表现
- [ ] Preflight 进度可观察（8 步检查，选择器只读 + Loading）
- [ ] 运行中展示步骤进度与 `workflow_run_id`
- [ ] 失败状态展示失败步骤/错误摘要和恢复动作
- [ ] 历史剧本可追溯到 `workflow_run_id`、`deck_plugin_version` 与 `desk_config_snapshot_id`
- [ ] 结构化错误码映射为用户可理解的恢复入口
- [ ] 单元测试/E2E 测试覆盖各状态渲染、错误恢复交互
- [ ] 与 story-workspace 既有布局、审阅 UI 增量集成，不推翻既有设计
- [ ] Voice chat → run 的 UX 文案和展示方式保持未冻结，使用默认假设占位 `[待 DECK-020 决策]`

---

## 10. 风险提示

| 风险 | 等级 | 缓解 |
|---|---|---|
| 与既有布局集成复杂度 | 低 | 增量添加，不修改三栏骨架 |
| SSE 事件基础设施 | 中 | 复用现有 claude-agent SSE 模式；无 SSE 时降级为轮询 |
| DECK-016 未决（物理服务边界） | 中 | 按逻辑合同消费 API；物理拆分后 gateway 层适配 |
| DECK-017 未决（marketplace 签名/digest） | 低 | 本 task 不直接处理 manifest 发布；runtime lock 完整性由后端校验 |
| DECK-018 未决（多节点 runtime） | 中 | 默认假设：后台创建 run-scoped session；UI 展示来源链接；多节点决策后 readiness 按 environment 聚合 |
| DECK-019 未决（安全撤销） | 中 | 默认假设：普通禁用不终止；安全撤销允许强制终止并审计；运行中状态可能收到强制取消事件 |
| DECK-020 未决（Voice chat → run UX） | 中 | **Voice chat → run 的 UX 文案和展示方式保持未冻结**；当前使用默认假设（后台创建 run-scoped session，展示来源链接）；冻结 gate：产品 owner 确认（见下方 §14） |
| 错误文案安全 | 低 | 只展示安全文案；堆栈/secret 只进受限日志 |
| 状态机复杂 | 低 | 严格按设计稿 §11.3 状态机；不自行添加状态 |

---

## 11. 允许修改范围与禁止修改范围

### 允许修改
- `frontend/src/components/story-workspace/workflow/` 目录（新建）
- `frontend/src/hooks/useWorkflowPreflight.ts` 等（新建）
- `frontend/src/api/storyWorkspaceApi.ts`（新建/扩展）
- `frontend/src/components/story-workspace/layout/`（增量集成）

### 禁止修改
- `docs/design/`、`docs/issue/`、`docs/stage/`、`docs/exec/`
- `docs/task/TASK-REQUIREMENT-FORMAT.md`
- 后端 task 文档（后端实现 Agent 负责）
- 任何实现代码（本阶段为 task 规划）
- story-workspace 既有三栏布局骨架
- 数据表渲染逻辑（task_202c）
- Review Panel 审阅语义（task_202d）

---

## 12. 设计决策引用

- `DECK-DEC-005`: 选择仅影响下一次运行
- `DECK-DEC-006`: run-scoped session
- `DECK-DEC-008`: 重试创建新 run
- `DECK-DEC-011`: 预检失败禁止启动 Agent
- `DEC-010` (SUO-215): 单次运行锁定版本
- `DEC-011` (SUO-215): 预检未通过禁止启动 Agent
- `DEC-014` (SUO-215): 重试默认沿用固定版本

---

## 13. 未决项与默认假设

| 未决项 | 默认假设 | 影响 |
|---|---|---|
| DECK-016 物理服务边界 | 逻辑合同先行，gateway 聚合 | API 路径可能随物理拆分调整 |
| DECK-017 marketplace 签名/digest | 无 digest 不标 production-ready | 来源追溯中 runtime lock 完整性由后端校验 |
| DECK-018 多节点 runtime | 单节点 persistent 默认假设 | readiness 展示按 environment 聚合；多节点决策后适配 |
| DECK-019 安全撤销 | 普通禁用不终止；安全撤销允许强制终止并审计 | 运行中状态可能收到强制取消事件 |
| DECK-020 Voice chat → run UX | 后台创建 run-scoped session，展示来源链接 `[文案未冻结 — 待 DECK-020 决策]` | 上下文条需展示来源关系；Voice chat 发起 workflow run 的 UX 流程待产品 owner 确认 |
| SSE vs 轮询 | 优先 SSE，降级轮询 | 事件消费实现需兼容两者 |
| 步骤进度展示 | 按 manifest steps 展示 | 需要 manifest 中 steps 定义 |

---

## 14. DECK-020 Voice chat → run UX 文案冻结 gate

> **状态**：未冻结（默认假设下可推进，UI 文案冻结前必须解决）

| 项 | 说明 |
|---|---|
| 当前默认假设 | 后台创建 run-scoped session 并展示来源链接 |
| 当前 task 影响 | WorkflowContextBar 的 "运行" 状态展示和来源追溯为默认假设行为，非最终 UX |
| 冻结 gate | 产品 owner 确认 Voice chat 发起 workflow run 的 UX 流程、run-scoped session 展示方式、来源链接文案和位置 |
| 冻结 owner | `@CEOOrchestrator` 路由产品 owner |
| 下游影响 | DECK-009 (run-scoped session)、task_212 (Deck Editor 生效提示) |
| 本 task 处理 | 使用默认假设文案占位，明确标注 `[文案未冻结]`，待 DECK-020 决策后统一替换 |

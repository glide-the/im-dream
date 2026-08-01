# Task: Story Workspace 工作流状态与错误恢复体验

> **Task ID**: `task_213_frontend_story_workspace_status`
> **源 Issue**: `DECK-012` (from `SUO-223` / `SUO-218`)
> **Readiness 修订 Issue**: [SUO-324](/SUO/issues/SUO-324)
> **类型 / Domain**: `frontend`（domain 仅用于分类，不代表执行 Agent 身份）
> **优先级**: `P1`
> **生成日期**: 2026-08-01
> **状态**: `pending_stage_recheck`
> **唯一执行责任人**: `ExecTaskAgent`
> **Stage 映射**: Stage 3 / Wave 1（独立 execute Issue、独立 checkout、独立验收）

---

## 1. 任务标题

DECK-012: Story Workspace 工作流状态与错误恢复体验

---

## 2. 关联 Issue

| 关联 | ID | 说明 |
|---|---|---|
| 源 Issue | `DECK-012` | Story Workspace 工作流状态与错误恢复体验 |
| Readiness 修订 | `SUO-324` | 消除未来 execute 写入边界与冻结决策状态冲突 |
| 父 Issue | `SUO-217` | 组织 Deck 插件业务设计与 ClaudeAgent 交互方案分派 |
| Design Issue | `SUO-218` | Voice Decks × Ink Dream Deck Plugin 与 ClaudeAgent 集成设计 |
| Issue 清单 | `SUO-223` | Deck Plugin 前端/后端 Issue 拆解 |
| 上游 design | `docs/design/deck-plugin-voice-ink-dream-integration.md` §13.1 | 前端负责范围 |
| 上游 layout | `docs/design/story-workspace/story-workspace-layout-design.md` §2.3, §4.5 | 既有布局设计 |
| 上游 delta | `docs/design/deck/deck-integration-delta.md` §7.2 | 工作流运行状态 |

---

## 3. 任务目标

实现 story-workspace 中工作流执行状态的完整展示和错误恢复体验：

1. Dashboard/创作入口展示工作流上下文条（Deck 插件、Deck 运行配置状态、运行进度）。
2. 覆盖所有运行状态：未选择、不可用、Deck 运行配置未就绪、预检中、运行中、待审阅、失败、完成。
3. Preflight 进度可观察，失败时展示结构化错误和恢复入口。
4. 运行中展示步骤进度与 `workflow_run_id`。
5. 历史剧本可追溯来源（`workflow_run_id`、`deck_plugin_version`、`deck_runtime_snapshot_id`）。
6. 结构化错误码映射为用户可理解的恢复动作。

本 task 与 story-workspace 既有布局、审阅 UI 增量集成，不推翻既有设计。

未来实现仅由 `ExecTaskAgent` 在本 task 的独立 execute Issue 中执行；`frontend` 仅是 domain。本 task 不与其他 Stage 3/4 task 合并 checkout 或共享正式报告。

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
│  🧩 悬疑短剧工作流 v3.1.0  │  Deck 配置: ✅ Ready │ 运行: ⏳ 预检中...  │
│  [更换工作流]              │  [查看配置]      │  [取消]               │
└─────────────────────────────────────────────────────────────────────┘
```

1.2 展示内容：
- 当前绑定的 Deck Plugin：`display_name` + `deck_plugin_version`
- Deck 运行配置就绪状态：基于 `deck_runtime_snapshot_id` 的校验结果
- 当前运行状态：
  - 未选择插件 → "未选择工作流"
  - 插件不可用 → "工作流不可用"
  - Deck 运行配置未就绪 → "配置未就绪"
  - 预检中 → "预检中…" + 进度
  - 运行中 → "运行中…" + 步骤进度
  - 待审阅 → "待审阅"
  - 失败 → "运行失败" + 错误摘要
  - 完成 → "已完成"

1.3 操作按钮（按状态条件展示）：
- 「更换工作流」→ 跳转到 Deck 选择
- 「查看配置」→ 展示 Deck 运行配置摘要（脱敏；不展示 prompt、secret 或完整配置）
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
  4. host、ClaudeAgent、Claude Code、Deck runtime contract 兼容性
  5. 能力交集与来源策略
  6. 通过 Deck 创建或复用不可变 `deck_runtime_snapshot_id`
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
| `deck_runtime_config_not_ready` | 警告卡片 | "Deck 运行配置未就绪" + Deck owner + 修复入口 |
| `preflight_checking` | 进度面板 | PreflightProgressPanel |
| `running` | 运行面板 | 步骤进度条、当前步骤、已运行时间、`workflow_run_id` |
| `pending_review` | 成功面板 | 结果摘要 + 「开始审阅」按钮（“待审阅”仅为 UI 文案） |
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
| `DECK_PLUGIN_UNAVAILABLE` | "工作流版本不可用" | 「更换版本」按钮 |
| `DECK_RUNTIME_CONFIG_INVALID` | "Deck 运行配置缺失、未激活或过期" | 展示 Deck owner + 「查看配置」 |
| `DECK_RUNTIME_CONFIG_INCOMPATIBLE` | "Deck 运行快照合同不兼容" | 「选择兼容配置或版本」 |
| `DECK_RUNTIME_CONFIG_UNAVAILABLE` | "Deck 运行配置暂时不可访问" | 「重试」按钮（保留输入并沿用幂等语义） |
| `WORKFLOW_PERMISSION_DENIED` | "权限不足" | 「申请授权」或「选择其他插件」 |
| `AGENT_EXECUTION_FAILED` | "运行失败" | 「重试」按钮（同版本新 run） |
| `OUTPUT_CONTRACT_INVALID` | "结果格式不符合预期" | 「重试」或「更换工作流」 |
| `CONFIG_VERSION_DRIFT` | "配置版本已变化" | 保持已锁来源或由用户显式升级后创建新运行 |
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
- 默认沿用原 `deck_plugin_version` + `deck_runtime_snapshot_id` + `runtime_plugin_lock_id`
- 显示新 `workflow_run_id`

### 步骤 5：历史来源追溯

5.1 在故事/角色/场景数据表和 Review Panel 中展示来源：
- `workflow_run_id`（可点击跳转运行详情）
- `deck_plugin_id` + `deck_plugin_version`
- `deck_runtime_profile_id`（仅 ID / 版本摘要）
- `deck_runtime_snapshot_id`（受控引用 + 脱敏摘要）
- 生成时间
- 运行状态（完成/失败）

5.2 运行详情弹窗：
- 不可变来源字段（只读）
- 运行状态历史（时间线）
- 结果引用
- 重试链（`retry_of_run_id` 追溯）
- 有来源权限时展示「来源：Voice {voice_display_name} · {source_message_time}」与「返回来源对话」；不得回显消息正文、system prompt、secret 或 session settings
- 无来源权限时只展示「来源：Voice 对话（无权查看）」，隐藏来源名称、时间和返回链接

---

## 5. 涉及文件路径

以下十八个路径是未来 execute 的完整实现/测试闭集；目录名不构成额外授权：

| 路径 | 动作 | 最小变更 |
|---|---|---|
| `frontend/src/components/story-workspace/workflow/WorkflowContextBar.tsx` | 新建 | 工作流上下文条 |
| `frontend/src/components/story-workspace/workflow/PreflightProgressPanel.tsx` | 新建 | 预检进度面板 |
| `frontend/src/components/story-workspace/workflow/WorkflowRunStatusPanel.tsx` | 新建 | 运行状态面板 |
| `frontend/src/components/story-workspace/workflow/WorkflowErrorCard.tsx` | 新建 | 错误恢复卡片 |
| `frontend/src/components/story-workspace/workflow/WorkflowRunTimeline.tsx` | 新建 | 运行时间线 |
| `frontend/src/components/story-workspace/workflow/ProvenanceBadge.tsx` | 新建 | 来源与权限降级展示 |
| `frontend/src/components/story-workspace/workflow/index.ts` | 新建 | 受控导出 |
| `frontend/src/hooks/useWorkflowPreflight.ts` | 新建 | preflight 状态管理 |
| `frontend/src/hooks/useWorkflowRun.ts` | 新建 | run 状态管理 |
| `frontend/src/hooks/useWorkflowEvents.ts` | 新建 | SSE/轮询事件消费 |
| `frontend/src/api/storyWorkspaceApi.ts` | 新建/扩展 | story-workspace API client |
| `frontend/src/components/story-workspace/layout/StoryWorkspaceLayout.tsx` | 修改 | 仅集成上下文条 |
| `frontend/src/components/story-workspace/layout/StoryWorkspaceReviewPanel.tsx` | 修改 | 仅集成来源追溯 |
| `frontend/src/components/story-workspace/layout/StoryWorkspaceLayout.css` | 修改 | 仅新增本 task workflow 状态、来源与权限降级样式，不改三栏几何骨架 |
| `frontend/src/components/story-workspace/workflow/WorkflowRunStatusPanel.test.tsx` | 条件新建 | 已有兼容 runner 时覆盖状态、来源与权限降级渲染 |
| `frontend/src/components/story-workspace/workflow/PreflightProgressPanel.test.tsx` | 条件新建 | 已有兼容 runner 时覆盖八步 preflight 与失败停止 |
| `frontend/src/components/story-workspace/workflow/WorkflowErrorCard.test.tsx` | 条件新建 | 已有兼容 runner 时覆盖错误码、恢复入口与脱敏 |
| `frontend/src/hooks/useWorkflowEvents.test.ts` | 条件新建 | 已有兼容 runner 时覆盖事件去重、顺序和轮询降级 |

四个测试路径是闭集内的条件授权：仅当 §8 runner 发现命令返回非空且现有依赖可直接运行时创建；若仍无 runner，则不得生成不可执行测试文件，改以浏览器 E2E/人工证据验收。这不授权修改 `package.json`、依赖锁或测试配置。

### 后端 API 消费（由 backend domain 前置 task 提供；本 task 只读消费）

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

0. **命令发现与静态验证**：
   - execute Issue 先读取 `frontend/package.json` 的 `scripts` 与现有测试文件命名，逐字回填实际 runner、版本和命令；不得凭空假设 Vitest/Jest，也不得为本 task 新增测试框架、依赖锁或全局配置。
   - 当前仓库已发现 `build`、`lint`，未发现 `test` script；从仓库根执行的最低静态验证为 `npm --prefix frontend run build`、`npm --prefix frontend run lint` 和 `git diff --check`。runner 发现命令固定为 `node -p "require('./frontend/package.json').scripts?.test ?? ''"`。若 execute 时仍无 test runner，必须在 execute Issue/正式报告记录发现输出，并以下述人工/E2E 场景补证；不得伪报单元测试已执行。

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
   - 验证有权限来源可返回原 Voice 对话；无权限来源只显示批准的脱敏文案
   - 逐项保留页面状态、网络请求/响应、事件与权限降级证据；正式命令和结果写入唯一 exec 报告

---

## 9. 完成标志

- [ ] Dashboard 工作流上下文条展示 Deck 插件名称/版本、工作流摘要、Deck 运行配置就绪标记
- [ ] 各状态（未选择/不可用/Deck 运行配置未就绪/预检中/运行中/待审阅/失败/完成）均有明确 UI 表现
- [ ] Preflight 进度可观察（8 步检查，选择器只读 + Loading）
- [ ] 运行中展示步骤进度与 `workflow_run_id`
- [ ] 失败状态展示失败步骤/错误摘要和恢复动作
- [ ] 历史剧本可追溯到 `workflow_run_id`、`deck_plugin_version`、`deck_runtime_snapshot_id` 与 `runtime_plugin_lock_id`
- [ ] 结构化错误码映射为用户可理解的恢复入口
- [ ] 已有 runner 时自动化测试覆盖状态/错误/事件；无 runner 时浏览器 E2E/人工证据覆盖同等场景并记录发现结果
- [ ] 与 story-workspace 既有布局、审阅 UI 增量集成，不推翻既有设计
- [ ] run 详情按 §14 已批准合同展示双向来源；无来源权限时只显示「来源：Voice 对话（无权查看）」且不泄露名称、时间、正文或链接
- [ ] 实际变更只位于 §5 十八个实现/测试路径及唯一正式报告路径
- [ ] execute Issue/正式报告逐项回填验证命令、结果、验收、diff 与回滚说明；缺失 runner 时按 §8 记录发现证据

---

## 10. 风险提示

| 风险 | 等级 | 缓解 |
|---|---|---|
| 与既有布局集成复杂度 | 低 | 增量添加，不修改三栏骨架 |
| SSE 事件基础设施 | 中 | 复用现有 claude-agent SSE 模式；无 SSE 时降级为轮询 |
| DECK-016 已冻结（物理服务边界） | 低 | 只消费逻辑 API；无状态 gateway 只聚合/路由，不在前端假设新业务服务或写 owner |
| DECK-017 条件冻结（marketplace 签名/digest） | 低 | runtime lock 完整性由后端校验；未验证制品不得显示为 production-ready |
| DECK-018 已冻结但 rollout 限域 | 中 | 当前仅单节点 persistent 通过；多节点/临时 runtime 继续 fail closed，run-ready 只信任 session load receipt |
| DECK-019 已冻结（安全撤销） | 中 | DISABLE 不终止既有 run；REVOKE/EMERGENCY 可触发确定性安全取消；Stage 4 production Gate 仍等待真实 evidence pack |
| DECK-020 已冻结（Voice chat → run UX） | 中 | 严格使用 §14 批准的显式启动、独立 run/session、双向来源与权限降级合同 |
| 错误文案安全 | 低 | 只展示安全文案；堆栈/secret 只进受限日志 |
| 状态机复杂 | 低 | 严格按设计稿 §11.3 状态机；不自行添加状态 |

---

## 11. 允许修改范围与禁止修改范围

### 11.1 未来 execute 允许闭集

- §5 列出的十八个 frontend 实现/测试路径；每个路径仅限表中最小变更。
- `docs/exec/exec_task_213_frontend_story_workspace_status.md`：仅允许 `ExecTaskAgent` 写入本 task 的唯一正式执行报告。

以上十九个路径可直接复制到 execute 模板（十八个 frontend 路径 + 一个正式报告例外）；未列出的路径默认禁止。

### 11.2 未来 execute 禁止范围

- `docs/exec/` 下除 `docs/exec/exec_task_213_frontend_story_workspace_status.md` 之外的全部路径。
- `docs/design/`、`docs/issue/`、`docs/task/`、`docs/stage/`、`backend/`、依赖锁、测试/构建配置、生成物及 §11.1 未列出的任何实现或测试文件。
- story-workspace 既有三栏布局骨架、数据表渲染逻辑（task_202c）和 Review Panel 审阅语义（task_202d）。
- Voice chat 触发按钮或 `WorkflowRunLinkCard` 实现；本 task 只消费并展示 run 侧来源合同，不扩大到 chat 侧路径。
- 前端自行推进 Preflight/Run 状态机、伪造服务端来源/权限结果、泄露 prompt/secret/session settings，或覆盖共享工作树既有差异。

### 11.3 当前修订阶段约束

[SUO-324](/SUO/issues/SUO-324) 只修订 task 合同，不授权实现 §11.1。未来 execute 必须由 `ExecTaskAgent` 在独立 Issue checkout 后实施；完成后由 StagePlanner 独立重跑 readiness，不得由本 task 自行宣布进入 execute 或通过 Stage 3 Gate。

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

## 13. 决策状态与剩余实现假设

| 决策/事项 | 权威状态或合同 | 本 task 影响 |
|---|---|---|
| DECK-016 物理服务边界 | `frozen`：三域单写、无状态 gateway 聚合；不新增第三业务服务 | 只消费逻辑 API，物理拆分不得改变来源/状态语义 |
| DECK-017 marketplace 签名/digest | `conditional_frozen`：生产完整性仍受阻 | 来源追溯只展示服务端验证结果，不自行验签或放行 |
| DECK-018 runtime 分发 | `frozen` 设计；当前仅单节点 persistent rollout 限域通过 | 多节点/临时 runtime 不得显示 ready；节点/会话来源按服务端 receipt 展示 |
| DECK-019 安全撤销 | `frozen`：DISABLE 不终止；REVOKE 60 秒默认/300 秒上限后硬停；EMERGENCY 零 grace | 运行 UI 消费 `cancelling/cancelled/failed` 与 `SECURITY_REVOCATION`，不得显示 `completed` |
| DECK-020 Voice chat → run UX | `frozen`；批准合同见 §14 | 本 task 实现 run 详情的来源/返回与权限降级侧，不实现 chat 卡片 |
| SSE vs 轮询 | 实现选择仍可由现有基础设施决定 | 优先 SSE、可降级轮询；两者都要按 event_id/aggregate_version 保序去重 |
| 步骤进度展示 | 按 manifest steps 展示 | 不自行发明服务端未声明步骤 |

---

## 14. DECK-020 Voice chat → run UX 已冻结合同

> **状态**：`frozen`；依据 [SUO-254](/SUO/issues/SUO-254) 的 CEO `approve`，Stage 3 UI/文案设计 Gate 已通过。设计冻结不代替 execute、E2E 或发布验收。

| 项 | 已批准合同 / 本 task 边界 |
|---|---|
| 启动方式 | 仅用户点击「创建工作流运行」时启动；普通聊天消息不得静默触发 |
| 原 chat | 保持原位置并插入/更新 `WorkflowRunLinkCard`，不得自动跳转 |
| run/session | 创建独立 `workflow_run_id` 与 run-scoped `agent_session_id`，不得复用 Voice `thread_id`；session 不进入普通 Chat 历史，重试创建新 run/session |
| 双向来源 | chat 卡片主操作「查看运行」打开 `/story-workspace/runs/{workflow_run_id}`；run 详情有权限时显示来源并提供「返回来源对话」 |
| 权限降级 | 无来源权限时固定显示「来源：Voice 对话（无权查看）」，隐藏来源名称、时间、正文和返回链接 |
| 批准文案 | 入口「创建工作流运行」；卡片标题「已创建独立工作流运行」；说明「本次运行使用锁定的 Deck 工作流与 ClaudeAgent 运行时；当前 Voice 对话仅作为来源。」；主操作「查看运行」 |
| 本 task 实现 | 仅实现 story-workspace run 侧状态、来源、返回链接与权限降级；Voice chat 触发按钮/卡片不在 §11.1 闭集内 |
| 必留 E2E 证据 | 正确 run 跳转、有权限返回原对话、run/session 与 Voice thread 隔离、无权限脱敏、重试形成新 run/session 与可审计链 |

---

## 15. 回滚边界

- 只回退 §11.1 中本 task 新增的 workflow 组件、hooks、client、测试，以及两个 layout 文件的最小集成区段。
- 不回滚或删除后端 Workflow Run、Preflight、session、结果或来源记录；回滚后保留既有三栏布局、数据表和 Review Panel 审阅语义。
- 若后端合同不可用，UI 回到只读/不可用安全状态并保留来源权限边界，不伪造运行成功、来源或返回链接。
- 回滚前后均执行 §8 的静态验证与关键人工场景，并在 `docs/exec/exec_task_213_frontend_story_workspace_status.md` 记录触发条件、变更路径、验证结果与剩余影响；正式报告本身不得在代码回滚中删除。

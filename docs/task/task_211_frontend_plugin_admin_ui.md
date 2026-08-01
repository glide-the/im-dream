# Task: 前端管理端插件目录与安装状态 UI

> **Task ID**: `task_211_frontend_plugin_admin_ui`
> **源 Issue**: `DECK-010` (from `SUO-223` / `SUO-218`)
> **类型**: `frontend`（**TaskDesignAgent 负责 task 设计**，前端实现 Agent 负责代码实现）
> **优先级**: `P1`
> **生成日期**: 2026-08-01
> **状态**: `draft`

---

## 1. 任务标题

DECK-010: 前端管理端插件目录与安装状态 UI

---

## 2. 关联 Issue

| 关联 | ID | 说明 |
|---|---|---|
| 源 Issue | `DECK-010` | 前端管理端插件目录与安装状态 UI |
| 父 Issue | `SUO-217` | 组织 Deck 插件业务设计与 ClaudeAgent 交互方案分派 |
| Design Issue | `SUO-218` | Voice Decks × Ink Dream Deck Plugin 与 ClaudeAgent 集成设计 |
| Issue 清单 | `SUO-223` | Deck Plugin 前端/后端 Issue 拆解 |
| 上游 design | `docs/design/deck-plugin-voice-ink-dream-integration.md` §16.1, §16.2 | UI 复用 Paperclip Settings → Plugins 的边界 |

---

## 3. 任务目标

实现管理端的 Deck Plugin 目录和安装状态 UI，复用 Paperclip Settings → Plugins 的管理体验，但显式区分三类插件：

1. **Deck 工作流插件**（业务工作流 release，由 `deck_plugin_id` + `deck_plugin_version` 标识）
2. **ClaudeAgent 运行时插件**（运行时能力包，由 `claude_code_plugin_id` + `resolved_version` + `artifact_digest` 标识）
3. **Paperclip Plugin**（仅作管理基线参考，本文不直接管理；使用 `pluginKey` / `PluginRecord.id` 标识）

> **命名隔离原则**：UI 必须显示"Deck 工作流插件"和"ClaudeAgent 运行时插件"两类标签，不能只写"插件"。禁止在跨域 API 中使用无前缀的 `plugin_id`、`plugin_version` 表达两类对象。

展示安装项、精确版本、三维状态（declared/materialized/loadable）、能力、兼容、健康和错误摘要。支持安装、启停、升级、卸载动作。

### 3.1 UI 状态适用性矩阵

| 状态组 | 适用性 | 本 task 的 UI 边界 | 依赖方与原因 |
|---|---|---|---|
| `installation/compatibility` | 适用（核心） | 展示 installation 生命周期、兼容性、capability 交集与 runtime readiness，并提供安装、启停、升级、回滚、卸载入口 | `DECK-003` / `DECK-004` 提供权威状态、权限裁决和 mutation 结果；前端不自行计算兼容性或推进后端状态机 |
| `binding/version` | 部分适用 | 展示安装版本、`default_version`、升级目标与版本差异；单个 Deck 的 binding 选择、`binding_revision` 和并发保存 N/A | `DECK-005`、`task_210_shared_deck_plugin_binding` 与 `task_212_frontend_deck_editor_plugin_binding` 负责 Deck binding；管理端不能暗示可改写某个 Deck 的选择 |
| `preflight/run` | N/A（不在本 task 实现） | runtime readiness 和最近 run 引用只作管理/审计摘要；不触发 preflight，不展示或控制 Workflow Run 生命周期 | `DECK-006` / `DECK-007` 提供执行服务，`task_213_frontend_story_workspace_status` 负责 preflight/run UI |
| `error/recovery` | 适用（管理态） | 展示安装、兼容性、物化、加载和管理动作的安全错误，并提供 reconcile、重试、回滚或申请授权入口；Workflow Run 错误恢复 N/A | `DECK-003` / `DECK-004` / `DECK-014` 提供错误合同；执行态错误与重试由 `task_213_frontend_story_workspace_status` 承担 |

---

## 4. 实现步骤

### 步骤 1：管理端页面路由与入口

1.1 在 Settings 或独立管理区域新增「插件管理」入口：
- 路由建议：`/settings/plugins` 或 `/admin/plugins`
- 入口标签：「Deck 工作流插件」（避免笼统写「插件」）

1.2 页面布局：
- 左侧/顶部：插件分类标签切换（Deck 工作流插件 / ClaudeAgent 运行时插件）
- 主区域：插件列表
- 详情抽屉/弹窗：选中插件的 Configuration / Status

### 步骤 2：插件列表组件

2.1 实现 `PluginAdminList` 组件：
- 列表项展示：
  - `display_name` + `deck_plugin_id`
  - 精确版本 `deck_plugin_version`
  - 来源（marketplace / 本地 / 受控路径）
  - 三维状态标签（见下方状态映射）
  - 能力摘要（capability 数量 / 关键能力）
  - 兼容性指示（通过/不兼容 / 待检查）
  - 健康状态（正常 / 上次错误 / 物化失败）
  - 最近运行时间

2.2 状态标签映射（设计稿 §7.1 三维状态）：

| declaration | materialization | activation | UI 展示 |
|---|---|---|---|
| declared | materialized | loadable | ✅ Ready |
| declared | materialized | loaded | ✅ Loaded |
| declared | materializing | — | ⏳ Materializing… |
| declared | failed | — | ⚠️ Declared, not materialized |
| declared | materialized | load_failed | ⚠️ Load failed |
| disabled | — | — | 🚫 Disabled |
| undeclared | — | — | ⏸️ Not installed |

2.3 操作按钮（按权限和状态条件展示）：
- Install（未安装时）
- Enable / Disable（ready 时）
- Upgrade（有可用新版本时）
- Rollback（有旧版本可用时）
- Uninstall（非系统插件）
- Reconcile（物化失败时重试）

### 步骤 3：插件详情页/抽屉

3.1 实现 `PluginAdminDetail` 组件，分两个 tab：

**Configuration Tab**：
- manifest 摘要（schema_version、deck_plugin_id、version、author）
- 工作流定义引用
- 输入/输出 schema 版本
- 能力列表（manifest_requested）
- Desk contract 摘要
- 运行时依赖（Claude Code Plugin 列表 + 版本约束）

**Status Tab**：
- 安装状态历史（时间线）
- 三维状态详情
- 能力交集计算结果（effective_capabilities）
- 最近错误摘要（`last_error_code`、`last_error_summary`）
- 最近运行列表
- 操作日志（安装、启停、升级、回滚记录）

3.2 能力扩张升级审批 UI：
- 检测到 `upgrade_pending` 时显示审批入口
- 展示 `capability_diff`（added / removed）
- 管理员确认/拒绝动作

### 步骤 4：安装/升级/卸载交互

4.1 安装流程：
- 选择来源（受控 marketplace / 本地路径 — 仅管理员）
- 输入精确版本
- 确认能力列表
- 提交后显示 operation 进度（`operation_id`）
- 轮询或接收 SSE 事件直到 `ready` 或 `error`

4.2 升级流程：
- 对比当前版本与目标版本差异
- 展示 capability_diff
- 若新增能力 → 进入 `upgrade_pending` 审批
- 目标版本物化完成后切换 default_version

4.3 卸载流程：
- 确认是否存在历史 run 引用
- 软删除（默认）/ 强制 purge（需证明无审计义务）
- 保留历史来源元数据

### 步骤 5：错误与恢复展示

5.1 结构化错误码映射：
- `DECK_PLUGIN_MANIFEST_INVALID` → "插件定义不合法，请联系发布者"
- `RUNTIME_PLUGIN_MATERIALIZATION_FAILED` → "已声明但未物化，点击重试"
- `DECK_HOST_INCOMPATIBLE` → "当前平台版本不兼容，请升级"
- `WORKFLOW_PERMISSION_DENIED` → "权限不足，申请授权"
- 等（完整映射见设计稿 §12.1）

5.2 每个错误展示：
- 安全文案（无堆栈/路径/prompt）
- 失败阶段
- `operation_id` / `run_id`
- 恢复动作入口

---

## 5. 涉及文件路径

### 前端（新增）

```
frontend/src/components/plugin-admin/
  PluginAdminPage.tsx              -- 管理端页面根组件
  PluginAdminList.tsx              -- 插件列表
  PluginAdminListItem.tsx          -- 列表项
  PluginAdminDetail.tsx            -- 详情抽屉/弹窗
  PluginStatusBadge.tsx            -- 三维状态标签
  PluginCapabilityDiff.tsx         -- 能力差异展示
  PluginErrorCard.tsx              -- 错误摘要卡片
  PluginOperationProgress.tsx      -- 操作进度
  index.ts

frontend/src/hooks/
  usePluginInstallations.ts        -- 安装列表查询
  usePluginInstallationDetail.ts   -- 详情查询
  usePluginOperation.ts            -- 操作（安装/升级/卸载）
  usePluginRuntimeReadiness.ts     -- runtime readiness 查询

frontend/src/api/
  deckPluginAdminApi.ts            -- 管理端 API 客户端
```

### 后端 API 消费（由 BackendTaskAgent 提供）

```
GET  /api/deck-plugins/installations
POST /api/deck-plugins/install
GET  /api/deck-plugins/{deck_plugin_id}/versions/{version}
POST /api/deck-plugins/{deck_plugin_id}/enable
POST /api/deck-plugins/{deck_plugin_id}/disable
POST /api/deck-plugins/{deck_plugin_id}/upgrade
POST /api/deck-plugins/{deck_plugin_id}/rollback
GET  /api/deck-plugins/{deck_plugin_id}/runtime-readiness
POST /api/deck-plugins/{deck_plugin_id}/reconcile
```

---

## 6. 输入 / 输出说明

### 输入

| 来源 | 内容 | 格式 |
|---|---|---|
| 后端 API | 安装列表 | `DeckPluginInstallation[]` |
| 后端 API | 版本详情 | `DeckPluginManifestV1` + `DeckRuntimePluginLock` |
| 后端 API | runtime readiness | 三维状态 |
| 后端 SSE | 操作进度事件 | `deck_plugin.installation.status_changed` |
| 用户交互 | 安装/启停/升级/卸载 | mutation 请求 |

### 输出

| 去向 | 内容 | 格式 |
|---|---|---|
| 后端 API | mutation 请求 | POST/PUT 请求 |
| UI | 列表、详情、状态、错误 | React 组件 |
| UI | 操作进度 | 进度条 / SSE 事件驱动 |

---

## 7. 依赖项

| 依赖 | 状态 | 说明 |
|---|---|---|
| `DECK-003` | 需稳定 | Installation 生命周期管理 |
| `DECK-004` | 需稳定 | 兼容性判定与能力交集 |
| `DECK-005` | 可选 | binding 选择（管理端与 Deck Editor 独立） |
| 后端管理端 API | 由后端 task 文档定义 | TaskDesignAgent 引用合同，前端实现消费；§14.1 逻辑路由 |
| Paperclip Settings UI | 参考基线 | 复用 UX 原则，不直接 import 类型 |

---

## 8. 测试策略

1. **列表渲染测试**：
   - 各状态标签正确渲染
   - 操作按钮按状态条件展示
   - 权限过滤（非管理员不展示管理动作）

2. **详情页测试**：
   - Configuration / Status tab 切换
   - 能力列表展示
   - 错误摘要展示

3. **操作交互测试**：
   - 安装流程（提交 → 进度 → 完成/失败）
   - 升级审批流程
   - 卸载确认流程

4. **错误处理测试**：
   - 各 error_code 映射正确文案
   - 恢复入口可点击

5. **E2E 测试**：
   - 安装 → 启用 → 升级 → 回滚 → 卸载 完整流程

---

## 9. 完成标志

- [ ] 管理端插件列表页面实现
- [ ] 列表展示名称、来源、精确版本、三维状态、能力、兼容、健康、错误摘要
- [ ] 详情页分 Configuration / Status tab
- [ ] UI 区分「Deck 工作流插件」和「ClaudeAgent 运行时插件」标签
- [ ] 能力扩张升级进入显式审批流程
- [ ] 健康状态和 `last_error` 可观察
- [ ] 管理动作要求实例/插件管理员权限（前端按权限隐藏/禁用）
- [ ] 单元测试/E2E 测试覆盖列表渲染、状态展示、安装/启停交互
- [ ] 不直接复用 Paperclip `PluginRecord.status` 类型

---

## 10. 风险提示

| 风险 | 等级 | 缓解 |
|---|---|---|
| Paperclip Plugin 基线 alpha 状态 | 中 | 只复用 UX 原则，Deck 域维护独立枚举；不直接 import Paperclip `PluginRecord.status` |
| 后端管理端 API 未实现 | 中 | 按设计稿 §14.1 合同消费；差异在 Issue 评论记录 |
| 三维状态展示复杂 | 低 | 提供状态图例和 hover 说明 |
| 多节点 runtime readiness | 中 | 默认按单节点 persistent 展示；DECK-018 决策后适配 |
| DECK-016 未决（物理服务边界） | 中 | 管理端 UI 按逻辑合同消费 API；物理拆分后 gateway 层适配 |
| DECK-017 未决（marketplace 签名/digest） | 中 | 无 digest 的 release 不标 production-ready；UI 展示对应状态标签 |
| DECK-018 未决（多节点 runtime） | 中 | 默认按单节点 persistent 展示 readiness；多节点决策后按 environment 聚合 |
| DECK-019 未决（安全撤销） | 低 | 管理端展示撤销状态与审计入口；强制终止策略待 DECK-019 冻结后适配 |
| DECK-020 未决（Voice chat → run UX） | 低 | 本 task 不涉及 Voice chat 入口；管理端只处理插件生命周期 |

---

## 11. 允许修改范围与禁止修改范围

### 允许修改
- `frontend/src/components/plugin-admin/` 目录（新建）
- `frontend/src/hooks/usePluginInstallations.ts` 等（新建）
- `frontend/src/api/deckPluginAdminApi.ts`（新建）
- Settings / 管理区域路由配置（增量添加入口）

### 禁止修改
- `docs/design/`、`docs/issue/`、`docs/stage/`、`docs/exec/`
- `docs/task/TASK-REQUIREMENT-FORMAT.md`
- 后端 task 文档（后端实现 Agent 负责）
- 任何实现代码（本阶段为 task 规划）
- Paperclip Plugin worker 模型或状态枚举

---

## 12. 设计决策引用

- `DECK-DEC-001`: 三类插件边界
- `DECK-DEC-004`: declared/materialized/loadable 分开记录
- `DECK-DEC-007`: 有效能力取交集
- `DECK-DEC-010`: 复用 Paperclip UX 原则，不直接复用 worker 模型
- `DEC-009` (SUO-215): 职责独立

---

## 13. 未决项与默认假设

| 未决项 | 默认假设 | 影响 |
|---|---|---|
| DECK-016 物理服务边界 | 逻辑合同先行，gateway 聚合 | API 路径可能调整 |
| DECK-017 marketplace 签名 | 无 digest 不标 production-ready | UI 展示对应状态 |
| DECK-018 多节点 runtime | 单节点 persistent | readiness 展示按 environment 聚合 |
| DECK-019 安全撤销 | 普通禁用不终止；安全撤销允许强制终止并审计 | 管理端展示撤销状态与审计入口 |
| DECK-020 Voice chat → run UX | 本 task 不涉及 | 管理端只处理插件生命周期 |
| 管理端路由位置 | Settings → Plugins 子页面 | 产品确认后可调整 |

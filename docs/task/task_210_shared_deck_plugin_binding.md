# Task: Deck 创建/编辑的插件选择与版本绑定（Shared）

> **Task ID**: `task_210_shared_deck_plugin_binding`
> **源 Issue**: `DECK-005` (from `SUO-223` / `SUO-218`)
> **类型**: `shared`（**TaskDesignAgent 主责设计**，后端 binding/API task 合同由已有后端 task 文档定义）
> **优先级**: `P0`
> **生成日期**: 2026-08-01
> **状态**: `draft`

---

## 1. 任务标题

DECK-005: Deck 创建/编辑的插件选择与版本绑定（Shared — **TaskDesignAgent 负责 task 设计**，前后端执行由对应实现 Agent 承担）

---

## 2. 关联 Issue

| 关联 | ID | 说明 |
|---|---|---|
| 源 Issue | `DECK-005` | Deck 创建/编辑的插件选择与版本绑定 |
| 父 Issue | `SUO-217` | 组织 Deck 插件业务设计与 ClaudeAgent 交互方案分派 |
| Design Issue | `SUO-218` | Voice Decks × Ink Dream Deck Plugin 与 ClaudeAgent 集成设计 |
| Issue 清单 | `SUO-223` | Deck Plugin 前端/后端 Issue 拆解 |
| 上游 design | `docs/design/deck-plugin-voice-ink-dream-integration.md` | 主设计稿 |
| 上游 delta | `docs/design/deck/deck-integration-delta.md` | Deck integration 唯一当前 canonical |

---

## 3. 任务目标

实现 Deck 创建/编辑时的**插件选择、版本绑定和保存语义**，确保：

1. Deck Editor 可展示已安装/可用的 Deck Plugin release 列表及状态。
2. 用户选择精确版本后保存产生新的 `binding_revision`，仅影响下一次运行。
3. 通过 `expected_binding_revision` 防止并发覆盖，冲突时返回 `409 BINDING_REVISION_CONFLICT`。
4. 前端负责版本列表 UI、状态展示、选择交互、revision 冲突处理、生效提示。
5. 后端负责 binding 模型、保存校验、revision 并发控制、selection validation 逻辑。
6. **TaskDesignAgent 是 shared task 设计唯一责任人**：负责前后端合同对齐、字段定义、验收条件与依赖梳理；不负责具体代码实现。

> **命名与 UI 标签隔离**：Deck 业务工作流统一显示为「Deck 工作流插件」，只使用 `deck_plugin_id` / `deck_plugin_version`；ClaudeAgent 会话能力包统一显示为「ClaudeAgent 运行时插件」，只使用 `claude_code_plugin_id` / `resolved_version` / `artifact_digest` 及 `declared`、`materialized`、`loadable` 等运行时标签。禁止只显示笼统的「插件」，禁止用 `claude_code_plugin_id` 或运行时标签替代 Deck binding 的业务标识与发布状态。

### 3.1 UI 状态适用性矩阵

| 状态组 | 适用性 | 本 task 的 UI/合同边界 | 依赖方与原因 |
|---|---|---|---|
| `installation/compatibility` | 适用（只读消费） | 版本列表展示 installation、兼容性与不可选原因；selection validation 只消费脱敏摘要，不实现生命周期或兼容性判定 | `DECK-003` / `DECK-004` 提供权威状态与 reason code；管理恢复动作由 `task_211_frontend_plugin_admin_ui` 承担 |
| `binding/version` | 适用（核心） | 展示精确 release、选择并保存、处理 `binding_revision` 冲突，并明确仅影响下一次运行 | `DECK-005` 的 shared 合同；TaskDesignAgent 负责 task 设计，前端消费、后端 task 提供 binding/API 实现 |
| `preflight/run` | N/A（不在本 task 实现） | 仅展示“当前 run 来源不变/下一次运行生效”的只读语义；不触发或展示 preflight、run 状态、取消与重试 | `DECK-006` / `DECK-007` 提供服务，`task_213_frontend_story_workspace_status` 负责执行态 UI；selection validation 不等于权威 preflight |
| `error/recovery` | 部分适用 | 处理列表加载、selection validation、保存失败与 `BINDING_REVISION_CONFLICT` 刷新确认；只提供配置/安装 owner 跳转 | 安装/物化恢复由 `task_211_frontend_plugin_admin_ui` 承担，preflight/run 恢复由 `task_213_frontend_story_workspace_status` 承担，避免暗示本 task 编排这些恢复流程 |

---

## 4. 实现步骤

### 步骤 1：后端 binding 模型与 API 合同（由已有后端 task 文档定义，TaskDesignAgent 引用合同）

> **引用边界**：以下后端模型与 API 合同已在后端 task 文档中定义，本文仅引用消费，不重复定义也不改写。
> - `task_deck_001_backend_manifest-model.md` — Manifest 模型
> - `task_deck_003_backend_installation-lifecycle.md` — Installation 生命周期
> - `task_deck_004_backend_compatibility-capability.md` — 兼容性判定
> - `task_deck_006_backend_workflow-preflight.md` — Preflight 服务
> - `task_deck_014_backend_api-error-codes.md` — API 错误码规范

1.1 定义 `DeckPluginBinding` 数据模型：
```
deck_plugin_binding_id  (PK)
deck_id
workspace_id
creator_id
deck_plugin_id
deck_plugin_version      -- 精确版本，禁止 latest/范围
binding_revision         -- 单调递增整数，乐观锁
status                   -- active | stale
applied_to               -- next_run (仅影响下一次)
created_at / updated_at
```

1.2 实现 API 端点：
- `GET /api/voice-decks/{deck_id}/plugin-binding` — 返回当前 binding/revision
- `PUT /api/voice-decks/{deck_id}/plugin-binding` — 保存精确版本，需传 `expected_binding_revision`
- `POST /api/voice-decks/{deck_id}/plugin-binding/validate` — selection validation，不创建 Workflow Run

1.3 实现 `expected_binding_revision` 乐观锁：
- 不匹配时返回 `409 BINDING_REVISION_CONFLICT`
- 成功返回新 `binding_revision` 和 selection validation 摘要

1.4 实现 selection validation 逻辑（快速校验）：
- release 为 `published`/策略允许的 `deprecated`
- installation 为 `ready`
- 静态兼容性通过（host API、schema、Deck runtime contract）
- 用户有选择权限
- 已知 runtime readiness（不替代 preflight 的权威物化检查）

### 步骤 2：前端 Deck Editor 插件选择区（前端实现 Agent 负责）

2.1 在 `DeckEditorModal` 中新增「Deck 工作流插件」区：
- 位置：Deck metadata 下方、voice list 上方（或作为独立 tab）
- 展示已选择的 `display_name`、`deck_plugin_version`、发布状态、capability 摘要

2.2 实现版本选择器组件 `DeckPluginVersionSelector`：
- 调用 `GET /api/voice-decks/{deck_id}/plugin-options` 获取过滤后的 release 列表
- 每个版本展示状态标签：`ready` / `materializing` / `configuration_required` / `deprecated` / `disabled` / `revoked` / `incompatible` / `permission_denied` / `upgrade_pending`
- 不可选版本显示 reason code（非敏感）
- 「推荐兼容版本」默认高亮
- 「查看其他版本」展开全部

2.3 实现选择变更 UI：
- 选择后显示生效提示："仅影响下一次运行；历史和当前运行不变"
- 配置/安装问题显示 owner 与恢复入口
- 运行中可预选下一版本；当前 run 继续显示自己的锁定来源

2.4 实现保存与并发处理：
- 保存时携带 `expected_binding_revision`
- 收到 `409 BINDING_REVISION_CONFLICT` 时刷新并提示用户确认
- 禁止最后写入者静默覆盖

### 步骤 3：前端状态管理与数据流

3.1 创建 `useDeckPluginBinding` hook：
- 管理 binding 状态、版本列表、加载状态、错误状态
- 处理 revision 冲突刷新
- 缓存版本列表（合理 TTL）

3.2 集成到 `DeckEditorModal`：
- 打开 modal 时加载当前 binding
- 版本选择变更时本地预览，保存时提交
- 保存成功后更新本地 binding revision

### 步骤 4：测试策略

4.1 前端单元测试：
- `DeckPluginVersionSelector` 渲染各状态版本
- 选择交互与状态变更
- `409 BINDING_REVISION_CONFLICT` 处理
- 生效提示文案

4.2 后端单元测试：
- binding 保存与 revision 递增
- 乐观锁冲突检测
- selection validation 各失败路径

4.3 集成测试：
- 前后端 binding 保存端到端
- 并发编辑冲突场景

---

## 5. 涉及文件路径

### 前端（新增/修改）

```
frontend/src/components/deck/
  DeckPluginSelector.tsx           -- 插件选择主组件（新增）
  DeckPluginVersionList.tsx        -- 版本列表展示（新增）
  DeckPluginVersionCard.tsx        -- 单个版本卡片（新增）
  DeckBindingStatusBar.tsx         -- 绑定状态与生效提示（新增）
  index.ts

frontend/src/hooks/
  useDeckPluginBinding.ts          -- binding 状态管理 hook（新增）
  useDeckPluginOptions.ts          -- 版本列表查询 hook（新增）

frontend/src/api/
  deckPluginApi.ts                 -- Deck Plugin binding API（新增）

frontend/src/components/
  DeckEditorModal.tsx              -- 集成插件选择区（修改）
```

### 后端（由后端 task 文档定义，前端实现引用合同）

```
backend/routers/deck_plugin_binding.py    -- binding API 路由
backend/services/deck_plugin_binding.py   -- binding 服务逻辑
backend/models/deck_plugin_binding.py     -- binding 数据模型
backend/services/selection_validation.py  -- selection validation
```

---

## 6. 输入 / 输出说明

### 输入

| 来源 | 内容 | 格式 |
|---|---|---|
| 后端 API | 当前 binding | `DeckPluginBinding` |
| 后端 API | 可用 release 列表 | `DeckPluginRelease[]` + 不可选原因 |
| 用户交互 | 版本选择 | `deck_plugin_id` + `deck_plugin_version` |
| 用户交互 | 保存请求 | `expected_binding_revision` |

### 输出

| 去向 | 内容 | 格式 |
|---|---|---|
| 后端 API | 保存 binding | `PUT /api/voice-decks/{deck_id}/plugin-binding` |
| UI | 版本列表、状态标签、生效提示 | React 组件渲染 |
| UI | 冲突提示 | 刷新 + 用户确认对话框 |

### 关键 API 合同

**GET /api/voice-decks/{deck_id}/plugin-binding**
```jsonc
{
  "deck_plugin_binding_id": "dpb_...",
  "deck_id": "deck_...",
  "deck_plugin_id": "voice-decks.story-dramatize",
  "deck_plugin_version": "3.1.0",
  "binding_revision": 8,
  "status": "active",
  "applied_to": "next_run",
  "selection_validation_summary": {
    "release_status": "published",
    "installation_status": "ready",
    "compatibility": "passed",
    "runtime_readiness": "materialized"
  }
}
```

**PUT /api/voice-decks/{deck_id}/plugin-binding**
```jsonc
// Request
{
  "deck_plugin_id": "voice-decks.story-dramatize",
  "deck_plugin_version": "3.1.0",
  "expected_binding_revision": 8,
  "apply_to": "next_run"
}

// Response (success)
{
  "deck_plugin_binding_id": "dpb_...",
  "binding_revision": 9,
  "selection_validation_summary": { ... }
}

// Response (conflict)
{
  "error_code": "BINDING_REVISION_CONFLICT",
  "current_revision": 10,
  "message": "Binding was modified concurrently. Please refresh and confirm your selection."
}
```

---

## 7. 依赖项

| 依赖 | 状态 | 说明 |
|---|---|---|
| `DECK-001` | 需稳定 | Manifest 模型 — binding 引用 `deck_plugin_id/version` |
| `DECK-003` | 需稳定 | Installation 生命周期 — 版本列表依赖 installation 状态 |
| `DECK-004` | 需稳定 | 兼容性判定 — selection validation 依赖兼容性服务 |
| `task_202a` / `task_202e` | 已存在 | Deck Editor / Dashboard 基础 UI |
| 后端 binding API | 由后端 task 文档定义 | TaskDesignAgent 引用合同，前端实现消费 |

---

## 8. 测试策略

### 前端测试

1. **组件渲染测试**：
   - `DeckPluginVersionSelector` 正确渲染各状态版本
   - 不可选版本显示正确 reason code
   - `ready` 版本默认可选，`disabled`/`revoked` 不可选

2. **交互测试**：
   - 选择版本后本地状态更新
   - 保存按钮触发 API 调用
   - 生效提示文案正确显示

3. **并发测试**：
   - 模拟 `409 BINDING_REVISION_CONFLICT`
   - 验证刷新提示和用户确认流程

4. **边界测试**：
   - 无可用版本时显示空状态
   - 运行中预选下一版本不影响当前 run 展示

### 后端测试（BackendTaskAgent 负责）

1. **binding 保存测试**：
   - 正确 revision 递增
   - 乐观锁冲突检测
   - 精确版本校验（拒绝 latest/范围）

2. **selection validation 测试**：
   - 各失败路径返回正确 error code
   - 快速校验不替代 preflight

---

## 9. 完成标志

- [ ] 前端 `DeckPluginVersionSelector` 组件实现并渲染版本列表
- [ ] 前端 `useDeckPluginBinding` hook 管理 binding 状态与冲突处理
- [ ] 前端集成到 `DeckEditorModal`，展示插件选择区
- [ ] 后端 binding API 实现（由后端实现 Agent 完成或合同已冻结）
- [ ] `expected_binding_revision` 乐观锁工作正常
- [ ] `409 BINDING_REVISION_CONFLICT` 前端处理完整
- [ ] 生效提示文案："仅影响下一次运行；历史和当前运行不变"
- [ ] 单元测试覆盖版本列表渲染、选择交互、并发冲突
- [ ] 与后端 API 合同对齐，无字段歧义

---

## 10. 风险提示

| 风险 | 等级 | 缓解 |
|---|---|---|
| 后端 binding API 合同未冻结 | 中 | TaskDesignAgent 按设计稿 §14.2 定义合同；后端实现确认或提出差异 |
| `DeckEditorModal` 当前无插件区 | 低 | 增量添加，不推翻既有 voice 编辑区 |
| 版本列表数据量大 | 低 | 分页/折叠 deprecated 版本；默认只展示 ready + 推荐 |
| DECK-016 未决（物理服务边界） | 中 | 按逻辑合同实现；物理拆分后 gateway 层适配 |
| DECK-017 未决（marketplace 签名/digest） | 低 | 本 task 不涉及 manifest 发布；selection validation 只校验已发布 release 的完整性标记 |
| DECK-018 未决（多节点 runtime） | 低 | 本 task 不涉及 runtime 物化；runtime readiness 由后端服务返回，前端只展示脱敏摘要 |
| DECK-019 未决（安全撤销） | 低 | 本 task 不涉及撤销逻辑；revoked release 在版本列表中标记为不可选 |
| DECK-020 未决（Voice chat → run session UX） | 低 | 本 task 不涉及 Voice chat 入口；仅处理 Deck Editor 内的插件选择 |

---

## 11. 允许修改范围与禁止修改范围

### 允许修改
- `frontend/src/components/deck/` 目录（新建）
- `frontend/src/hooks/useDeckPluginBinding.ts`（新建）
- `frontend/src/api/deckPluginApi.ts`（新建）
- `frontend/src/components/DeckEditorModal.tsx`（增量添加插件选择区）

### 禁止修改
- `docs/design/`、`docs/issue/`、`docs/stage/`、`docs/exec/` 目录
- `docs/task/TASK-REQUIREMENT-FORMAT.md`
- 后端 task 文档（后端实现 Agent 负责）
- 任何实现代码（本阶段为 task 规划，非 execute）
- `docs/task/` 下其他已稳定的 task 文档

---

## 12. 设计决策引用

- `DECK-DEC-001`: Deck Plugin 是业务工作流 release
- `DECK-DEC-002`: 发布时冻结 runtime lock
- `DECK-DEC-005`: 选择/升级仅影响下一次运行
- `DECK-DEC-007`: 有效能力取交集
- `DEC-010` (SUO-215): 单次运行锁定版本
- `DEC-013` (SUO-215): 选择即建立可审计 workflow binding

---

## 13. 未决项与默认假设

| 未决项 | 默认假设 | 影响 |
|---|---|---|
| DECK-016 物理服务边界 | 逻辑合同先行，gateway 聚合 | API 路径可能随物理拆分调整 |
| DECK-017 marketplace 签名/digest | 无 digest 不标 production-ready；本 task 只消费已发布 release | selection validation 依赖后端完整性校验 |
| DECK-018 多节点 runtime | 单节点 persistent 默认假设 | runtime readiness 展示按 environment 聚合 |
| DECK-019 安全撤销 | 普通禁用不终止；安全撤销允许强制终止并审计 | revoked release 在版本列表中标记为不可选 |
| DECK-020 Voice chat → run UX | 本 task 不涉及 | 仅 Deck Editor 内插件选择 |
| 版本列表分页策略 | 默认折叠 deprecated，展示前 10 个 | UI 实现时可调 |

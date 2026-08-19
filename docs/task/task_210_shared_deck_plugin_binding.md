# Task: Deck 创建/编辑的插件选择与版本绑定（Shared）

> **Task ID**: `task_210_shared_deck_plugin_binding`
> **源 Issue**: `DECK-005` (from `SUO-223` / `SUO-218`)
> **类型**: `shared`（合同索引；**不可 checkout、不可直接执行**）
> **优先级**: `P0`
> **标签**: `deck-plugin`, `binding`, `selection`, `shared`, `contract`
> **生成日期**: 2026-08-01
> **状态**: `contract-only`（执行入口已拆分至 `task_210a` 与 `task_212`）
> **合同维护责任人**: `TaskDesignAgent`

---

## 1. 任务标题

DECK-005: Deck 创建/编辑的插件选择与版本绑定（Shared 合同索引）

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
4. `task_210a_backend_deck_plugin_binding` 是后端 binding/API 唯一执行单元，由 `BackendTaskAgent` 单独 checkout、实现和验收。
5. `task_212_frontend_deck_editor_plugin_binding` 是前端消费唯一执行单元，由 `FrontendTaskAgent` 单独 checkout、实现和验收。
6. 本文只冻结跨端字段、API、依赖与集成 Gate；不授权任何前端或后端实现代码。

> **命名与 UI 标签隔离**：Deck 业务工作流统一显示为「Deck 工作流插件」，只使用 `deck_plugin_id` / `deck_plugin_version`；ClaudeAgent 会话能力包统一显示为「ClaudeAgent 运行时插件」，只使用 `claude_code_plugin_id` / `resolved_version` / `artifact_digest` 及 `declared`、`materialized`、`loadable` 等运行时标签。禁止只显示笼统的「插件」，禁止用 `claude_code_plugin_id` 或运行时标签替代 Deck binding 的业务标识与发布状态。

### 3.1 UI 状态适用性矩阵

| 状态组 | 适用性 | 本 task 的 UI/合同边界 | 依赖方与原因 |
|---|---|---|---|
| `installation/compatibility` | 适用（只读消费） | 版本列表展示 installation、兼容性与不可选原因；selection validation 只消费脱敏摘要，不实现生命周期或兼容性判定 | `DECK-003` / `DECK-004` 提供权威状态与 reason code；管理恢复动作由 `task_211_frontend_plugin_admin_ui` 承担 |
| `binding/version` | 适用（核心） | 展示精确 release、选择并保存、处理 `binding_revision` 冲突，并明确仅影响下一次运行 | `DECK-005` 的 shared 合同；TaskDesignAgent 负责 task 设计，前端消费、后端 task 提供 binding/API 实现 |
| `preflight/run` | N/A（不在本 task 实现） | 仅展示“当前 run 来源不变/下一次运行生效”的只读语义；不触发或展示 preflight、run 状态、取消与重试 | `DECK-006` / `DECK-007` 提供服务，`task_213_frontend_story_workspace_status` 负责执行态 UI；selection validation 不等于权威 preflight |
| `error/recovery` | 部分适用 | 处理列表加载、selection validation、保存失败与 `BINDING_REVISION_CONFLICT` 刷新确认；只提供配置/安装 owner 跳转 | 安装/物化恢复由 `task_211_frontend_plugin_admin_ui` 承担，preflight/run 恢复由 `task_213_frontend_story_workspace_status` 承担，避免暗示本 task 编排这些恢复流程 |

### 3.2 唯一执行单元映射

| 执行单元 | Domain | 唯一执行责任人 | 来源 | 独立 checkout / 验收 | 本文是否授权实现 |
|---|---|---|---|---|---|
| `task_210a_backend_deck_plugin_binding` | backend | `BackendTaskAgent` | `DECK-005` 后端子边界 | 是 | 否；以 `task_210a_backend_deck_plugin_binding.md` 为唯一授权 |
| `task_212_frontend_deck_editor_plugin_binding` | frontend | `FrontendTaskAgent` | `DECK-011`，消费 `DECK-005` | 是 | 否；以 `task_212_frontend_deck_editor_plugin_binding.md` 为唯一授权 |

- 禁止把本文 checkout 给两个实现 Agent；本文不是 execute task。
- 禁止新增第二份 frontend binding 执行 task；Deck Editor 组件、hook 和 API client 的唯一 ownership 在 `task_212`。
- Stage 中的 `task_210` Shared Binding 执行节点在落地时映射为后端 `task_210a`；前端仍按既有 `task_212` 节点执行。

---

## 4. 合同维护与执行交接步骤

> 本节记录稳定合同和交接顺序，不是实现步骤，也不构成代码写入授权。

### 步骤 1：冻结后端 binding 模型与 API 合同

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

### 步骤 2：交接后端独立执行单元

2.1 仅由 `task_210a_backend_deck_plugin_binding.md` 授权模型、持久化、binding service、selection validation、API 模块和后端测试。

2.2 `BackendTaskAgent` 必须在独立 execute Issue 上 checkout；完成后逐项回填后端验收与测试证据。

### 步骤 3：交接前端独立执行单元

3.1 仅由 `task_212_frontend_deck_editor_plugin_binding.md` 授权 Deck Editor 组件、hook、API client、冲突交互和前端测试。

3.2 `FrontendTaskAgent` 必须在独立 execute Issue 上 checkout；不得复用后端 checkout，也不得把实现归回本文。

### 步骤 4：执行跨端 Gate 验证

4.1 后端单元先证明精确版本、revision 递增、冲突与 selection validation。

4.2 前端单元再基于冻结响应 fixture 验证状态渲染、保存、冲突刷新和重新确认。

4.3 联调只验证同一 `deck_plugin_binding_id`、字段兼容性和“仅影响下一次运行”；不在本文中产生第三份实现 ownership。

---

## 5. 涉及文件路径

本文不授权任何实现路径。执行路径仅在以下唯一执行文档中形成闭集：

| Domain | 唯一执行文档 | 路径 ownership |
|---|---|---|
| backend | `docs/task/task_210a_backend_deck_plugin_binding.md` | binding 模型、持久化、服务、API 模块与后端测试 |
| frontend | `docs/task/task_212_frontend_deck_editor_plugin_binding.md` | Deck Editor 组件、hooks、API client 与前端测试 |

合同维护仅允许由 task 规划 Issue 增量修改本文；未来 execute Issue 不得以本文作为代码写入授权。

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

| Method | Path | 合同边界 |
|---|---|---|
| `GET` | `/api/voice-decks/{deck_id}/plugin-options` | 权限过滤后的精确 release 列表与不可选原因 |
| `GET` | `/api/voice-decks/{deck_id}/plugin-binding` | 当前下一次运行 binding/revision |
| `PUT` | `/api/voice-decks/{deck_id}/plugin-binding` | 保存精确 release；必须传 `expected_binding_revision` |
| `POST` | `/api/voice-decks/{deck_id}/plugin-binding/validate` | selection validation，不创建 Workflow Run |

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
| `task_210a_backend_deck_plugin_binding` | Stage 2 独立执行单元 | 提供 binding/API 与 selection validation |
| `task_212_frontend_deck_editor_plugin_binding` | Stage 3 独立执行单元 | 消费冻结 API 合同；拥有全部 Deck Editor binding UI |

---

## 8. 测试策略

| 验证层 | 唯一 owner | 方式 | 通过标准 |
|---|---|---|---|
| Shared 合同静态检查 | TaskDesignAgent | 检索 Task ID、来源、依赖、字段、API、ownership、闭集与禁止范围 | `task_210` 不含任何实现授权；后端与前端映射唯一 |
| 后端单元/集成测试 | BackendTaskAgent | 按 `task_210a` §8 执行 | 精确版本、revision、冲突、validation 和持久化逐项通过 |
| 前端单元/E2E | FrontendTaskAgent | 按 `task_212` §8 执行 | 状态渲染、选择、保存、冲突重新确认和生效提示逐项通过 |
| 跨端合同验证 | 两个执行单元各自回填证据 | 后端响应 fixture + 最小联调 | 字段、错误码与 `next_run` 语义一致，无第二份 binding 存储 |

---

## 9. 完成标志

- [ ] 后端唯一执行文档 `task_210a_backend_deck_plugin_binding.md` 存在且只授权 BackendTaskAgent
- [ ] 前端唯一执行文档 `task_212_frontend_deck_editor_plugin_binding.md` 存在且只授权 FrontendTaskAgent
- [ ] 本文不再授权前端组件、hook、API client 或后端实现路径
- [ ] 两个执行单元均明确 Task ID、来源、依赖、输入/输出、闭集、禁止范围、验收、测试和回滚
- [ ] `DeckPluginBinding` 字段、四个 API、`BINDING_REVISION_CONFLICT` 与 `next_run` 语义在三个文档中一致
- [ ] Stage 的 Shared 节点可映射为后端 `task_210a` 独立 checkout，前端继续映射 `task_212`

---

## 10. 风险提示

| 风险 | 等级 | 缓解 |
|---|---|---|
| 后端实现偏离已冻结 binding API 合同 | 中 | 后端以 `task_210a` 闭集实现；前端只消费本节四个 API 与冻结 fixture |
| `DeckEditorModal` 当前无插件区 | 低 | 增量添加，不推翻既有 voice 编辑区 |
| 版本列表数据量大 | 低 | 分页/折叠 deprecated 版本；默认只展示 ready + 推荐 |
| DECK-016 未决（物理服务边界） | 中 | 按逻辑合同实现；物理拆分后 gateway 层适配 |
| DECK-017 未决（marketplace 签名/digest） | 低 | 本 task 不涉及 manifest 发布；selection validation 只校验已发布 release 的完整性标记 |
| DECK-018 未决（多节点 runtime） | 低 | 本 task 不涉及 runtime 物化；runtime readiness 由后端服务返回，前端只展示脱敏摘要 |
| DECK-019 未决（安全撤销） | 低 | 本 task 不涉及撤销逻辑；revoked release 在版本列表中标记为不可选 |
| DECK-020 未决（Voice chat → run session UX） | 低 | 本 task 不涉及 Voice chat 入口；仅处理 Deck Editor 内的插件选择 |

---

## 11. 规划边界与未来 execute 授权

### 11.1 本次 task 规划修订

仅允许增量修改 `docs/task/task_210_shared_deck_plugin_binding.md`、`docs/task/task_212_frontend_deck_editor_plugin_binding.md`，并新增 `docs/task/task_210a_backend_deck_plugin_binding.md`。本次不得执行或修改任何实现代码。

### 11.2 本文的未来 execute 规则

- 本文允许实现路径闭集为：`N/A`。
- 本文不可用于 checkout，不可指派 FrontendTaskAgent、BackendTaskAgent 或 ExecTaskAgent 执行代码。
- 后端未来 execute 仅以 `task_210a_backend_deck_plugin_binding.md` §5/§11 为授权。
- 前端未来 execute 仅以 `task_212_frontend_deck_editor_plugin_binding.md` §5/§11 为授权。
- 未出现在对应执行单元允许闭集中的路径默认禁止。

### 11.3 禁止范围

- `docs/design/`、`docs/issue/`、`docs/stage/`、`docs/exec/` 与 `docs/task/TASK-REQUIREMENT-FORMAT.md`
- 任何实现代码、依赖锁、部署配置与生成物
- `docs/task/` 下除本次三个授权文档外的稳定 task 文档

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

---

## 14. 回滚边界与交付顺序

- 合同修订回滚：只回退本文关于 execute mapping、ownership 和授权边界的增量，不改写 §6 已冻结字段/API。
- 后端执行回滚：只按 `task_210a` 的闭集回滚 binding/API 变更，不触碰前端。
- 前端执行回滚：只按 `task_212` 的闭集撤销 Deck Editor binding UI，不删除或降级后端 binding 数据。
- 交付顺序：`task_210a` 后端合同测试通过并冻结 fixture → `task_212` 前端消费与测试 → 最小跨端验证。

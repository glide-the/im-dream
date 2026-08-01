# Task: Deck Editor 插件选择与版本绑定 UI

> **Task ID**: `task_212_frontend_deck_editor_plugin_binding`
> **源 Issue**: `DECK-011` (from `SUO-223` / `SUO-218`)
> **Readiness 修订 Issue**: `SUO-279`
> **Execute 合同修订 Issue**: [SUO-324](/SUO/issues/SUO-324)
> **类型 / Domain**: `frontend`（domain 仅用于分类，不代表执行 Agent 身份）
> **优先级**: `P1`
> **标签**: `frontend`, `deck-editor`, `deck-plugin`, `binding`
> **生成日期**: 2026-08-01
> **状态**: `pending_stage_recheck`
> **唯一执行责任人**: `ExecTaskAgent`
> **Stage 映射**: Stage 3 / Wave 1（独立 execute Issue、独立 checkout、独立验收）

---

## 1. 任务标题

DECK-011: Deck Editor 插件选择与版本绑定 UI

---

## 2. 关联 Issue

| 关联 | ID | 说明 |
|---|---|---|
| 源 Issue | `DECK-011` | Deck Editor 插件选择与版本绑定 UI |
| Readiness Issue | `SUO-279` | 消除与 shared task 的重复 frontend ownership |
| Execute 合同修订 | `SUO-324` | 统一执行责任人、正式报告例外与冻结决策状态 |
| 父 Issue | `SUO-217` | 组织 Deck 插件业务设计与 ClaudeAgent 交互方案分派 |
| Design Issue | `SUO-218` | Voice Decks × Ink Dream Deck Plugin 与 ClaudeAgent 集成设计 |
| Issue 清单 | `SUO-223` | Deck Plugin 前端/后端 Issue 拆解 |
| 上游 design | `docs/design/deck-plugin-voice-ink-dream-integration.md` §9.1, §9.2 | Deck 创建/编辑与选择交互 |
| Shared 合同索引 | `task_210_shared_deck_plugin_binding` | 只读跨端合同；不可作为 execute 授权 |
| 后端执行单元 | `task_210a_backend_deck_plugin_binding` | DECK-005 binding/API 唯一实现与前置交接 |

---

## 3. 任务目标

实现 Deck Editor 中的插件选择区和版本绑定 UI，让创作者在编辑 Deck 时：

1. 查看当前已绑定的 Deck Plugin release 信息。
2. 浏览所有可用版本，了解每个版本的状态和不可选原因。
3. 选择新版本并保存，产生新的 `binding_revision`。
4. 明确获知「选择仅影响下一次运行」的语义。
5. 处理并发冲突（`409 BINDING_REVISION_CONFLICT`）。

本 task 是 Deck Editor binding UI、hooks 与 API client 的**唯一前端执行单元**。`task_210_shared_deck_plugin_binding` 只保留共享合同索引，不再授权相同组件；后端实现唯一归属 `task_210a_backend_deck_plugin_binding`。

- 未来 execute 必须由 `ExecTaskAgent` 在独立 Issue 上 checkout；不得与后端或其他 task 共用 checkout。
- 本 task 可以消费后端 fixture/接口，但禁止实现或改写 binding 模型、持久化、selection validation、权限与兼容性判定。

> **命名隔离原则**：本 task 涉及的插件标识必须使用 `deck_plugin_id` + `deck_plugin_version` 前缀，禁止与 `claude_code_plugin_id` 或 Paperclip `pluginKey` 混用。UI 文案必须区分"Deck 工作流插件"和"ClaudeAgent 运行时插件"。

### 3.1 UI 状态适用性矩阵

| 状态组 | 适用性 | 本 task 的 UI 边界 | 依赖方与原因 |
|---|---|---|---|
| `installation/compatibility` | 适用（只读选择门禁） | 版本卡片展示 installation、兼容性、runtime readiness 与不可选原因；只提供配置/安装 owner 入口 | `DECK-003` / `DECK-004` 提供权威判定，`task_211_frontend_plugin_admin_ui` 负责安装与管理恢复；本 task 不执行安装、启停或兼容性计算 |
| `binding/version` | 适用（核心） | 展示当前精确 release、选择版本、保存 binding、处理 `expected_binding_revision` 冲突并提示下一次运行生效 | `task_210_shared_deck_plugin_binding` / `DECK-005` 提供 shared 合同与后端 API；本 task 只负责 Deck Editor UI 消费 |
| `preflight/run` | N/A（不在本 task 实现） | 当前 run 引用和“下一次运行使用”仅为只读提示；不触发 preflight，不展示运行进度，不提供取消或重试 | `DECK-006` / `DECK-007` 提供服务，`task_213_frontend_story_workspace_status` 负责执行态 UI |
| `error/recovery` | 部分适用 | 处理列表加载、版本不可选、保存失败和 `BINDING_REVISION_CONFLICT`；可跳转配置/安装 owner | 安装/物化恢复由 `task_211_frontend_plugin_admin_ui` 承担，preflight/run 错误恢复由 `task_213_frontend_story_workspace_status` 承担 |

---

## 4. 实现步骤

### 步骤 1：Deck Editor 插件区布局设计

1.1 在 `DeckEditorModal` 中新增「Deck 工作流插件」区域：

```
┌─────────────────────────────────────────────────────────────┐
│  Deck Editor                                                │
├─────────────────────────────────────────────────────────────┤
│  [Deck Name / Description]  [Deck Prompt]                   │
├─────────────────────────────────────────────────────────────┤
│  🧩 Deck 工作流插件                                          │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  当前选择: 悬疑短剧工作流 v3.1.0 (published)            │  │
│  │  能力: story.context.read, story.result.produce        │  │
│  │  状态: ✅ Ready                                        │  │
│  │  [更换版本 ▼]                                          │  │
│  └───────────────────────────────────────────────────────┘  │
│  ⚠️ 选择变更仅影响下一次运行；历史和当前运行不变              │
├─────────────────────────────────────────────────────────────┤
│  [Agents List]  [Selected Voice Editor]                     │
└─────────────────────────────────────────────────────────────┘
```

1.2 区域位置：
- 位于 Deck metadata（name/description/prompt）下方
- 位于 Agents/Voice 编辑区上方
- 使用与 Deck metadata 相同的卡片式容器风格

### 步骤 2：当前绑定展示组件

2.1 实现 `DeckPluginBindingCard`：
- 展示已选择的：
  - `display_name`（插件显示名）
  - `deck_plugin_version`（精确版本）
  - 发布状态标签（`published` / `deprecated` / `revoked`）
  - capability 摘要（前 3 个 + 更多计数）
  - installation 状态（`ready` / `materializing` / `error`）
  - runtime readiness（`materialized` / `loadable`）
- 操作：「更换版本」按钮

2.2 空状态：
- 未选择插件时显示：「未选择工作流插件。选择插件以启用剧本创作工作流。」
- 提供「浏览可用插件」入口

### 步骤 3：版本选择弹窗/抽屉

3.1 实现 `DeckPluginVersionPicker`：
- 触发：点击「更换版本」或「浏览可用插件」
- 展示形式：Modal 或右侧抽屉

3.2 版本列表展示：
- 默认展示「推荐兼容版本」（按 installation `ready` + 兼容性通过排序）
- 「查看其他版本」展开全部
- 每个版本卡片展示：
  - `deck_plugin_version`
  - 发布状态标签
  - installation 状态
  - runtime readiness 指示
  - capability 数量
  - Deck runtime contract 兼容性
  - 不可选时展示 reason code（非敏感）

3.3 版本状态映射（设计稿 §9.1）：

| 展示状态 | 可选 | 视觉处理 |
|---|---|---|
| `ready` | ✅ 是 | 正常样式，默认推荐 |
| `materializing` | ⏳ 暂否 | 禁用，显示进度 |
| `configuration_required` | ❌ 暂否 | 禁用，显示配置入口 |
| `deprecated` | 策略决定 | 折叠，显示替代版本提示 |
| `disabled` / `revoked` | ❌ 否 | 禁用，保留名称用于解释 |
| `incompatible` | ❌ 否 | 禁用，显示非敏感 reason |
| `permission_denied` | ❌ 否 | 禁用，不泄露敏感细节 |
| `upgrade_pending` | ❌ 否 | 禁用，显示审批入口 |

3.4 选择交互：
- 点击版本卡片选中（radio 样式）
- 选中后展示版本差异摘要（与当前绑定对比）
- 「确认选择」按钮保存

### 步骤 4：保存与并发处理

4.1 保存流程：
- 用户确认选择后，调用 `PUT /api/voice-decks/{deck_id}/plugin-binding`
- 携带 `expected_binding_revision`（当前已知 revision）
- 请求体：
```jsonc
{
  "deck_plugin_id": "voice-decks.story-dramatize",
  "deck_plugin_version": "3.1.0",
  "expected_binding_revision": 8,
  "apply_to": "next_run"
}
```

4.2 并发冲突处理：
- 收到 `409 BINDING_REVISION_CONFLICT` 时：
  1. 停止保存
  2. 弹窗提示："该 Deck 的插件选择已被其他会话修改。请刷新查看最新状态后重新确认。"
  3. 自动刷新版本列表和当前绑定
  4. 保留用户选择（若版本仍可用），提示重新确认

4.3 保存成功：
- 关闭选择弹窗
- 更新 `DeckPluginBindingCard` 展示
- 显示成功提示："插件版本已更新，将在下一次运行时生效"

### 步骤 5：生效提示与运行中状态

5.1 始终展示的提示文案：
- 位置：绑定卡片下方
- 文案："⚠️ 选择变更仅影响下一次运行；历史和当前运行不变"；这是 binding 生效语义，不替代 §15 已批准的 Voice → run 发布文案
- 样式：弱提示色，不干扰主操作

5.2 运行中状态：
- 若当前 Deck 有运行中的 Workflow Run：
  - 绑定卡片旁显示："当前运行使用中：{workflow_run_id}"
  - 允许预选下一版本，但明确标注"下一次运行使用"

---

## 5. 涉及文件路径

| 路径 | 动作 | 最小变更 |
|---|---|---|
| `frontend/src/components/deck/DeckPluginBindingCard.tsx` | 新建 | 当前 binding、空状态、版本与 capability 摘要 |
| `frontend/src/components/deck/DeckPluginVersionPicker.tsx` | 新建 | options 列表、版本差异、选择与确认 |
| `frontend/src/components/deck/DeckPluginVersionCard.tsx` | 新建 | 单版本状态、可选性与安全 reason 展示 |
| `frontend/src/components/deck/DeckPluginBindingStatus.tsx` | 新建 | `next_run` 提示、加载/保存/冲突状态 |
| `frontend/src/hooks/useDeckPluginBinding.ts` | 新建 | 当前 binding、保存、revision 冲突刷新与重新确认状态 |
| `frontend/src/hooks/useDeckPluginOptions.ts` | 新建 | options 查询、缓存与刷新 |
| `frontend/src/api/deckPluginApi.ts` | 新建 | 只封装 task_210a 冻结的四个 API 合同 |
| `frontend/src/components/DeckEditorModal.tsx` | 修改 | 只增量集成 Deck 工作流插件区域 |
| `frontend/src/components/deck/DeckPluginBindingCard.test.tsx` | 条件新建 | 已有兼容 runner 时覆盖当前/空/运行中只读状态 |
| `frontend/src/components/deck/DeckPluginVersionPicker.test.tsx` | 条件新建 | 已有兼容 runner 时覆盖 options、选择和不可选原因 |
| `frontend/src/hooks/useDeckPluginBinding.test.ts` | 条件新建 | 已有兼容 runner 时覆盖保存、409 刷新与重新确认 |

以上十一个路径是未来 execute 的完整闭集；未列出的路径默认禁止。三个测试路径仅在 §8 runner 发现命令返回非空且现有依赖可直接运行时创建；若仍无 runner，不得生成不可执行测试文件，改以浏览器 E2E/人工证据验收。这不授权修改 `package.json`、依赖锁或测试配置。所有路径 ownership 仅属于本 task，不与 `task_210` 共享。

---

## 6. 输入 / 输出说明

### 输入

| 来源 | 内容 | 格式 |
|---|---|---|
| 后端 API | 当前 binding | `DeckPluginBinding` |
| 后端 API | 可用版本列表 | `DeckPluginRelease[]` + 不可选原因 |
| 用户交互 | 版本选择 | `deck_plugin_id` + `deck_plugin_version` |
| 用户交互 | 保存确认 | 点击「确认选择」 |

### 输出

| 去向 | 内容 | 格式 |
|---|---|---|
| 后端 API | 保存 binding | `PUT /api/voice-decks/{deck_id}/plugin-binding` |
| UI | 绑定卡片、版本列表、状态标签 | React 组件 |
| UI | 冲突提示弹窗 | 对话框 |

### API client 映射

| Method | Path | 本 task 的消费方式 |
|---|---|---|
| `GET` | `/api/voice-decks/{deck_id}/plugin-options` | `useDeckPluginOptions` 加载权限过滤后的精确 release 与不可选原因 |
| `GET` | `/api/voice-decks/{deck_id}/plugin-binding` | `useDeckPluginBinding` 加载当前下一次运行 binding/revision |
| `PUT` | `/api/voice-decks/{deck_id}/plugin-binding` | 携带精确版本、`expected_binding_revision`、`apply_to=next_run` 保存 |
| `POST` | `/api/voice-decks/{deck_id}/plugin-binding/validate` | 展示 selection validation 摘要；不得当作 execution preflight |

---

## 7. 依赖项

| 依赖 | 状态 | 说明 |
|---|---|---|
| `task_210_shared_deck_plugin_binding` | 合同输入 | 只读字段、API、状态与 `next_run` 语义；不承载实现 |
| `task_210a_backend_deck_plugin_binding` | 前置交接 | 后端 binding/API 与成功、不可选、冲突响应 fixture 冻结 |
| `DECK-005` | 由 task_210a 提供 | 后端 binding 服务 |
| `DECK-003` | 需稳定 | Installation 状态 |
| `DECK-004` | 需稳定 | 兼容性判定 |
| `DeckEditorModal` | 已存在 | 现有 Deck 编辑器 |

---

## 8. 测试策略

1. **静态与闭集检查**：
   - 使用仓库既有 frontend lint/typecheck 对 §5 组件、hook、API client 做最小相关检查
   - `git diff --check` 通过，实际实现/测试变更仅位于 §5 十一个路径，另只写本 task 的唯一正式报告路径

2. **绑定卡片渲染测试**：
   - 已选择状态：展示名称、版本、状态、能力
   - 空状态：展示引导文案
   - 运行中状态：展示当前 run 引用

3. **版本选择器测试**：
   - 版本列表正确渲染各状态
   - 不可选版本禁用并显示 reason
   - 推荐版本默认高亮

4. **保存流程测试**：
   - 正常保存：revision 更新、UI 刷新
   - 冲突处理：409 后停止保存、刷新当前 binding/options、仍可用时保留选择并要求重新确认
   - 禁止在客户端用最后写入者覆盖冲突

5. **文案与安全测试**：
   - 生效提示始终可见
   - 错误文案安全（无敏感信息）
   - UI 只展示服务端 `reason_code` 映射，不执行版本/权限/兼容性裁决

6. **E2E / 人工验证**：
   - 打开 Deck Editor → 加载当前 binding/options → 选择精确版本 → 保存 → 显示新 revision 与下一次运行提示
   - 两个编辑会话并发保存 → 后提交者收到冲突 → 刷新并重新确认
   - 当前运行来源保持不变；不得通过前端测试伪造或改写历史 run

execute Issue 必须先读取 `frontend/package.json` 的 `scripts` 与现有测试文件命名，逐字回填实际 runner、版本和命令，不得凭空假设 Vitest/Jest。当前仓库已发现 `build`、`lint`，未发现 `test` script；从仓库根执行的最低静态验证为 `npm --prefix frontend run build`、`npm --prefix frontend run lint` 与 `git diff --check`，runner 发现命令固定为 `node -p "require('./frontend/package.json').scripts?.test ?? ''"`。若 execute 时仍无 test runner，必须在 execute Issue/正式报告记录发现输出，并以本节 E2E/人工场景补证；不得为了本 task 新增/更换测试框架、依赖锁或全局配置，也不得伪报单元测试已执行。

---

## 9. 完成标志

- [ ] `DeckPluginBindingCard` 组件实现，展示当前绑定信息
- [ ] `DeckPluginVersionPicker` 组件实现，展示版本列表与选择
- [ ] 版本状态标签正确映射（ready/materializing/deprecated 等）
- [ ] 「推荐兼容版本」与「查看其他版本」功能
- [ ] 选择变更生效提示："仅影响下一次运行；历史和当前运行不变"；该 binding 文案不得冒充或覆盖 §15 已批准的 Voice → run 发布文案
- [ ] 配置/安装问题的 owner 与恢复入口
- [ ] `expected_binding_revision` 并发冲突处理完整
- [ ] 已有 runner 时自动化测试覆盖版本列表/选择/冲突；无 runner 时浏览器 E2E/人工证据覆盖同等场景并记录发现结果
- [ ] 集成到 `DeckEditorModal`，不推翻既有 voice 编辑区
- [ ] 成功、不可选与 409 响应只消费 `task_210a` 冻结合同，无客户端裁决副本
- [ ] 实际改动严格位于 §5 十一个实现/测试路径与本 task 唯一正式报告路径内
- [ ] execute Issue 评论逐项回填验收、验证命令、结果、diff 与回滚说明

---

## 10. 风险提示

| 风险 | 等级 | 缓解 |
|---|---|---|
| `DeckEditorModal` 当前结构紧凑 | 低 | 插件区放在 metadata 下方，不挤占 voice 区 |
| 版本列表数据量大 | 低 | 默认折叠 deprecated，分页或虚拟滚动 |
| DECK-016 已冻结（物理服务边界） | 低 | 只消费逻辑 API；无状态 gateway 只聚合/路由，不在前端假设新业务服务或双写 owner |
| DECK-017 条件冻结（marketplace 签名/digest） | 低 | 本 task 只消费服务端 release 状态；未验证制品不得在 UI 中显示为 production-ready |
| DECK-018 已冻结但 rollout 限域 | 低 | runtime readiness 由后端返回；当前仅单节点 persistent 通过，多节点/临时 runtime 继续 fail closed |
| DECK-019 已冻结（安全撤销） | 低 | revoked release 不可选；不把设计冻结误写成 Stage 4 production Gate 已通过 |
| DECK-020 已冻结（Voice chat → run UX） | 低 | 本 task 不实现 Voice chat 卡片；binding 文案与批准的独立 run/session、原 chat 留卡语义保持一致 |

---

## 11. 允许修改范围与禁止修改范围

### 11.1 未来 execute 允许闭集

- `frontend/src/components/deck/DeckPluginBindingCard.tsx`
- `frontend/src/components/deck/DeckPluginVersionPicker.tsx`
- `frontend/src/components/deck/DeckPluginVersionCard.tsx`
- `frontend/src/components/deck/DeckPluginBindingStatus.tsx`
- `frontend/src/hooks/useDeckPluginBinding.ts`
- `frontend/src/hooks/useDeckPluginOptions.ts`
- `frontend/src/api/deckPluginApi.ts`
- `frontend/src/components/DeckEditorModal.tsx`（仅增量添加插件区）
- `frontend/src/components/deck/DeckPluginBindingCard.test.tsx`
- `frontend/src/components/deck/DeckPluginVersionPicker.test.tsx`
- `frontend/src/hooks/useDeckPluginBinding.test.ts`
- `docs/exec/exec_task_212_frontend_deck_editor_plugin_binding.md`（仅允许 `ExecTaskAgent` 写入本 task 的唯一正式执行报告）

### 11.2 未来 execute 禁止范围

- `backend/` 全部路径；后端唯一 ownership 属于 `task_210a`
- `docs/exec/` 下除 `docs/exec/exec_task_212_frontend_deck_editor_plugin_binding.md` 之外的全部路径
- `docs/design/`、`docs/issue/`、`docs/task/`、`docs/stage/`
- 依赖锁、测试框架/构建配置、生成物与 §11.1 未列出的任何实现或测试文件
- `DeckEditorModal` 中既有 metadata、Agents/Voice 编辑、保存和关闭语义
- Plugin Admin 安装/启停/升级/恢复实现，以及 Preflight/Run 状态、取消、重试与 ClaudeAgent session 实现
- 在客户端复制 release、installation、权限、兼容性、digest 或 runtime readiness 的权威裁决
- 借机重构、全文件格式化、清理无关代码，或覆盖工作树既有改动

### 11.3 当前规划阶段约束

本次 [SUO-324](/SUO/issues/SUO-324) 仅增量修订 task 文档，不授权执行 §11.1 实现。未来必须由 `ExecTaskAgent` 在独立 execute Issue checkout 后才可按闭集实施；完成后由 StagePlanner 独立重跑 readiness，不得由本 task 自行宣布进入 execute 或通过 Stage 3 Gate。

---

## 12. 设计决策引用

- `DECK-DEC-005`: 选择仅影响下一次运行
- `DECK-DEC-007`: 有效能力取交集
- `DEC-010` (SUO-215): 单次运行锁定版本
- `DEC-013` (SUO-215): 选择即建立可审计 binding

---

## 13. 三文档唯一映射与联调边界

| 内容 | task_210 Shared 合同索引 | task_210a Backend | task_212 Frontend（本 task） |
|---|---|---|---|
| execute checkout | 禁止 | `ExecTaskAgent` 按 task_210a 独立 Issue checkout | `ExecTaskAgent` 按本 task 独立 Issue checkout；不得与 task_210a 共用 |
| binding 模型/持久化 | 只冻结字段 | 唯一 ownership | 禁止 |
| binding/options/validate API | 只冻结合同 | 唯一提供者 | 唯一消费者 |
| `useDeckPluginBinding` / `useDeckPluginOptions` | 不拥有 | 禁止 | 唯一 ownership |
| `deckPluginApi.ts` | 不拥有 | 禁止 | 唯一 ownership |
| Deck Editor 组件与交互 | 不拥有 | 禁止 | 唯一 ownership |
| revision 冲突 | 冻结 `409` 语义 | 原子拒绝并返回当前 revision | 刷新并要求用户重新确认 |
| 跨端验收 | 定义 Gate | 回填后端证据 | 回填前端与最小联调证据 |

---

## 14. 回滚边界

- 只移除 §11.1 中本 task 新增的 Deck Editor binding 区、hooks、client 与测试，或回退 `DeckEditorModal` 的最小集成区段。
- 不回滚、不删除后端 binding 数据、API、revision 或历史来源。
- 前端回滚不得影响既有 metadata、Agents/Voice 编辑和其他 Deck Editor 保存语义。
- 若后端合同回滚或不兼容，前端回到未启用 binding 区的安全状态并保留既有 Deck 编辑功能；不得伪造成功或本地保存 binding。
- 回滚前后执行 §8 的静态验证与关键人工场景，并在 `docs/exec/exec_task_212_frontend_deck_editor_plugin_binding.md` 记录触发条件、变更路径、验证结果与剩余影响；正式报告本身不得在代码回滚中删除。

---

## 15. DECK-020 Voice chat → run UX 已冻结合同

> **状态**：`frozen`；依据 [SUO-254](/SUO/issues/SUO-254) 的 CEO `approve`，Stage 3 UI/文案设计 Gate 已通过。该设计冻结不代替 execute、E2E 或发布验收。

| 项 | 已批准合同 / 本 task 边界 |
|---|---|
| 启动方式 | 仅用户点击「创建工作流运行」时启动；普通聊天消息不得静默触发 |
| 原 chat | 保持原位置并插入/更新 `WorkflowRunLinkCard`，不得自动跳转 |
| run/session | 创建独立 `workflow_run_id` 与 run-scoped `agent_session_id`，不得复用 Voice `thread_id`；重试创建新 run/session |
| 双向来源 | chat 卡片以「查看运行」打开正确 run；运行详情在有权限时提供「返回来源对话」 |
| 权限降级 | 无来源权限时只显示「来源：Voice 对话（无权查看）」，隐藏名称、时间、正文和返回链接 |
| 批准文案 | 入口「创建工作流运行」；卡片标题「已创建独立工作流运行」；说明「本次运行使用锁定的 Deck 工作流与 ClaudeAgent 运行时；当前 Voice 对话仅作为来源。」；主操作「查看运行」 |
| 本 task 影响 | 本 task 只实现 Deck Editor binding；“仅影响下一次运行；历史和当前运行不变”是 binding 生效语义，不替代上述 Voice 发布文案，也不授权实现 chat 卡片 |
| 验收边界 | 与 task_213 联调时验证当前/历史 run 来源不变；Voice 卡片、权限降级和双向来源证据由拥有对应路径的 execute task 提供 |

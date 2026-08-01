# Task: Deck Editor 插件选择与版本绑定 UI

> **Task ID**: `task_212_frontend_deck_editor_plugin_binding`
> **源 Issue**: `DECK-011` (from `SUO-223` / `SUO-218`)
> **类型**: `frontend`（**TaskDesignAgent 负责 task 设计**，前端实现 Agent 负责代码实现）
> **优先级**: `P1`
> **生成日期**: 2026-08-01
> **状态**: `draft`

---

## 1. 任务标题

DECK-011: Deck Editor 插件选择与版本绑定 UI

---

## 2. 关联 Issue

| 关联 | ID | 说明 |
|---|---|---|
| 源 Issue | `DECK-011` | Deck Editor 插件选择与版本绑定 UI |
| 父 Issue | `SUO-217` | 组织 Deck 插件业务设计与 ClaudeAgent 交互方案分派 |
| Design Issue | `SUO-218` | Voice Decks × Ink Dream Deck Plugin 与 ClaudeAgent 集成设计 |
| Issue 清单 | `SUO-223` | Deck Plugin 前端/后端 Issue 拆解 |
| 上游 design | `docs/design/deck-plugin-voice-ink-dream-integration.md` §9.1, §9.2 | Deck 创建/编辑与选择交互 |
| Shared Task | `task_210_shared_deck_plugin_binding` | DECK-005 前后端共享合同 |

---

## 3. 任务目标

实现 Deck Editor 中的插件选择区和版本绑定 UI，让创作者在编辑 Deck 时：

1. 查看当前已绑定的 Deck Plugin release 信息。
2. 浏览所有可用版本，了解每个版本的状态和不可选原因。
3. 选择新版本并保存，产生新的 `binding_revision`。
4. 明确获知「选择仅影响下一次运行」的语义。
5. 处理并发冲突（`409 BINDING_REVISION_CONFLICT`）。

本 task 是 `task_210_shared_deck_plugin_binding` 的前端 UI 子集，专注于 Deck Editor 内的交互体验。

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
- 文案："⚠️ 选择变更仅影响下一次运行；历史和当前运行不变" `[文案未冻结 — 待 DECK-020 决策]`
- 样式：弱提示色，不干扰主操作

5.2 运行中状态：
- 若当前 Deck 有运行中的 Workflow Run：
  - 绑定卡片旁显示："当前运行使用中：{workflow_run_id}"
  - 允许预选下一版本，但明确标注"下一次运行使用"

---

## 5. 涉及文件路径

### 前端（新增/修改）

```
frontend/src/components/deck/
  DeckPluginBindingCard.tsx        -- 当前绑定展示卡片（新增）
  DeckPluginVersionPicker.tsx      -- 版本选择弹窗/抽屉（新增）
  DeckPluginVersionCard.tsx        -- 单个版本卡片（新增）
  DeckPluginBindingStatus.tsx      -- 绑定状态与生效提示（新增）

frontend/src/hooks/
  useDeckPluginBinding.ts          -- 与 task_210 共享（binding 状态管理）
  useDeckPluginOptions.ts          -- 与 task_210 共享（版本列表查询）

frontend/src/api/
  deckPluginApi.ts                 -- 与 task_210 共享（binding API）

frontend/src/components/
  DeckEditorModal.tsx              -- 集成插件选择区（修改）
```

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

---

## 7. 依赖项

| 依赖 | 状态 | 说明 |
|---|---|---|
| `task_210_shared_deck_plugin_binding` | 同批次 | TaskDesignAgent 设计的共享 binding API 合同 |
| `DECK-005` | 需完成 | 后端 binding 服务 |
| `DECK-003` | 需稳定 | Installation 状态 |
| `DECK-004` | 需稳定 | 兼容性判定 |
| `DeckEditorModal` | 已存在 | 现有 Deck 编辑器 |

---

## 8. 测试策略

1. **绑定卡片渲染测试**：
   - 已选择状态：展示名称、版本、状态、能力
   - 空状态：展示引导文案
   - 运行中状态：展示当前 run 引用

2. **版本选择器测试**：
   - 版本列表正确渲染各状态
   - 不可选版本禁用并显示 reason
   - 推荐版本默认高亮

3. **保存流程测试**：
   - 正常保存：revision 更新、UI 刷新
   - 冲突处理：409 响应、刷新提示、重新确认

4. **文案测试**：
   - 生效提示始终可见
   - 错误文案安全（无敏感信息）

5. **E2E 测试**：
   - 打开 Deck Editor → 选择插件 → 保存 → 验证下一次运行生效

---

## 9. 完成标志

- [ ] `DeckPluginBindingCard` 组件实现，展示当前绑定信息
- [ ] `DeckPluginVersionPicker` 组件实现，展示版本列表与选择
- [ ] 版本状态标签正确映射（ready/materializing/deprecated 等）
- [ ] 「推荐兼容版本」与「查看其他版本」功能
- [ ] 选择变更生效提示："仅影响下一次运行；历史和当前运行不变" `[文案未冻结 — 待 DECK-020 决策]`
- [ ] 配置/安装问题的 owner 与恢复入口
- [ ] `expected_binding_revision` 并发冲突处理完整
- [ ] 单元测试/E2E 测试覆盖版本列表、选择交互、并发冲突
- [ ] 集成到 `DeckEditorModal`，不推翻既有 voice 编辑区

---

## 10. 风险提示

| 风险 | 等级 | 缓解 |
|---|---|---|
| `DeckEditorModal` 当前结构紧凑 | 低 | 插件区放在 metadata 下方，不挤占 voice 区 |
| 版本列表数据量大 | 低 | 默认折叠 deprecated，分页或虚拟滚动 |
| DECK-016 未决（物理服务边界） | 中 | 按逻辑合同消费 API；物理拆分后 gateway 层适配 |
| DECK-017 未决（marketplace 签名/digest） | 低 | 本 task 只消费已发布 release；digest 完整性由后端校验 |
| DECK-018 未决（多节点 runtime） | 低 | runtime readiness 由后端返回，前端只展示脱敏摘要 |
| DECK-019 未决（安全撤销） | 低 | revoked release 在版本列表中标记为不可选 |
| DECK-020 未决（Voice chat → run UX） | 中 | **生效提示文案保持未冻结**；当前使用默认假设文案，冻结 gate：产品 owner 确认 fork/跳转/历史展示文案（见下方 §14） |

---

## 11. 允许修改范围与禁止修改范围

### 允许修改
- `frontend/src/components/deck/` 目录（增量添加）
- `frontend/src/components/DeckEditorModal.tsx`（添加插件区）
- 共享 hook/api 文件（与 task_210 协作）

### 禁止修改
- `docs/design/`、`docs/issue/`、`docs/stage/`、`docs/exec/`
- `docs/task/TASK-REQUIREMENT-FORMAT.md`
- 后端 task 文档（后端实现 Agent 负责）
- 任何实现代码（本阶段为 task 规划）
- `DeckEditorModal` 中既有 voice 编辑功能

---

## 12. 设计决策引用

- `DECK-DEC-005`: 选择仅影响下一次运行
- `DECK-DEC-007`: 有效能力取交集
- `DEC-010` (SUO-215): 单次运行锁定版本
- `DEC-013` (SUO-215): 选择即建立可审计 binding

---

## 13. 与 task_210 的协作边界

| 内容 | task_210 (Shared — TaskDesignAgent 设计) | task_212 (本 task) |
|---|---|---|
| binding API 合同 | TaskDesignAgent 定义并协商 | 前端实现消费 |
| `useDeckPluginBinding` hook | TaskDesignAgent 定义 | 前端实现复用 |
| `deckPluginApi.ts` | TaskDesignAgent 定义 | 前端实现复用 |
| Deck Editor 内 UI | 不涉及 | 前端实现主责 |
| 版本选择交互 | 不涉及 | 前端实现主责 |
| 并发冲突处理 | TaskDesignAgent 定义后端行为 | 前端实现前端交互 |

---

## 14. DECK-020 Voice chat → run UX 文案冻结 gate

> **状态**：未冻结（默认假设下可推进，UI 文案冻结前必须解决）

| 项 | 说明 |
|---|---|
| 当前默认假设 | 后台创建 run-scoped session 并展示来源链接 |
| 当前 task 影响 | 生效提示文案 "仅影响下一次运行；历史和当前运行不变" 为默认假设文案，非最终文案 |
| 冻结 gate | 产品 owner 确认 fork/跳转/历史展示文案（DECK-020 决策单） |
| 冻结 owner | `@CEOOrchestrator` 路由产品 owner |
| 下游影响 | DECK-009 (run-scoped session)、DECK-012 (story-workspace 状态展示) |
| 本 task 处理 | 使用默认假设文案占位，明确标注 `[文案未冻结]`，待 DECK-020 决策后统一替换 |

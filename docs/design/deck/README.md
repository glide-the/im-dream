<!-- [Input] Deck requirement PDF and current Deck frontend/backend implementation. -->
<!-- [Output] Final current Deck requirements, implemented behavior, and deferred boundaries. -->
<!-- [Pos] Canonical Deck business design. -->

# Deck

原始需求参考：[Deck 设计需求 PDF](./Deck设计需求.pdf)。当 PDF、旧草稿与当前业务约束冲突时，
本文件描述的生产行为为当前定稿。

## 业务目标

Deck 是一组可供 Chat 或 Dream 使用的 Agent、Prompt 和 Claude Plugin 引用。用户在轻量启动页选择
已可用 Deck，在 Settings / Work 中完成创建、维护、启停和内容版本提交。

## 启动页

- `/story-workspace/decks` 只展示可运行内容，并按 **Available Decks** 和 **System Decks** 分组。
- 用户 Deck 必须同时满足：已启用、至少有一个内容版本、没有未提交草稿。
- System Decks 分组包含平台 `is_system` Deck，也包含 `publish_block_reason=default_initialized` 的用户默认副本；两者在当前页面均按产品默认内容只读展示，不提供启停或维护。
- 顶部最多展示 14 个等距正方形快捷图标；设置角标进入 `/story-workspace/settings/work`。
- 点击任意用户或系统 Deck 打开预览；ChatAgent 示例进入 Chat 并预填内容，DreamAgent 示例进入独立 Dream 工作台。
- 启动页顶栏保留“创建 Deck”；创建成功后直接打开同一维护弹窗。普通用户 Deck 的预览页也提供编辑快捷入口，系统/默认 Deck 不提供。

## Work 管理

Settings 左侧只有一个“工作台 / Work”分类，内部使用 Deck、资源链接、插件三个页签。Deck 页签负责：

- 搜索、筛选、刷新、分页和查看系统/用户来源；
- 创建用户 Deck，并在同一维护弹窗持续编辑元数据、Agent、Prompt 与 Claude Plugin 引用；
- 用户 Deck 启用、禁用、复制、修改、查看版本和删除；
- 平台系统 Deck 和产品初始化默认副本只读，不出现启停、编辑和删除操作；
- 删除被历史 Chat 引用的 Deck 时，在更多菜单展示相关对话，用户先逐条确认删除对话后再删除 Deck。

## 内容版本

- 新建和每次表单修改先写入可恢复草稿，并推进 `draft_revision`。
- 等价写入不产生新 revision；所有受管表单属于同一个 Deck 聚合草稿。
- 用户显式提交时先读取差异预览，再确认追加不可变 `v1/v2/vN` 快照。
- 提交使用 `expected_draft_revision` 与 `expected_base_version` 做并发校验；冲突保留当前草稿和已发布版本。
- 版本记录默认折叠，通过顶部“版本记录”按钮展开，不建立独立版本工作台。
- 历史 Thread 固定其创建时的 Deck 内容；当前代码不会自动升级，也没有批量升级入口。

CozeLoop 只作为草稿、差异、显式提交、不可变版本和 CAS 冲突的交互参考。Deck 不包含 Workflow、
Agent 编排、Prompt 工作台或 Memory 工作台。

## 数据与接口

- CRUD：`/api/decks`、`/api/voices`
- 版本：`/api/decks/{deck_id}/version-state`、`/versions/preview`、`/versions`
- Claude Plugin 引用：`/api/decks/{deck_id}/claude-plugins`
- 数据：`decks`、`voices`、`deck_claude_plugin_refs` 为草稿事实，`deck_versions` 为不可变快照。
- Schema capability：`dream.deck-content-versions.v1`；缺失时关闭版本能力，不在 Dream 内建表。

## 代码所有权

- 前端：`frontend/src/components/DeckManager.tsx`、`frontend/src/components/DeckEditorModal.tsx`、`frontend/src/components/deck/`
- 后端：`backend/routers/voices.py`、`backend/routers/deck_versions.py`、`backend/services/deck/`
- Thread 上下文：`backend/services/deck/chat_context.py`、`backend/services/deck/runtime_context.py`

市场分发边界见 [deck-register](../deck-register/README.md)。

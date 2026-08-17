<!-- [Input] Deck design units, Admin capability, Dream implementation, and QA lanes. -->
<!-- [Output] Requirement-to-code/test/evidence traceability and test matrix. -->
<!-- [Pos] Deck redesign acceptance ledger. -->
<!-- [Sync] 2026-08-17: trace typed preview Demo dispatch to Chat or the dedicated Dream workbench. -->

# Deck 需求追踪矩阵与测试计划

## 需求 → 设计 → 代码 → 测试 → 验收证据

| 需求 | 设计章节 | 代码 | 自动化 | 验收证据 |
|---|---|---|---|---|
| Deck 主页面最多 14 个正式可用正方形图标 | `deck-management-list.md` §3 | `isDeckHomeVisible`, `DECK_ENABLED_LAUNCH_LIMIT` | source + browser | enabled/published/version/clean 五项过滤、44×44、无 switch |
| 系统内置区分 | 同上 §3 | system shortcut/card classes | source + browser | 快捷盾牌角标、列表系统标签各可见 |
| Work 展示更多内容 | 同上 §4 | `DeckSettingsPanel` | browser | 未发布/草稿/停用仍可搜索并维护 |
| 设置直达 Work | 同上 §2–3 | `App.handleOpenSettingsFromDeck` | browser history journey | 一次点击 URL 为 `/story-workspace/settings/work` |
| Settings 左栏只新增 Work | 同上 §4 | `StoryWorkspaceSettingsPage` | source + browser | Work 可见，独立资源/插件左栏项不存在 |
| Work 内部三页签 | 同上 §4 | `settings-work` route, Work tablist | route + browser | Deck/resources/plugins query 切换 |
| Deck 启停移入 Work | 同上 §4.2 | `DeckSettingsPanel`, existing `updateDeck` | browser success/conflict | 主页面零开关；Work 行尾开关持久化 |
| Deck 相关对话 | 同上 §4.3 | `chatHistoryApi.ts`, `GET /api/claude-agent/threads?deck_id=...`, `DeckSettingsPanel` | API + browser | More 入口、标题/日期预览、分页/加载/空/失败状态 |
| 先删对话再删 Deck | 同上 §4.3 | Chat DELETE, `database.delete_deck` | backend transaction + browser | 有对话 409；逐条永久删除；清空后 Deck 删除解锁 |
| 删除冲突不误报 | 同上 §4.3 | `DeckDeletionConflict`, binding cleanup, snapshot guard | backend unit + real read-only diagnosis | 普通 binding 可清理；runtime snapshot 仍 fail closed |
| 资源链接/插件复用 | 同上 §4.1 | `ConnectorSettingsSection`, `ClaudePluginAdminPage` | browser tab visibility | 无重复状态 owner |
| 原创建并弹出 | `deck-detail-version-history.md` §1 | `DeckManager.tsx` | POST 返回 ID 后 modal | 请求与弹窗断言 |
| 新建后继续更新 | 同上 §1–2 | `DeckEditorModal.tsx`, Deck/Voice/ref/binding APIs | create→edit→reopen | 表单持久化与草稿 revision |
| 所有表单纳入版本 | 同上 §2 | `database.py`, `binding_service.py`, `content_versioning.py` | effective/no-op mutations | revision 只在有效变更推进 |
| 首次 v1 / 后续 vN+1 | 同上 §3–4 | `deck_versions.py`, `deckVersionApi.ts`, `useDeckContentVersions.ts`, submit dialog | v1→modify→v2 | immutable rows/history |
| preview/取消零写 | 同上 §4 | preview API + dialog cancel | row count/request count | 取消无 commit 请求 |
| 冲突/失败保留 | 同上 §6 | service CAS transaction + hook recovery | stale expected revision | 草稿/旧 vN 不变 |
| 默认折叠内容历史 | 同上 §5 | `DeckVersionPanel.tsx` | folded/open/close/reopen | 内容时间线截图 |
| 运行插件版本次级化 | `deck-evaluator-interaction-draft.md` §5 | binding hooks/picker | source/browser | 标明“运行插件”，不冒充内容 vN |
| 排除 Workflow | `deck-impact-review.md` | 当前 Deck UI/transport 无 Workflow | negative source/browser | 入口/请求为零 |
| 排除市场 | `deck-register/README.md` | 当前 UI/i18n 无 publish/install/market | negative source/browser | 入口/请求为零 |
| 历史 Thread 不自动升级 | `thread-version-upgrade.md` | 当前行为保持；apply capability 后续 | negative current contract | 无自动/批量写 |
| 同一 Chat 切换 Deck 内 Agent | `2026-08-03-deck-context-badge-design.md` §3–8；`deck-business-sequences.md` §10 | `PluginReceiptBadge.tsx`, `ChatView.tsx`, `claude_agent.py`, `database.select_chat_thread_voice` | source + route/CAS unit + provider-free browser | 当前 Agent pressed；同 Thread/Deck；发送时成员校验；CAS 冲突不启动；每轮 provenance metadata |
| 预览 Demo 按 Agent 类型分流 | `deck-management-list.md` §3.1；`deck-business-sequences.md` §11 | `DeckManager.tsx`, `DeckManagerPanels.tsx`, `useStoryWorkspaceDreamLaunch.ts` | source + provider-free browser + real只读边界 | Chat 示例只预填；Dream 示例走 Dream start 并进入独立工作台；重复点击受控；失败留页可重试；不伪造 Chat Thread |

## Schema/事务映射

| 功能 | Admin Drizzle | Dream 后端 | 前端 |
|---|---|---|---|
| 草稿 CAS | `decks.draft_revision` | 所有受管写先锁 aggregate 后 advance | mutation 成功后刷新 state |
| 当前版本 | `latest_version/published_draft_revision` | list/detail projection | 列表/头部状态 |
| 不可变 commit | `deck_versions` + no-update/no-delete triggers | canonical snapshot/hash + append | preview/confirm/history |
| capability | `dream.deck-content-versions.v1` receipt | 缺失时 version API 503 | 提交禁用、编辑可继续 |

## 测试矩阵

| 层级 | 覆盖 | 车道 |
|---|---|---|
| 静态/类型/构建 | DTO、API、组件、无禁用入口、响应式 CSS | 技术验证 |
| Admin schema | columns/table/FK/check/trigger/capability/migration inventory | 隔离技术验证 |
| 后端单元 | preview 零写、v1/v2、history、hash/no-op、content/binding CAS preservation、same-Deck Agent CAS 与 provenance metadata | provider-free 技术验证 |
| API/组件合同 | content state/preview/commit/history，表单刷新，提交确认 | 技术验证 |
| Playwright | enabled14→Settings→Work→相关对话→逐条删除→空状态；创建→修改→v1→修改→v2→历史；error/390px | mocked production-entry 技术验收 |
| 真实业务 | 只在用户指定现有真实账户/Deck 且本机完整服务可用时执行 | 单独报告，不以 mock 冒充 |

## 验收门

1. Admin migration 先发布，Dream 才显示版本事实；不得 runtime DDL。
2. vN snapshot 必须覆盖 Deck、Agents、Claude refs、Agent type/active binding。
3. 等价保存、preview、取消、展开/收起不产生业务版本写。
4. commit 409/500 后旧版本和草稿均保持可恢复。
5. Deck 主页面不得包含完整列表、状态筛选或启停控件；这些仅属于 Work / Deck。
6. 本期页面不出现 Workflow 或市场入口。
7. 有相关 Chat 时不得直接删除 Deck；相关对话未知/失败不得当作空列表；普通未使用 binding 不得误报为历史 Chat。
8. Chat 内只能选择当前 Deck 的已启用 Agent；Deck、内容版本、插件 receipt 与 Thread ID 不得随 Agent 选择改变。
9. Deck 预览示例必须按服务端 `agent_type` 分流；DreamAgent 复用现有 Dream start 并进入独立 Dream 工作台，禁止降级为 Chat 预填。

执行命令、退出码、通过数量和截图路径在本次最终交付中记录；未执行的真实业务车道必须说明原因。

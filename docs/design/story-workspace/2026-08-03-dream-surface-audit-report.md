# Dream Surface 机制只读审计报告（任务一）

> **审计人**: drama-forge maintainer
> **日期**: 2026-08-03
> **性质**: 只读审计。未修改任何设计文档与代码。
> **审计对象**: D003 / D004 / PLAN 描述的「Deck × Dream 联动」（`.dream/` 协议目录 + surfaces 透出 + 跳转链 + 独立执行页）与现有 Deck 插件体系、会话链路、前端、合同层的兼容性。

---

## 1. 审计范围与方法

### 1.1 已读设计文档（全文）

| 文档 | 路径 |
|------|------|
| D003 | `docs/design/story-workspace/design_003_story-workspace-episodes-metadata-review.md` |
| D004 | `docs/design/story-workspace/design_004_story-workspace-dream-surface-execution-page.md` |
| PLAN | `docs/design/story-workspace/2026-08-03-dream-surface-execution-implementation-plan.md` |
| PRD | `docs/design/story-workspace/story-workspace-prd.md`（重点 §3.5–3.6、DEC-007/009/010/017/018/026） |
| 上游 packer 设计 | `docs/design/deck/drama-forge-workspace-init-design.md`（§6 扩展插槽、§7 错误模型，D004 引用其为上游机制） |

### 1.2 已读代码文件（全文或相关段落）

| 文件 | 关键位置 |
|------|----------|
| `backend/services/claude_plugin/workspace_packer.py` | `pack_workspace_plugins()` :104；冻结分支 :128-151；新鲜 pack :153-221；refs 排序 :58-70；`_ensure_packed_entry` :246-312 |
| `backend/services/claude_plugin/workspace_init.py` | `load_init_profile()` :87-183（fail-closed 注释 :91）；`execute_init_profile()` :186-214；venv :240-321 |
| `backend/claude_agent/service.py` | `_pack_thread_workspace_plugins` :202-218；pack 调用点（assemble_context）:1172-1187；`story-workspace-output` SSE :1317-1319 |
| `backend/claude_agent/workspace_context.py` | `<workspace_context>` 模板全文 :61-123 |
| `backend/routers/claude_agent.py` | `POST /api/claude-agent/threads` :435-468；`GET …/plugin-load-receipt` :471-523 |
| `backend/libs/claude_agent_kit/server/plugin_launcher.py` | manifest 读取 :48-86（唯一 CLI 边界消费方） |
| `backend/story_workspace/contracts.py` | 全文 434 行（契约清单） |
| `backend/routers/story_workspace.py` | `_audit_review_action` :367-389；`_transition_pending_review` :392-492；`_REVIEW_RESOURCES` :59-63；workflow-runs 路由 :1130-1193 |
| `backend/models/workflow_run.py` | `RunStatus` :26-47；`WorkflowRun` 不变量 :67-164 |
| `backend/services/workflow/run_service.py` | `_ALLOWED_TRANSITIONS` :98-125；幂等键落库 :456-461、:690-739 |
| `backend/database.py` | `review_status` CHECK :701-702/:738-739/:766-767；`chat_message` :603-611；`workflow_runs` 幂等 UNIQUE :1178-1186；`workflow_run_token_consumptions` :1208-1221；`workflow_run_transitions`（append-only 触发器）:1223-1268；`save_chat_message` :4249-4296 |
| `backend/services/deck/builtin_plugin.py` | `BUILTIN_DECK_PLUGIN_ID` :18；制品 digest 算法（全文件哈希）:28-43 |
| `backend/services/deck/story_workflow_gateway.py` | `StoryWorkflowApplicationGateway` :71+ |
| `backend/services/story_workspace/agent_integration.py` | `parse_agent_story_output` :29-58 |
| `plugins/ink-dream-story/` | 全目录清单：仅 `README.md`、`.claude-plugin/plugin.json`、`skills/dream-story-workflow/SKILL.md`；**无 `.ink/` 目录** |
| `frontend/src/pages/story-workspace/StoryWorkspaceDreamPage.tsx` | 全文 12 行（裸容器） |
| `frontend/src/App.tsx` | `dreamContent = <ChatView …/>` :1484-1499 |
| `frontend/src/router/story-workspace.tsx` | 路由 union :23；PATHS :35-40；精确路径匹配 :52-67；output 订阅开审阅面板 :130-135 |
| `frontend/src/components/chat/ChatPanel.tsx` | `story-workspace-output` 帧不进消息气泡 :421-424 |
| `frontend/src/lib/story-workspace-events.ts` | 全文 37 行 |
| `frontend/src/hooks/story-workspace/contracts.ts` | 全文 84 行（无 surface/guidance 类型） |

### 1.3 方法

逐条对照审计问题清单（A1–E15），每条结论给三档判定【兼容】【需调整】【冲突】，附 `文件:行号` 证据。判定口径：

- **兼容**：现有代码/设计可直接容纳，无需修改或仅需纯新增。
- **需调整**：机制可落地，但设计措辞、时序假设、落点选择或代码前置改造有一项以上偏差。
- **冲突**：设计前提与代码事实直接矛盾，不改设计或不改代码则无法按 PLAN 实施。

---

## 2. 逐条结论

### A. packer 兼容性

#### A1. packer 调用链能否容纳「profile 声明 surfaces 才物理映射 `.dream/`」插槽？【兼容】

**证据**：`pack_workspace_plugins()` 当前链路为——调用方 `backend/claude_agent/service.py:202-218`（`_pack_thread_workspace_plugins`，在 `assemble_context` 内 `service.py:1172-1187` 以 `asyncio.to_thread` 调用），入参 `(db, *, workspace, deck_id)`，返回 receipt dict。新鲜 pack 分支（`workspace_packer.py:153-221`）的步骤为：读 refs（:153，`:66` `ORDER BY r.order_index, r.created_at, r.plugin_installation_id`）→ 逐 ref 校验/复制制品（:165-172）→ `load_init_profile`（:174）→ `execute_init_profile`（:176-181）→ venv（:182-189）→ 写 manifest（:203-214）→ 写 receipt（:215-220）。

D004 §3.4.4 的 8 步时序与该结构一一对应，插槽「复制制品之后、写 manifest 之前」与上游 drama-forge 设计 §6 伪码位置（`docs/design/deck/drama-forge-workspace-init-design.md:140-153`）一致，无步骤冲突。

**注（实现期澄清，非阻断）**：`workspace.json.plugins[]` 需要**全量**插件清单（D004 §3.4.2），而代码中 `manifest_entries` 在逐 ref 循环内增量构建（`workspace_packer.py:192`）。物理映射 `.dream/` 必须放在循环**之后**、写 manifest 之前（PLAN Task 1 Step 6 伪码正是如此：`materialize_dream_surface(workspace, deck_id, manifest_plugins, …)`）；若按 D004 §3.4.4 线性 8 步字面理解为「循环内第 5 步」，多插件 Deck 会拿到不完整 plugins[]。建议 D004 §3.4.4 补一句「第 5 步在全部制品复制与 init 完成后执行一次」。

#### A2. `load_init_profile()` 校验严格度与新增 `surfaces[]` 可选字段【兼容】

**证据**：`load_init_profile()`（`workspace_init.py:87`）对**已解析字段** fail-closed（注释 :91「Any malformed profile raises — fail-closed」；schema_version 不等于 `workspace-init/v1` 即拒绝 :108-112；`runtime_dirs`/`workspace_files`/`python` 类型与路径校验 :114-177）。但它**不拒绝未知键**——函数只 `payload.get()` 已知字段，未对 `payload` 做 extra-keys 检查。因此：①新增可选 `surfaces[]` 不会被现有校验拒绝（存量 profile 无该键行为不变，符合 DEC-027）；②profile 保持 v1 不升版可行（schema 校验是等值比较 :108，不是版本协商）。

PLAN Task 1 的 6 组非法用例（未知 name / 保留目录 / 无点前缀 / 越界路由 / 多层路径）全部是**新字段上的新校验**（`validate_surfaces`），与既有校验逻辑正交，错误码 `CLAUDE_PLUGIN_INIT_PROFILE_INVALID` 与现有 `WorkspaceInitError.code` 体系（`workspace_init.py:38-41`、packer 转包 `_as_pack_error` `workspace_packer.py:33-34`）一致。

**注（建议改进）**：未知键静默忽略意味着 `surfaces` 拼写错误（如 `surface`）会 fail-open 为「无 surface」，不会报任何错。建议在 `load_init_profile` 增加已知键白名单警告（receipt warning，不 fail），列入实现期可选项，不要求改设计。

#### A3. 冻结语义与 D004「只校验不重建」【兼容】

**证据**：冻结分支（`workspace_packer.py:128-151`）已有 manifest 时：逐条 `_ensure_packed_entry(allow_repair=True)` 重校验 digest、缺失/损坏从制品库修复（:246-312），`_ensure_frozen_runtime` 仅在 venv 缺失时按 digest 重建（:224-243）；**init 步骤绝不重跑**——代码注释 :131-132「Init steps are never re-run; the managed venv is a derived cache」。版本永不更换（模块 docstring :11-16「plugin versions are never swapped mid-thread」）。

D004 §3.4.4「冻结只校验 `.dream/workspace.json` 存在且与 manifest surfaces 一致、缺失不重建（属初始化结果，非 venv 类派生缓存）」与上述语义**完全同构**：`.dream/` 与 `runtime_dirs`/`workspace_files` 同属 init 产物，现有代码对 init 产物本就不重跑不修复；D004 新增的「校验存在性」是比现状略严的新增检查（现状对 init 产物连存在性都不校验），方向一致、无冲突。PLAN Task 1 Step 6 冻结分支伪码（缺失即 `WorkspacePackError`）可落地。

#### A4. 幂等/原子性差距【需调整】

**证据**：现状 pack **无任何回滚/清理**：逐 ref 循环中若第 2 个插件 profile 非法抛错（`workspace_packer.py:190-191`），第 1 个插件的制品拷贝（:172）与 init 产物（`execute_init_profile` 已写 `runtime_dirs`/`workspace_files`，`workspace_init.py:197-213`）已留在工作区；manifest 未写 → 下次 pack 走新鲜分支重跑，靠 `create-if-missing`（`workspace_init.py:199-201`、:206-209）收敛到相同内容。即现状是「半成品可残留、靠幂等重跑收敛」，不是「原子失败」。

D004 §3.4.4 要求「第 5 步任一文件写失败 → 整个 pack 失败，不留半截目录」。PLAN Task 1 的 `materialize_dream_surface` 参考实现（PLAN :195-211）是 `mkdir` + 两个 `write_text`，**非原子**：README 写成功、workspace.json 写失败即留半截 `.dream/`；且 create-if-missing 语义下半截文件会在重 pack 时被保留。

**建议修法（改代码，实现期）**：`materialize_dream_surface` 改为「临时目录写入 → 校验两文件齐全 → `os.rename` 原子就位」，或将 D004「不留半截目录」措辞修订为「重 pack 收敛到字节一致产物」。倾向前者（改代码），因为 D004 的原子性要求本身合理且成本极低。设计文档可不动。

#### A5. 多插件冲突裁决【兼容】

**证据**：refs 读取有确定顺序（`workspace_packer.py:66` `ORDER BY r.order_index, r.created_at, r.plugin_installation_id`），pack 逐 ref 处理（:158）。现状无 surfaces 概念故无冲突处理；既有 init 产物（`runtime_dirs`/`workspace_files`）多插件碰撞时以 create-if-missing 自然「先写者胜出」（`workspace_init.py:199-213`），无警告记录。

D004「按 pack 顺序前者胜出，receipt 记录冲突警告」可直接映射到既有确定顺序；receipt 已有自由扩展空间（`workspace_packer.py:215-220` 增量 update），新增 `warnings` 键不破坏任何消费方（receipt 唯一 REST 消费方 `plugin-load-receipt` 端点原样透传，`routers/claude_agent.py:509-514`）。新增行为，无冲突。

### B. 会话/API 兼容性

#### B6. thread 创建链路与设计时序【需调整】

**证据**：`POST /api/claude-agent/threads`（`routers/claude_agent.py:435-468`）只做两件事：校验 Deck 存在且 enabled（:449-466）、`database.create_chat_thread(user_id, deck_id=…)` 锁定 `chat_thread.deck_id`（:467）。**不分配工作区目录、不 pack**。pack 实际发生在**首个 agent turn**：`assemble_context` 内 `get_or_create_workspace` 建目录（`service.py:1021-1028`）后调 `_pack_thread_workspace_plugins`（`service.py:1172-1187`），且**每个 turn 都会调**（幂等，冻结后走 :128-151 分支）。

D004 §3.4.1「后端创建 thread（deck_id 锁定，分配会话工作区目录）→ pack_workspace_plugins(workspace, deck_id) # 每个会话创建时执行一次」与代码事实有两处偏差：①pack 时刻是首个 turn 而非 thread 创建；②pack 每 turn 执行（冻结语义保证等价于「生效一次」）。

**实际影响**：前端若在「创建 thread 后立即」查询 surfaces，此刻 manifest 尚不存在，`plugin-load-receipt` 端点返回 `workspace_found: false`（`routers/claude_agent.py:500-507`）。「Dream 页选 Deck 点 Chat → 创建 thread → pack」链路本身吻合（前端 ChatView 已有 Deck 选择与 `createThread(deckId)`，`frontend/src/components/chat/ChatView.tsx:257-259`、:694），缺口仅在**时序表述与 surfaces 首次可见时机**。

**建议修法（改设计）**：D004 §3.4.1/§3.5 修订为「pack 发生在会话首个 agent turn；surfaces 在首个 turn 完成 pack 后可见；此前前端按无 surface 处理」。该修订与 DEC-028「缺省即隐藏」自然衔接，无代码前置。

#### B7. 会话 payload 现状与 `surfaces` 承载、旧会话兼容【需调整】

**证据**：代码中**不存在** D004 §3.5 假设的「既有 workspace_context 注入模式的会话 payload（与 plugins / receipt 同层）」这一对象。两个被混淆的事实：①`<workspace_context>` 是注入 **agent 用户消息**的提示块（`backend/claude_agent/workspace_context.py:61-123`），不是前端会话 API payload；②前端可见的会话级 workspace 事实载体是 `GET /api/claude-agent/threads/{thread_id}/plugin-load-receipt`（`routers/claude_agent.py:471-523`），它把 `.ink/launch-manifest.json` 与 `.ink/plugin-pack-receipt.json` **整文件透传**（:509-522）。

由此得出两个结论：①**透出链路比 PLAN 假设的更顺**——packer 一旦在 manifest/receipt 写入 `surfaces`，该既有端点零改动自动透给前端，PLAN Task 2 的 `build_session_payload(session)` 是不存在的虚构挂载点，应改为「消费 plugin-load-receipt 端点（或在 thread payload 上增字段）」；②旧会话兼容设计（D004 §3.5「无 `surfaces` 字段 → 前端按无 surface 处理，不报错、不补探测」）**成立**——manifest 无该键时端点原样返回无该键的 JSON，前端缺省隐藏即可，前端零文件系统探测也符合现状（该端点是后端读文件后透传，不是前端探测）。

**建议修法（改设计/PLAN）**：D004 §3.5 与 PLAN Task 2 把「会话 payload」明确为 `plugin-load-receipt` 端点响应（或新增 thread payload 字段），删除 `build_session_payload` 虚构接口；保留 manifest → receipt 兜底顺序。

### C. 前端兼容性

#### C8. StoryWorkspaceDreamPage 现状与 D003/D004 差距【兼容】

**证据**：`StoryWorkspaceDreamPage.tsx` 全文 12 行，是裸容器；`App.tsx:1484-1499` 将 `dreamContent` 设为完整 `<ChatView …/>`（含 `requestedDeckId`/`landingTab="history"`）。**Dream 首页默认 Chat 页已是现状**，与 D004「Dream 首页默认 Chat 页，发起对话进入 Agent 对话」一致。三栏方面：`StoryWorkspaceLayout` 已提供 sidebar + 主区 + 360px 审阅面板（`router/story-workspace.tsx:171-206`），审阅面板 `StoryWorkspaceReviewDetail` 已实现 story/character/scene 级确认/驳回（`router/story-workspace.tsx:173-184`），`story-workspace-output` SSE 事件驱动自动打开审阅面板（:130-135）。

差距（属未实现范围而非冲突）：D003 的 episodes 投影、Prompt Composer、ReviewGate UI、分集列表/详情 Tabs、`/story-workspace/episodes*` 页面均未实现；D003 §5.2 的三栏骨架与现状「Chat 占满主区」是两种 Dream 主页形态。D004 的增量（surface、按钮、执行页）不依赖这些未实现项的存在（按钮可见条件是会话 surfaces + runId，见 §4.1）。

**结论**：对 D004 兼容；对 D003 的差距是既有设计债，不在本次增量引入，标注即可。

#### C9. Dream 提案消息卡片挂靠点【冲突】

**证据**：代码中**不存在 Chat 消息流内的「Dream 提案 pending proposal 卡片」**。事实链：Agent 的故事 JSON 由后端从 assistant 全文解析（`agent_integration.py:29-58`），持久化为 `story_workspace_*` 表行；SSE 侧发出独立的 `story-workspace-output` 帧（`service.py:1317-1319`），前端 `ChatPanel.tsx:421-424` 收到该帧后**只发浏览器事件、不进消息气泡**（`publishStoryWorkspaceOutput` → `story-workspace-events.ts:19-24` → `router/story-workspace.tsx:130-135` 打开审阅面板）。提案的可见形态是 Dream 域审阅面板/列表行，不是 Chat 消息卡片。全仓 grep `proposal|提案` 仅命中 story-workspace 域组件，无 Chat 域卡片组件。

PLAN Task 4 假设「卡片渲染处位于前端 Chat 域消息流」（PLAN :369）并要在其上挂 `StoryWorkspaceSurfaceLinkButton`；D004 §0.2 也称「Dream 提案 JSON 合同属 Chat 域既有合同（SSE 消息流中的提案消息类型）」——「提案消息类型」实际不存在，存在的是独立于消息流的 `story-workspace-output` 生命周期帧。

**建议修法（改设计为主）**：两条路线择一并修订 D004 §4 与 PLAN Task 4——①新建 Chat 消息卡片：`story-workspace-output` 帧同时落一条持久化消息（或前端合成卡片），按钮挂其上，工作量含消息合同扩展；②把跳转按钮挂靠点改为既有审阅面板/列表行（`StoryWorkspaceReviewDetail` / 故事列表操作列），不新增 Chat 卡片。路线②与现状零冲突、工作量小，但与 D004 已拍板决策 #4「Chat 跳转入口 = 消息内卡片按钮」矛盾，需 D004 增量修订决策。这是本审计最重要的设计修正点。

#### C10. `?run=` 深链与执行页路由落位【需调整】

**证据**：story-workspace 前端不是 react-router，而是自研 state router（`router/story-workspace.tsx`）：路由类型为封闭 union `'dream' | 'stories' | 'characters' | 'scenes'`（:23）；`resolveStoryWorkspacePath` 只做**精确路径等值匹配**（:52-67），不支持 `:param` 段；query string 完全不解析（仅看 `window.location.pathname`，:53）；history 操作手写 pushState/replaceState（:78-82、:159-167）。

落位评估：新增 `/story-workspace/runs/:storyWorkspaceRunId/execution`、`/story-workspace/episodes/:id/review`、`?run=` 需要：①扩展 union 与 `STORY_WORKSPACE_PATHS`；②给 resolver 加参数化匹配（前缀分段比较）；③新增 query 解析（`URLSearchParams`）；④App 侧 `currentView` 仍由路径前缀 `/story-workspace` 命中（`App.tsx:1476`），不受影响。结构上全部逻辑集中在 `resolveStoryWorkspacePath` 单一 choke point，改造可控，与现有架构不冲突。

**建议修法（改代码，实现期）**：按上述①②③扩展 state router；无需改设计。注意 `replaceWithCanonicalPath`（:78-82）目前会丢弃 query，深链实现时须保留 `?run=`。

### D. 合同与数据兼容性

#### D11. ReviewEvent action=guide 持久化与 DEC-026【冲突】（关键风险点，明确结论）

**证据**：
- `backend/story_workspace/contracts.py` 现有契约清单：枚举 `StoryWorkspaceReviewStatus/ContentStatus/AssetStatus/StoryType/RoleType/BatchAction/ResourceType`（:20-59）， dataclass `StoryWorkspaceStory/Character/Scene/Workspace/StoryCharacter/SceneCharacter/*Detail/Paginated*/PaginationInfo/*Filter/ReviewActionRequest/BatchReviewRequest/BatchReviewResponse/Stats/Agent*Output/Agent*Payload/*Patch`（:62-392）。**无 `StoryWorkspaceReviewEvent`、无 `ReviewAction` 枚举、无 `StoryWorkspaceGuidanceCommand`、无 `StoryWorkspaceExecutionProjection`、无 `StoryWorkspaceSurface`**。
- 持久化侧：`review_status` 是三张资源表上的**状态列**（`database.py:701-702`、:738-739、:766-767，`CHECK(review_status IN ('pending','confirmed','rejected'))`），每资源一行一态，**不是事件日志**——没有 event ID、actor、run 关联、request ID、timestamp 的承载列。
- 现有「审阅审计」实为 **logger 输出**：`_audit_review_action`（`routers/story_workspace.py:367-389`）只 `logger.info`，不落任何表。
- DEC-026：`backend/database.py` 只读、禁止新增 Schema/DDL（PRD §3.5.4、D003 §6.3、PLAN Global Constraints）。

**明确结论**：`review_status` 列模型**不能**承载 `StoryWorkspaceReviewEvent`（含 action=guide）。它是枚举状态列而非事件流；把 guide 塞进去既没有事件行结构也违反 CHECK 约束语义。D004 §5.3「每条指导 = 一条 ReviewEvent（含 actor、run、指令摘要、timestamp、request ID）；合同层扩展，持久化层不动」在「需要可查询的持久审计」解读下**与 DEC-026 冲突**——现有库中不存在任何可承载该事件的表。

**可行的无 DDL 落点（必须三选一并写回设计）**：
1. **复用 `chat_message` 表**：`metadata` JSON 列可携带 `{kind:"story-workspace-guidance", run_id, actor, request_id, idempotency_key}`，`id` 主键可作幂等键（见 D12）。与 DEC-032「复用 thread 作传输通道」天然同路；缺点是需要前端过滤不渲染（见 D13）。
2. **沿用 `_audit_review_action` 的 log-only 模式**：审计只进应用日志，不供页面查询。「指导历史」列表则无法从库读出，与 D004 §5.3「指导历史（指令+状态+时间）」页面需求矛盾——除非指导历史也读 chat_message。
3. **复用 `workflow_run_transitions`**：append-only 且有 `actor_id`/`reason_code`（`database.py:1223-1237`），但其不变量要求状态变迁（`run_service.py:179-185`「a transition must change status」），guidance 不产生状态变迁，语义不合，**不推荐**。

结论：合同层新增 `StoryWorkspaceGuidanceCommand`/`StoryWorkspaceExecutionProjection`/`StoryWorkspaceSurface`/`ReviewAction.guide` 本身与 DEC-026 无冲突（contracts.py 是纯 Python 合同模块）；**冲突点仅在 ReviewEvent 的持久化承载**，推荐路线 1（chat_message.metadata），需 D004 §5.3/§9 DEC-032 增量修订明确承载表与「不渲染」的过滤机制。

#### D12. guidance 幂等键存储【需调整】

**证据**：不新增表的前提下，既有幂等机制有三处：①`workflow_runs` 的 `UNIQUE(workspace_id, created_by, idempotency_key)`（`database.py:1186`）——但作用域是「创建 run」，guidance 不是 run 创建，复用会污染 run 幂等命名空间且无处可写；②`workflow_run_token_consumptions`（`database.py:1208-1221`，`token_digest` PK，append-only 触发器保护 :1254-1268）——作用域是 preflight token 消费，语义专属，不可直接复用；③`chat_message.id` 主键 + `save_chat_message` 的 `INSERT OR REPLACE`（`database.py:4288-4291`）——客户端幂等键作 `message_id` 时，重放同键同内容是无害覆盖，天然去重。

**结论**：有可复用机制，首选 ③（与 D11 路线 1 同一条承载）：guidance 请求以 `idempotency_key` 作为 `chat_message.id`（或派生 `guide_<key>`），同键重放 INSERT OR REPLACE 收敛为一条记录。弱点：同键**不同**内容会被静默覆盖而非报 409 冲突，严格性弱于 `workflow_runs` 的冲突检测（`run_service.py:456-461` 先查后判）。若产品要求冲突可观测，需在服务层先 `SELECT` 比对再决定 202/409——纯应用层逻辑，无需 DDL。

**建议修法（改设计）**：PLAN Task 3 补充幂等键承载说明（chat_message.id + 服务层先查比对），并在测试 `test_guidance_idempotent_replay` 中断言「同键同内容 → 单条记录；同键不同内容 → 409」。

#### D13. DEC-032 复用 thread 传输与现有消息流【需调整】

**证据**：`backend/claude_agent/` 消息流现状：每个 turn = 一次 `POST /api/claude-agent` → `execute_session`（`service.py:1262-1328`）；用户消息一律 `_persist_user_message` → `save_chat_message` 落 `chat_message`（`service.py:1367-1399`）；`GET /threads/{id}/messages` 返回全部消息（`routers/claude_agent.py:585-599`），前端全量渲染。会话恢复机制存在（`resume=true` + `claude_session_id`，`service.py:1131-1162`），guidance 作为「同一 thread 的新 turn」技术上可行（run 状态机允许 `continuing` 态存在，`models/workflow_run.py:34`、`run_service.py:122-124`）。

**矛盾点**：DEC-032 要求「指导消息不渲染为 Chat 会话消息」，但现状凡 `save_chat_message` 落库的消息都会出现在 messages API 并被渲染。要让「复用 thread 传输」与「不渲染」同时成立，必须二选一：①落 `chat_message` 并在 `metadata` 打 `kind:"story-workspace-guidance"` 标记，**前端 messages 渲染层过滤**（新增过滤逻辑，前端零schema改动）；②不落 chat_message，另辟「不入库的指令帧」直接注入 runner——但现有 runner 是单 turn 流式调用，无 mid-turn 注入通道（除 tool confirmation 外），等于新建传输机制，成本高。

**建议修法（改设计）**：DEC-032 增量修订为「指导以 metadata 标记的 user 消息落 chat_message（承载幂等键与审计字段），Chat 视图按 metadata.kind 过滤不渲染；指导历史由执行页按 kind 反查」。这与 D11 路线 1、D12 首选③三者自洽，是同一条承载链。另外「Agent 阻塞等待用户输入」（`awaiting-guidance`）在现有状态机中没有对应 RunStatus 枚举值（`models/workflow_run.py:26-37`），该 UI 态只能从 `continuing` + 投影推断或后续扩展，设计需注明这是投影态而非新枚举（否则又要动 DDL）。

### E. 插件侧兼容性

#### E14. `plugins/ink-dream-story/` 无 `.ink/workspace-init.json`【需调整】

**证据**：`plugins/ink-dream-story/` 全目录仅 3 个文件：`README.md`、`.claude-plugin/plugin.json`、`skills/dream-story-workflow/SKILL.md`；**无 `.ink/` 目录，无 workspace-init.json**。因此按现状 pack 该制品时 `load_init_profile` 返回 None（`workspace_init.py:95-96`），走「无 profile → 跳过」兼容路径，永远不会物理映射 `.dream/`——**Dream surface 全链路对内置插件当前是关闭的**（D004 §8 风险表已预见「profile 未上线前 surfaces 全链路降级为无 surface」）。

**改造点**：①在 `plugins/ink-dream-story/.ink/workspace-init.json` 新增 profile（`schema_version: workspace-init/v1` + `surfaces: [{name:"dream", protocol_dir:".dream", entry_route:"/story-workspace/dream"}]`，可选 `runtime_dirs`/`workspace_files`）；②注意 digest 级联：`plugin_artifact_digest()` 对目录全部文件哈希（`builtin_plugin.py:28-43`），新增文件 → digest 变化 → `deck_runtime_plugin_locks.lock_json` 内 `artifact_digest`（seed 于 `builtin_plugin.py:130-140`）与 `claude_plugin_installations`/`deck_claude_plugin_refs` 中已存的 digest 全需要刷新；`seed_builtin_deck_plugin` 是「每库一次」INSERT（:52-62），**既有数据库不会自动重 seed**，需要一条升级路径（重 seed 脚本或安装记录 digest 迁移）。

**建议修法（改代码前置）**：制品加 profile 属实现期任务；但「digest 变化后既有 DB 的安装/lock 如何迁移」必须在 PLAN 中补一个前置步骤（或明确「仅新装库生效，旧库接受无 surface 降级」），否则 Task 6 的 e2e 在旧库上会静默走无 surface 路径，验收假阳性。

#### E15. launch-manifest 增加 `surfaces[]` 对现有消费方【兼容】

**证据**：`.ink/launch-manifest.json`（schema `claude-launch/v1`）的全部读取点：①`plugin_launcher.read_workspace_launch_manifest`（`plugin_launcher.py:48-86`）——只校验 `schema_version`、读 `plugins[]`，**未知键不校验不拒绝**（无 extra=forbid 式检查），`surfaces` 键透明忽略；②packer 冻结分支（`workspace_packer.py:133-149`）——只 `.get("plugins")`/`.get("runtime")`/`.get("init_steps")`，未知键透明忽略；③`GET …/plugin-load-receipt`（`routers/claude_agent.py:515-522`）——整文件透传，`surfaces` 自动出现在响应中（对前端是**新增可见字段**，前端旧代码不认识即忽略，无破坏）；④测试（`backend/tests/test_claude_plugin_pipeline.py`、`test_real_cli_drama_forge.py`、`test_workspace_init.py`、`test_claude_agent_runner.py`）——均围绕 plugins/venv 断言，新增键不触礁。

**结论**：增加 `surfaces[]` 不破坏任何现有消费方；schema 保持 `claude-launch/v1` 不升版成立（与 A2 同理：消费方做等值校验而非版本协商）。无需改动。

---

## 3. 问题汇总表（按严重度排序）

| # | 条目 | 严重度 | 结论 | 摘要 |
|---|------|--------|------|------|
| 1 | C9 | **阻断实现** | 冲突 | PLAN Task 4 的挂靠点「Chat 消息流中的 Dream 提案卡片」不存在；`story-workspace-output` 是不进消息气泡的生命周期帧（ChatPanel.tsx:421-424）。按钮无处可挂，必须先决策「新建 Chat 卡片」还是「改挂审阅面板」。 |
| 2 | D11 | **阻断实现** | 冲突 | ReviewEvent（含 action=guide）无持久化承载：`review_status` 是状态列非事件日志（database.py:701-702 等），现有审阅审计仅 logger（routers/story_workspace.py:367-389），DEC-026 禁新表。必须选定 chat_message.metadata / log-only 承载并写回 D004。 |
| 3 | B6 | **阻断实现（时序前提）** | 需调整 | pack 发生在首个 agent turn 而非 thread 创建（service.py:1172-1187 vs routers/claude_agent.py:435-468）；D004「会话创建时物理映射 + 会话 API 透出」的时序表述错误，surfaces 首次可见时机需重新定义。 |
| 4 | D13 | 需设计澄清 | 需调整 | 「复用 thread 传输但不渲染为 Chat 消息」与 save_chat_message 全量渲染现状矛盾；需选 metadata 标记 + 前端过滤路线。另 `awaiting-guidance` 无 RunStatus 对应枚举，需注明为投影态。 |
| 5 | D12 | 需设计澄清 | 需调整 | guidance 幂等键无专属表；可复用 chat_message.id（INSERT OR REPLACE 去重）+ 服务层先查比对，但冲突语义弱于 workflow_runs，需 PLAN 补测试断言。 |
| 6 | E14 | 需设计澄清 | 需调整 | 内置插件无 `.ink/workspace-init.json`；新增后 digest 变化（builtin_plugin.py:28-43），既有 DB 的 installation/lock 不会自动迁移（seed 每库一次 :52-62），e2e 可能在旧库静默降级。 |
| 7 | B7 | 需设计澄清 | 需调整 | 「会话 payload（与 plugins/receipt 同层）」对象不存在；真实落点是 plugin-load-receipt 端点整文件透传（routers/claude_agent.py:471-523）——比 PLAN 假设更有利，但 PLAN Task 2 的 `build_session_payload` 是虚构接口，需改。 |
| 8 | C10 | 建议改进 | 需调整 | 自研 state router 仅精确路径匹配（router/story-workspace.tsx:52-67），需扩展参数路由与 query 解析；`replaceWithCanonicalPath` 会丢 `?run=`。单一 choke point，改造可控。 |
| 9 | A4 | 建议改进 | 需调整 | pack 无回滚（现状靠 create-if-missing 重跑收敛）；PLAN 的 materialize 参考实现非原子，与 D004「不留半截目录」有差距，建议 temp-dir + rename。 |
| 10 | A1 | 建议改进 | 兼容（附注） | `workspace.json.plugins[]` 需全量清单，物理映射必须在逐 ref 循环之后；D004 §3.4.4 线性 8 步建议补一句说明。 |
| 11 | A2 | 建议改进 | 兼容（附注） | 未知 profile 键静默忽略，`surfaces` 拼写错误会 fail-open；建议加白名单警告（可选）。 |
| 12 | C8 | — | 兼容 | Dream 首页=Chat 已是现状（App.tsx:1484-1499）；D003 三栏 episodes 差距属既有未实现范围，不被本增量阻塞。 |
| 13 | A3 / A5 / E15 | — | 兼容 | 冻结语义、冲突裁决顺序、manifest 消费方均无需改动。 |

**三档计数**：【兼容】6 条（A1、A2、A3、A5、C8、E15）；【需调整】7 条（A4、B6、B7、C10、D12、D13、E14）；【冲突】2 条（C9、D11）。

---

## 4. 给任务二（修复）的输入清单

### 4.1 改设计文档（任务二主战场）

| 优先级 | 文档/章节 | 修订内容 |
|--------|-----------|----------|
| P0 | D004 §4 + §0.1 决策 4 + PLAN Task 4 | **C9**：决策「新建 Chat 提案消息卡片」或「按钮改挂 StoryWorkspaceReviewDetail/列表行」。推荐后者（零新消息合同），但需改写已拍板决策 #4；若坚持消息卡片，需新增 Chat 域消息合同定义（原「Chat 域既有合同」表述删除）。 |
| P0 | D004 §5.3 + §9 DEC-032 + PLAN Task 3 | **D11+D12+D13 合并修订**：明确 ReviewEvent/guidance 的无 DDL 承载 = `chat_message`（metadata.kind 标记 + id 作幂等键 + 服务层先查比对）；「不渲染」= 前端 messages 层按 metadata.kind 过滤；`awaiting-guidance` 注明为投影态非新枚举。 |
| P0 | D004 §3.4.1/§3.5 | **B6**：pack 时刻修订为「会话首个 agent turn」；surfaces 在首次 pack 后可见，此前前端按无 surface 处理。 |
| P1 | D004 §3.5 + PLAN Task 2 | **B7**：「会话 payload」明确为 `GET …/plugin-load-receipt` 响应（或新增 thread 字段）；删除虚构的 `build_session_payload`；保留 manifest→receipt 兜底与旧会话缺省隐藏。 |
| P1 | D004 §3.4.4 | **A1**：补「第 5 步在全部制品复制与 init 完成后执行一次（plugins[] 需全量）」；**A4**：如采纳 temp-dir+rename 方案则设计不变，否则措辞放宽为「重 pack 收敛字节一致」。 |
| P2 | PLAN Task 6 / E14 | 补内置插件 profile 改造后的 digest/lock 迁移策略（重 seed 或显式声明旧库降级）。 |

### 4.2 改代码前置（任务二需排期的代码改造，仍属实现期前）

| 项 | 内容 |
|----|------|
| `plugins/ink-dream-story/.ink/workspace-init.json` | 新增含 `surfaces[]` 的 profile（E14），并接受 digest 变化；准备既有 DB 的 installation/lock digest 刷新路径。 |
| `frontend/src/router/story-workspace.tsx` | state router 扩展参数化匹配与 query 解析；`replaceWithCanonicalPath` 保留 query（C10）。 |
| Chat 消息过滤位 | 若采纳 D11/D13 的 chat_message 承载：`GET /threads/{id}/messages` 消费侧按 metadata.kind 过滤 guidance（前端改动，落点 `ChatView.tsx` 消息加载 :346 与 ChatPanel 渲染）。 |

### 4.3 留到实现期处理（设计无需改，PLAN 已覆盖或代码注释级）

- A1 物理映射位置（循环后执行）——PLAN Task 1 Step 6 伪码已正确，实现时照做。
- A2 未知键白名单警告——可选增强，实现期决定是否做。
- A4 temp-dir + rename 原子物理映射——实现期代码细节。
- A5 receipt `warnings` 键——纯新增，随 Task 1 落地。
- C8 的 D003 三栏/episodes 差距——既有设计债，不在本增量范围，不在任务二处理。

---

## 附：审计边界声明

- 本报告未执行任何代码、测试或数据库迁移；所有「兼容/冲突」判定基于静态阅读。
- `backend/tests/test_workspace_init.py`（16 个测试）等既有测试文件仅以文件名/命中情况核实存在与主题，未逐条核对断言；E15 对测试「不触礁」的判定基于其围绕 plugins/venv 的主题定位，任务二若需精确结论可补一轮测试断言精读。
- 审计中发现的 `backend/database.py` 全部内容仅为只读引用，未做修改。

# Dream 发起与 writer 生产链接通实施记录

> 日期：2026-08-04
> 范围：Dream 专用发起、服务端 Dream adapter、可信 run context、Dream Agent
> run/stage writer 链、同一 Dream Agent 单次确认 continuation，以及对应文档校准
> 设计依据：`design_005`、`design_006`、`design_007`、`story-workspace-prd.md`
> 术语依据：`docs/architecture/术语表.md`
> **放行证据**：U3 初始提交 `62e21d7`、整改提交 `4c85b96` 已由不同 reviewer
> 终审 PASS；终审最小复跑 48 passed、19 subtests passed。

## 1. 本轮目标与结论口径

本轮把既有 `.dream` 文件、页面读取和一次确认能力接到生产入口：

```text
Dream 专用发起
  → 服务端创建 Dream Agent / preflight / run
  → 服务端注入 Dream adapter 与可信 run context
  → Dream Agent 按 run → characters → scenes → storyboards 更新工作空间
  → Dream 页面渲染、用户修改并一次确认
  → 同一 Dream Agent 写入修改并继续后续执行
```

Dream Agent 是 Dream 四阶段的业务主体。技术实现复用隐藏 Deck-bound Agent thread 与
隐藏 `chat_message` 保存 source/confirmation 并维持 turn 连续性；Dream 页面不挂载
`ChatView`，该技术载体不属于 Chat 页面或 Chat 业务合同。

本轮没有执行归档操作，也没有新增归档、驳回、失败或人工重试业务设计。

## 2. Subagent-Driven / TDD 独立单元

| 单元 | 提交 | Red → Green 结果 | 独立评审 |
|---|---|---|---|
| U2a 服务端 Dream adapter pack seam | `bb1b0eb` | 覆盖服务端 adapter 合并、ready 校验、surface 与冻结边界 | 已通过前序独立评审 |
| U1 发起核心幂等恢复 | `2da2b41` | pending source 重放会重新调度；已 dispatched 不重复调度 | 已通过前序独立评审 |
| U4 Dream 专用发起前端 | `d09f43c` | Playwright Node seam 7/7；`npx tsc -b` 通过；改动文件 ESLint 0 error | 已通过独立复核 |
| U2b 可信 run context / writer continuation | `530f1ac` | 定向后端 207 passed、1 skipped、112 subtests；全量排除一个既有 reflection 用例后 903 passed、1 skipped、416 subtests | 已通过独立复核 |
| U3 REST / gateway 生产接线 | `62e21d7` + `4c85b96` | 初始目标测试 8 passed、4 subtests；整改后 API 16 passed/11 subtests、Dream 相关 83 passed/37 subtests，并覆盖 atomic claim、冻结 binding 重放、binding CAS 与 strict wire | **不同 reviewer 终审 PASS；48 passed、19 subtests** |
| D1 文档与术语收口 | 本提交 | `rg` 术语/状态守门、`git diff --check`、`git diff --word-diff` | 自检通过 |

`62e21d7` 是 U3 初始实现证据，`4c85b96` 是阻断项整改证据；二者与不同 reviewer
终审 PASS 共同构成放行证据。

## 3. 已接通的生产合同

### 3.1 Dream 专用发起

- 无 run 时 `StoryWorkspaceDreamPage` 渲染独立 `StoryWorkspaceDreamLaunch`；页面选择
  enabled Deck、输入目标，只提交 `deckId + goal + idempotencyKey`。
- `POST /api/story-workspace/dream-runs/start` 只接受 camelCase 的
  `deckId + goal + idempotencyKey`，不静默裁剪边界空白，并从认证依赖取得
  actor/workspace；浏览器不能提交 thread ID、run ID、来源五字段或 adapter package
  spec。
- gateway 先校验 Deck/binding，再创建隐藏 source、preflight/run 和可信
  `StoryWorkspaceDreamRunContext`；幂等请求复用同一 source/run。同键改 Deck/goal
  返回幂等冲突；active binding 漂移后重放仍使用 run 冻结 binding。
- 首 turn 派发使用 SQLite `BEGIN IMMEDIATE` 与 claim token；并发重放只有 claim
  获得者派发，fresh claim 不抢占，stale claim 可恢复，派发异常恢复 pending。
- 成功后前端导航到 `/story-workspace/dream?run=<workflowRunId>`。

### 3.2 服务端 Dream adapter 与静态层

- `pack_workspace_plugins()` 新增默认空的 `server_adapter_package_specs` seam；普通 turn
  不注入 adapter。
- Dream Agent turn 由服务端固定选择 `ink-dream-story@platform-builtin`；客户端、Deck
  输入和普通 Chat 都不能选择或伪造。
- adapter 与 Deck 插件一起经过 ready/digest/profile 校验；首次 pack 时物理映射
  `.dream` 静态启动层，冻结分支不后补、不重建。

### 3.3 可信 writer 链

- Dream Agent context 明确要求先调用 `write_dream_run`。
- canonical 人物文件完成后调用 `write_dream_stage(characters)`；场景完成后调用
  `write_dream_stage(scenes)`；canonical `storyboard.yaml` 完成后调用
  `write_dream_stage(storyboards)`。
- MCP 把请求 run ID 与服务端可信 context、run 所属 thread/actor/workspace 精确核对；
  `.dream/**` 只能经 Story Workspace MCP / `StoryWorkspaceDreamFileWriter` 更新。
- 普通 `Write`/`Edit`/`MultiEdit` 与 Bash 不能写 `.dream/**`；canonical `assets/**`、
  `stories/**`、`.dramaforge/**` 仍按插件权限写入。

### 3.4 一次确认 continuation

- 用户只提交一次 `StoryWorkspaceDreamConfirmationCommand`；服务端把它持久化为隐藏
  `chat_message`，后台协调器恢复同一 Dream Agent。
- continuation 重新装载同一可信 run context；Dream Agent 先写 canonical 修改与 stage
  revisions，再继续同一锁定插件流程。
- 页面刷新从持久 confirmation fact 恢复 continuing；不出现第二次确认。

### 3.5 文件与行号证据

- strict camelCase / 边界空白拒绝与可信 context 合同：
  `backend/story_workspace/contracts.py:190-255`；REST 201 alias 输出：
  `backend/routers/story_workspace.py:1152-1170`；
- 隐藏 Deck-bound source 的原子创建与 metadata：
  `backend/services/story_workspace/dream_launch_gateway.py:156-225`；核心
  source/preflight/run/context 编排：
  `backend/services/story_workspace/dream_launch_service.py:157-275`；
- 服务端 adapter spec 与 run → characters → scenes → storyboards 指令：
  `backend/services/story_workspace/dream_launch_gateway.py:109-113,661-673`；pack seam：
  `backend/services/claude_plugin/workspace_packer.py:175-180,247-252`；
- binding CAS、原子派发 claim 与冻结 binding 重放：
  `backend/services/story_workspace/dream_launch_gateway.py:575-658,723-860,898-1030`；
- 可信 context 内 writer 顺序：`backend/claude_agent/context_builder.py:435-459`；MCP
  精确核对 thread/run 并调用 writer：
  `backend/libs/claude_agent_kit/server/story_workspace_tool.py:170-255`；
- confirmation continuation 重新装载可信 context：
  `backend/services/story_workspace/dream_confirmation_service.py:489-653`；
- 前端 request 只有三字段、单 in-flight 与 canonical run 导航：
  `frontend/src/hooks/story-workspace/contracts.ts:112-123`、
  `frontend/src/hooks/story-workspace/useStoryWorkspaceDreamLaunch.ts:30-72`；无 run 渲染
  专用发起页：`frontend/src/pages/story-workspace/StoryWorkspaceDreamPage.tsx:273-275`。

## 4. 变更文件清单

### 4.1 后端与测试

| 路径 | 说明 |
|---|---|
| `backend/services/claude_plugin/workspace_packer.py` | 服务端 adapter refs 合并、校验与 pack seam |
| `backend/services/story_workspace/dream_launch_service.py` | 可信 source/preflight/run 编排与幂等 dispatch core |
| `backend/services/story_workspace/dream_launch_gateway.py` | 生产 source store、adapter provisioning、persistent dispatcher 与 gateway |
| `backend/routers/story_workspace.py` | `POST /dream-runs/start` REST 接线 |
| `backend/services/deck/builtin_plugin.py` | 内建 Dream adapter 制品定义/准备 |
| `backend/services/deck/story_workflow_gateway.py` | 路由层 actor/workspace 到 Dream launch gateway 桥接 |
| `backend/story_workspace/contracts.py` | launch command、accepted response、可信 run context canonical 合同 |
| `backend/claude_agent/context_builder.py` | 注入可信 Dream context 与 writer 顺序 |
| `backend/claude_agent/service.py` | Dream turn 选择 server adapter、传递可信 context |
| `backend/libs/claude_agent_kit/server/agent_runner.py` | Dream 文件工具边界与运行保护 |
| `backend/libs/claude_agent_kit/server/story_workspace_tool.py` | MCP 精确 run/thread/context 绑定 |
| `backend/services/deck/chat_context.py` | Dream turn 的 Deck context 解析 |
| `backend/services/story_workspace/dream_confirmation_service.py` | confirmation continuation 重新装载可信 Dream context |
| `backend/tests/test_workspace_init_surfaces.py` | 服务端 adapter pack、surface 与冻结测试 |
| `backend/tests/test_story_workspace_dream_launch.py` | 核心 launch 幂等/派发测试 |
| `backend/tests/test_story_workspace_dream_launch_api.py` | REST/gateway authority、幂等、并发与 wire 测试 |
| `backend/tests/test_claude_agent_context_builder.py` | Dream context / writer 指令测试 |
| `backend/tests/test_claude_agent_runner.py` | 普通文件工具 `.dream` 写保护测试 |
| `backend/tests/test_claude_agent_service.py` | Dream adapter/context service 接线测试 |
| `backend/tests/test_claude_agent_thread_factory.py` | continuation 的同 thread runtime 测试 |
| `backend/tests/test_deck_chat_context.py` | Dream Deck context 回归 |
| `backend/tests/test_story_workspace_dream_confirmation.py` | confirmation 可信 context continuation 测试 |
| `backend/tests/test_story_workspace_dream_mcp_tool.py` | MCP exact run/context 绑定测试 |

### 4.2 前端与测试

| 路径 | 说明 |
|---|---|
| `frontend/src/App.tsx` | 移除 Dream 对 Chat 视图注入依赖 |
| `frontend/src/api/storyWorkspaceApi.ts` | 专用 launch endpoint、201 解析与错误边界 |
| `frontend/src/hooks/story-workspace/contracts.ts` | 前端局部 launch request/accepted 合同 |
| `frontend/src/hooks/story-workspace/index.ts` | launch hook 公共导出 |
| `frontend/src/hooks/story-workspace/useStoryWorkspaceDreamLaunch.ts` | 幂等键保留、单 in-flight Promise 与 canonical run path |
| `frontend/src/hooks/story-workspace/__tests__/useStoryWorkspaceDreamLaunch.test.ts` | launch coordinator Node seam 测试 |
| `frontend/src/pages/story-workspace/StoryWorkspaceDreamLaunch.tsx` | 独立 Deck/goal Dream 发起页 |
| `frontend/src/pages/story-workspace/StoryWorkspaceDreamPage.tsx` | 无 run 时进入专用发起页 |
| `frontend/src/pages/story-workspace/StoryWorkspaceDreamPage.css` | 暖纸、轻纸面发起布局 |
| `frontend/src/pages/story-workspace/index.ts` | launch page 导出 |
| `frontend/src/pages/story-workspace/__tests__/StoryWorkspaceDreamLaunchLayout.test.ts` | 不挂 ChatView、生命周期与视觉 seam |
| `frontend/src/router/story-workspace.tsx` | Dream canonical route 接入专用页面 |

### 4.3 文档

| 路径 | 说明 |
|---|---|
| `docs/architecture/术语表.md` | 新增 canonical “Dream Agent”，校准 `.dream`、writer、确认与门禁主体 |
| `docs/design/story-workspace/design_005_dream-module-dataflow-and-sequence.md` | 保留旧基线并追加当前生产数据流/时序与 G1–G7 状态 |
| `docs/design/story-workspace/design_006_dream-protocol-dir-mapping.md` | 服务端 adapter、可信 context、writer 链与技术载体边界 |
| `docs/design/story-workspace/design_007_dream-business-module-interaction.md` | Dream Agent 四阶段业务时序与专用发起交互 |
| `docs/design/story-workspace/story-workspace-prd.md` | 生命周期、API、布局、验收与诚实边界校准 |
| `docs/design/story-workspace/2026-08-04-dream-launch-writer-integration-implementation-record.md` | 本轮提交、测试、文件与遗留记录 |

没有夹带其他工作线的 claude-agent subagent UI、`i18n.ts` 或 workspace sandbox 文件。

## 5. 测试、构建与评审证据

| 验证 | 结果 |
|---|---|
| U4 Playwright Node seams | **7 passed** |
| U4 `npx tsc -b` | **exit 0** |
| U4 改动文件 ESLint | **0 errors**；`App.tsx` 17 条既有 hooks warnings |
| U2b 定向后端 | **207 passed, 1 skipped, 112 subtests passed** |
| U2b 后端全量（排除一个与本专项无关的既有 reflection JSON quote 用例） | **903 passed, 1 skipped, 416 subtests passed** |
| U3 初始目标测试 | **8 passed, 4 subtests passed**；仅作初始实现证据，不作放行证据 |
| U3-F API | **16 passed, 11 subtests passed** |
| U3-F Dream 相关 | **83 passed, 37 subtests passed**；另 route 8、Deck 2、contracts 7+6 均通过 |
| `cd backend && ../.venv/bin/python -m pytest tests -q` | **921 passed, 1 skipped, 428 subtests passed**；仅一个既有 Reflections 引号解析测试失败 |
| U3-F 不同 reviewer 终审 | **PASS；最小复跑 48 passed, 19 subtests passed** |
| D1 `git diff --check` / 术语状态 `rg` / `git diff --word-diff` | **通过** |
| `claude plugin validate` | 不适用：本轮未修改 `plugins/**` 制品文件；服务端 adapter 由内建制品代码提供 |
| 真实浏览器验收 | **待主代理执行**；本记录不提前写 PASS |

未执行真实外部 Claude 服务端到端 turn；上述结论来自可重复的单元、契约、Node seam
与构建测试，不把 fake dispatcher 结果描述为真实外部运行。

## 6. 按设计实现 vs 诚实遗留

| 项目 | 状态 | 说明 |
|---|---|---|
| Dream 专用发起页 | 已实现 | 无 run 时选择 Deck/目标，不复用 ChatView |
| 服务端可信发起 | 已实现 | 客户端只交 strict camelCase 三字段；source/preflight/run/context 由服务端派生 |
| 服务端专用 Dream adapter | 已实现 | 普通 turn 默认不注入；Dream turn 首次 pack 前选择 |
| 同一 Dream Agent 连续性 | 已实现 | 隐藏 Agent thread/message 是技术载体，不改变 Dream 业务归属 |
| run → characters → scenes → storyboards writer 链 | 已实现 | adapter/context 指令 + MCP exact run binding + writer |
| 页面读取与一次确认 | 已实现 | actor-scoped REST、base revisions、唯一确认、同一 Dream Agent continuation |
| G3：Dream UI 发起到 preflight/run/首 turn | 已实现 | atomic claim、冻结 binding replay、binding CAS 与 strict wire 已完成 Red → Green 并通过终审 |
| G5：Dream 文件 projection | 已实现 | actor-scoped `dream-files` REST |
| G1：旧 `WorkflowRun.status` | 技术遗留 | create 后仍为 `queued`；不等于缺少生产 Dream Agent |
| G6：入口六态聚合 | 遗留且降级隐藏 | 服务端聚合端点仍缺位 |
| writer 主动 run-scoped SSE | 遗留，不影响正确性 | REST 轮询是真相源与刷新保证 |
| 丰富 Outline / 镜头结构字段 | 字段级占位 | 当前 stage items 仍是通用摘要结构 |
| 真实外部 Agent E2E | 未验证 | 不以 fake seam 替代真实外部服务验证 |
| 真实浏览器验收 | 待主代理执行 | D1 不提前把未执行的浏览器验收写为 PASS |
| 归档、驳回、失败、人工重试业务流程 | 本期不做 | 未增加相关业务状态、按钮或时序 |

## 7. 更新后的设计文档清单

1. `docs/architecture/术语表.md`；
2. `docs/design/story-workspace/design_005_dream-module-dataflow-and-sequence.md`；
3. `docs/design/story-workspace/design_006_dream-protocol-dir-mapping.md`；
4. `docs/design/story-workspace/design_007_dream-business-module-interaction.md`；
5. `docs/design/story-workspace/story-workspace-prd.md`；
6. `docs/design/story-workspace/2026-08-04-dream-launch-writer-integration-implementation-record.md`。

没有执行文档归档。

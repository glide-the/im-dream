# Dream 发起与 writer 生产链接通实施记录

> 日期：2026-08-04
> 范围：Dream 专用发起、服务端 Dream adapter、可信 run context、Dream Agent
> run/stage writer 链、同一 Dream Agent 单次确认 continuation，以及对应文档校准
> 设计依据：`design_005`、`design_006`、`design_007`、`story-workspace-prd.md`
> 术语依据：`docs/architecture/术语表.md`
> **放行证据**：U3 初始提交 `62e21d7`、整改提交 `4c85b96` 已由不同 reviewer
> 终审 PASS；终审最小复跑 48 passed、19 subtests passed。真实 DeepSeek 验收随后
> 发现并推动发起 terminal metadata、drama-forge preflight 兼容发布与 Dream Agent
> 可见文案加固，以及 confirmation SQLite claim/lease 四轮整改；最终独立 reviewer
> PASS，并由新 run 真实验证单次确认只有一个 continuation。对应提交与复核见 §2、
> 真实验收见 §6。

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
| U5 发起 terminal metadata | `e292467` | Red 复现 Agent 落整份 metadata 后 `dispatching` 未收敛；Green 由 claim owner 写回 `dispatched` 并清理 claim 字段 | 独立 reviewer PASS；17 passed、11 subtests |
| U6 drama-forge preflight 兼容发布 | `9831e41` + `c7fcbcd` + `7087036` | 初版发布三个消费方读取入口；两轮 reviewer 分别指出父目录 symlink/并发回滚与 TOCTOU；最终以目录句柄锚定、不覆盖发布和可重入部分进度修复 | 独立 reviewer PASS；34 passed、11 subtests；packer/init 36 passed、17 subtests |
| U7 Dream Agent 可见文案 | `b091695` | Red 证明 pending/continuing/completed 仍使用 Chat 模块主体旧称；Green 统一为“Dream Agent” | 独立 reviewer PASS；最终 Story Workspace Node seams 99 passed，`tsc` 与 scoped ESLint 通过 |
| U8 单次确认原子领取 | `a0cb5d6` + `bea9dbe` + `5497a25` + `2200d28` | Red：两个协调器会消费同一 pending message；三轮 reviewer 依次打回 lease snapshot/心跳退出、incoming kind 绕过、续租 deadline 事务前计算竞争；最终整改在 SQLite 写事务内采样 clock 并写 `now + duration` | **第四次独立 reviewer PASS**；focused 50 passed/16 subtests，事务延迟 + 双协调器 200/200，相关回归 183 passed/56 subtests |
| D1 文档与术语收口 | 本提交 | `rg` 术语/状态守门、`git diff --check`、`git diff --word-diff` | 自检通过 |

`62e21d7` 是 U3 初始实现证据，`4c85b96` 是阻断项整改证据；二者与不同 reviewer
终审 PASS 共同构成发起主链的初始放行证据。`9831e41`、`c7fcbcd` 是真实验收后
preflight 兼容发布的中间提交；安全边界以最终 `7087036` 为准。
`a0cb5d6` 只修改 confirmation service 与对应测试，未修改 `backend/database.py` 或新增
DDL；claim/lease 复用既有隐藏 message metadata。它是初版实现证据，不是最终放行
证据；`bea9dbe` 补齐续租与 Agent metadata 重存竞争、续租暂态异常后的恢复，并把
`backend/claude_agent/service.py` 对服务端预持久化 confirmation 的处理改为只校验
不可变 envelope/claim identity、不再用旧 lease snapshot 覆写数据库；但二次 reviewer
发现该路径仍由请求携带的 `metadata.kind` 分流，改/删 kind 可落入普通 Chat replace，
所以 `bea9dbe` 也不是最终放行证据。`5497a25` 改为每条 Agent user persistence 先查
数据库 authoritative existing row，并结合 raw kind 与 `dream_confirm_` 保留前缀分类；
权威隐藏行必须完整验证，incoming kind 被修改、删除或 metadata 为空时也不能绕过。
三次 reviewer 又在联合重复中复现 heartbeat 用例 1/22 失败：续租 deadline 在进入
executor/SQLite 事务前计算，延迟后提交时可能已经过期，第二协调器实际接管。因此
`5497a25` 仍不是最终放行证据。`2200d28` 将 heartbeat/defer/cancel 的 duration 交给
SQLite helper，在 `BEGIN IMMEDIATE` 获锁并校验 owner 后才采样 clock、写
`now + duration`；初始 claim 也使用相同事务内计时口径。

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
- drama-forge 上游 preflight 从消费方根目录读取 `plugin.json`、
  `.claude/docs/templates/project-init.md` 与 `.claude/hooks/hooks.json`。当 Dream surface
  与 `drama-forge@drama-studio` 同时存在时，packer 从隔离制品发布这三个兼容入口；
  它们只适配上游读取路径，不属于 `.dream/runtime`。
- 最终发布实现以工作区目录句柄锚定并逐级 `O_NOFOLLOW` 遍历父目录；完整内容经
  临时文件、`fsync`、不覆盖 hard link 就位。既有同字节文件幂等复用，冲突不覆盖；
  中途只完成部分入口时保留正确进度，下次 pack 可补齐；launch manifest 存在后只校验。
- 上述兼容发布不修改 `.dream/workspace.json` schema，也不改变静态启动层冻结。

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

> **2026-08-04 真实验收跟踪**：confirmation API 与同技术 thread continuation 已被
> 实际触发，但首次数据库核验发现一条 confirmation user message 对应两条 assistant
> continuation。`a0cb5d6` 已加入 SQLite 原子 claim + lease，`bea9dbe` 已修复首轮
> reviewer 指出的 lease snapshot 回退与心跳暂态异常退出；二次 reviewer 继续发现
> incoming kind 可绕过权威校验，`5497a25` 已改为按数据库 canonical row 分类守卫。
> 三次 reviewer 又复现续租 deadline 事务前计算竞争，`2200d28` 已改为在 SQLite 写事务
> 内采样 clock。第四次独立 reviewer 已 PASS；新 run
> `run_2cb652215c38423398544133ff1b38c1` 的真实 transcript 只有一次 confirmation
> envelope 与一次 Dream Agent continuation，单次确认生产链最终通过。

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
  `backend/services/claude_plugin/workspace_packer.py:458-467`；
- drama-forge preflight 三个兼容入口、目录句柄锚定发布与 frozen 校验：
  `backend/services/claude_plugin/workspace_packer.py:45-53,187-367,423-441,538-544`；
- binding CAS、原子派发 claim 与冻结 binding 重放：
  `backend/services/story_workspace/dream_launch_gateway.py:575-658,723-860,898-1030`；
- 可信 context 内 writer 顺序：`backend/claude_agent/context_builder.py:435-459`；MCP
  精确核对 thread/run 并调用 writer：
  `backend/libs/claude_agent_kit/server/story_workspace_tool.py:170-255`；
- confirmation continuation 重新装载可信 context：
  `backend/services/story_workspace/dream_confirmation_service.py:832-999`；原子 claim、
  租约扫描、协调器续租与 owner ack：`:328-408,623-829,1007-1289`；预持久化
  confirmation 按数据库权威行分类，只校验且不用旧 lease 覆写：`:519-621` 与
  `backend/claude_agent/service.py:1452-1516`；claim 期间幂等重放不重复派发：
  `dream_confirmation_service.py:1592-1663`；
- 前端 request 只有三字段、单 in-flight 与 canonical run 导航：
  `frontend/src/hooks/story-workspace/contracts.ts:112-123`、
  `frontend/src/hooks/story-workspace/useStoryWorkspaceDreamLaunch.ts:30-72`；无 run 渲染
  专用发起页：`frontend/src/pages/story-workspace/StoryWorkspaceDreamPage.tsx:273-275`。

## 4. 变更文件清单

### 4.1 后端与测试

| 路径 | 说明 |
|---|---|
| `backend/services/claude_plugin/workspace_packer.py` | 服务端 adapter refs 合并、校验与 pack seam；drama-forge 三个 preflight 兼容入口的目录句柄锚定发布与 frozen 校验 |
| `backend/services/story_workspace/dream_launch_service.py` | 可信 source/preflight/run 编排与幂等 dispatch core |
| `backend/services/story_workspace/dream_launch_gateway.py` | 生产 source store、adapter provisioning、persistent dispatcher 与 gateway |
| `backend/routers/story_workspace.py` | `POST /dream-runs/start` REST 接线 |
| `backend/services/deck/builtin_plugin.py` | 内建 Dream adapter 制品定义/准备 |
| `backend/services/deck/story_workflow_gateway.py` | 路由层 actor/workspace 到 Dream launch gateway 桥接 |
| `backend/story_workspace/contracts.py` | launch command、accepted response、可信 run context canonical 合同 |
| `backend/claude_agent/context_builder.py` | 注入可信 Dream context 与 writer 顺序 |
| `backend/claude_agent/service.py` | Dream turn 选择 server adapter、传递可信 context；预持久化 confirmation turn 只校验 envelope/claim，不用旧 metadata 覆写续租 |
| `backend/libs/claude_agent_kit/server/agent_runner.py` | Dream 文件工具边界与运行保护 |
| `backend/libs/claude_agent_kit/server/story_workspace_tool.py` | MCP 精确 run/thread/context 绑定 |
| `backend/services/deck/chat_context.py` | Dream turn 的 Deck context 解析 |
| `backend/services/story_workspace/dream_confirmation_service.py` | confirmation continuation 重新装载可信 Dream context；SQLite 原子 claim/lease、owner 续租与 ack、过期租约恢复 |
| `backend/tests/test_workspace_init_surfaces.py` | 服务端 adapter pack、surface、drama-forge 兼容发布、symlink/并发/部分进度与冻结测试 |
| `backend/tests/test_story_workspace_dream_launch.py` | 核心 launch 幂等/派发测试 |
| `backend/tests/test_story_workspace_dream_launch_api.py` | REST/gateway authority、幂等、并发与 wire 测试 |
| `backend/tests/test_claude_agent_context_builder.py` | Dream context / writer 指令测试 |
| `backend/tests/test_claude_agent_runner.py` | 普通文件工具 `.dream` 写保护测试 |
| `backend/tests/test_claude_agent_service.py` | Dream adapter/context service 接线测试 |
| `backend/tests/test_claude_agent_thread_factory.py` | continuation 的同 thread runtime 测试 |
| `backend/tests/test_deck_chat_context.py` | Dream Deck context 回归 |
| `backend/tests/test_story_workspace_dream_confirmation.py` | confirmation 可信 context continuation；双协调器/双连接原子领取、fresh/过期租约、幂等重放与 owner ack 测试 |
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
| `frontend/src/pages/story-workspace/dreamViewModel.ts` | pending/continuing/completed 可见文案统一为同一 Dream Agent |
| `frontend/src/pages/story-workspace/StoryWorkspaceExecutionPage.tsx` | 后续执行页统一 Dream Agent 可见文案 |
| `frontend/src/pages/story-workspace/index.ts` | launch page 导出 |
| `frontend/src/pages/story-workspace/__tests__/StoryWorkspaceDreamLaunchLayout.test.ts` | 不挂 ChatView、生命周期与视觉 seam |
| `frontend/src/pages/story-workspace/__tests__/StoryWorkspaceDreamViewModel.test.ts` | Dream Agent 可见文案 seam 回归 |
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
| U5 dispatch terminal metadata | **17 passed, 11 subtests passed**；独立 reviewer PASS |
| U6 packer 兼容发布目标套件 | **34 passed, 11 subtests passed**；最小安全集 9 passed、25 deselected、3 subtests；frozen 3 passed |
| U6 packer/init 回归 | **36 passed, 17 subtests passed**；独立 reviewer PASS |
| U7 Story Workspace Node seams | **99 passed**；独立 reviewer PASS |
| U7 `npx tsc -b` / scoped ESLint | **exit 0 / 0 errors** |
| U8 claim Red | **6 failed, 35 passed, 12 subtests passed**；复现双协调器正常运行重复续跑 |
| U8 claim 初版 Green focused | **41 passed, 12 subtests passed**，连续 5 次；首轮 reviewer 仍 REJECT |
| U8 confirmation 初版相关回归 | **174 passed, 51 subtests passed**；`py_compile` / `git diff --check` 通过；不替代 reviewer 阻断项 |
| U8 续租整改 Red | **4 failed, 40 passed, 12 subtests passed**；覆盖旧 lease snapshot 回退、缺失/伪造 claim 与心跳暂态异常 |
| U8 续租整改 Green focused | **44 passed, 12 subtests passed**，连续 5 次；heartbeat 单测连续 10 轮 |
| U8 续租整改相关回归 | **177 passed, 52 subtests passed**；二次独立 reviewer 仍 REJECT |
| U8 权威行守卫整改 Red | **4 failed, 46 passed, 13 subtests passed**；覆盖 incoming kind 修改/删除/空 metadata 绕过 |
| U8 权威行守卫整改 Green focused | **47 passed, 16 subtests passed**，连续 5 次；攻击组连续 10 轮 |
| U8 权威行守卫相关回归 | **180 passed, 56 subtests passed**；三次 reviewer 仍 REJECT，heartbeat 联合重复曾 1/22 失败并发生 contender 接管 |
| U8 事务内 lease 时间整改 Red | **3 failed, 47 passed, 16 subtests passed**；复现 executor/DB 延迟后刚续租即过期 |
| U8 事务内 lease 时间整改 Green | **50 passed, 16 subtests passed**，连续 5 次；关键双协调器组连续 50 轮 |
| U8 事务延迟 + 双协调器重复 | **200/200 passed**（连续 100 轮），无 flaky、无 hang |
| U8 最终相关回归 | **183 passed, 56 subtests passed**；第四次独立 reviewer PASS |
| `cd backend && .venv/bin/python -m pytest tests -q` | **946 passed, 1 skipped, 438 subtests passed**；仅一个既有 Reflections 引号解析测试失败 |
| U3-F 不同 reviewer 终审 | **PASS；最小复跑 48 passed, 19 subtests passed** |
| D1 `git diff --check` / 术语状态 `rg` / `git diff --word-diff` | **通过** |
| `claude plugin validate` | 不适用：本轮未修改 `plugins/**` 制品文件；服务端 adapter 由内建制品代码提供 |
| 真实浏览器：生成阶段 | **通过**；DeepSeek 实际完成 run、人物、场景、分镜 writer 调用并由页面渐进显示，详见 §6 |
| 最终前端 Playwright seams | **84 passed**；`npx tsc -b` exit 0；Story Workspace scoped ESLint exit 0 |
| 真实浏览器：一次确认 continuation | **通过**；单次 POST 202、单 confirmation envelope、单 Dream Agent continuation，hidden row 最终 dispatched，详见 §6.4 |

后端全量的唯一失败为既有 `tests/test_reflections_agent.py:136`：修复 JSON 时丢失开头
引号，与本专项无关。真实 DeepSeek 验收与 seam 测试分开记录，不用 fake dispatcher
替代外部 turn 证据。

## 6. 真实 DeepSeek 浏览器验收

### 6.1 触发条件

- Deck：`e843a442-94fa-4466-8c68-42a2d1e4b240`（页面显示“内省卡组”），绑定
  `drama-forge@drama-studio`；
- Dream 专用发起输入：`/drama-forge:drama-init`；
- Agent provider：项目 `.env` 中的 DeepSeek；
- run：`run_fbea7043099c45b1b7b252e8fc45fbaf`；
- 隐藏技术 thread：`61345e3f-daff-5e51-a8c1-76fc27c8a7cd`。

该验收从 Dream 专用页面发起，不挂载或操作 `ChatView`。服务端创建 run 与隐藏技术
thread 后，首个 Dream Agent turn 同时装载 Deck 插件、服务端 Dream adapter 与可信 run
context。launch source metadata 最终为 `dispatchStatus=dispatched`，且未残留 claim ID/
timestamp；该收敛由 `e292467` 修复。

### 6.2 生成阶段结果

DeepSeek Agent 按 adapter 约定实际调用 `write_dream_run`，随后在每类 canonical 文件
完整后依次调用 `write_dream_stage(characters)`、`write_dream_stage(scenes)`、
`write_dream_stage(storyboards)`。工作空间与页面结果：

| stage | canonical 结果 | stage 结果 | 页面证据 |
|---|---|---|---|
| characters | `assets/characters/` 下 5 个人物 Markdown | `stages/characters.json`，revision 1，5 items | `frontend/output/playwright/dream-writer-trigger/second-characters-r1.png` |
| scenes | 3 个场景 Markdown | `stages/scenes.json`，revision 1，3 items | `frontend/output/playwright/dream-writer-trigger/second-scenes-r1.png` |
| storyboards | `stories/ni-guang-zhi-ren/episodes/EP01/storyboard.yaml` | `stages/storyboards.json`，revision 1，1 item | `frontend/output/playwright/dream-writer-trigger/second-storyboards-r1.png` |

分镜页面显示 `EP01「第一天」——重生、撕毁合同、蝴蝶效应序幕`，40 shots、89.6 秒。
人物、场景、分镜均在同一 run 下按 revision 1 渐进出现，证明“生成 canonical 文件 →
调用 Dream writer → 页面渲染”的三阶段链路已经真实触发，而不是只通过 mock/seam。
发起初态截图为
`frontend/output/playwright/dream-writer-trigger/second-after-launch.png`。

### 6.3 确认 continuation 跟踪

点击“确认并继续”后，confirmation API 返回 202，且请求继续绑定同一 run 与同一隐藏
技术 thread。页面可见文案已由 `b091695` 统一为“同一 Dream Agent 正在继续”，截图为
`frontend/output/playwright/dream-writer-trigger/second-confirmation-continuing.png`。

首次数据库核验同时发现一条 confirmation user message 后落入两条 assistant
continuation，因此本节只确认 API、同 thread 绑定与页面 continuing 投影被触发；
这次旧 run 当时不能作为单次 continuation 通过证据，最终 Green 见 §6.4 的全新 run。

Red 证据不是前端重复提交：数据库只有一条 confirmation user message
`dream_confirm_b2cde79e37092b42fe81a143fa9047aab0f8c78c91dce79f150a951be688694a`；
同一 confirmation envelope 在该 thread 的 Claude JSONL transcript 第 94、101 行分别于
`15:57:20.876Z`、`15:57:42.780Z` 被接收，并在第 96、103 行分别于
`15:57:41.110Z`、`15:57:53.998Z` 完成。第二个 turn 在第一个完成后约 0.7 秒进入，
早于协调器最小 2 秒退避。两个协调器共用临时数据库的确定性复现输出为：

`backend/data/agent-workspace/61345e3f-daff-5e51-a8c1-76fc27c8a7cd/.claude-home/projects/-Users-dmeck-project-ink-dream-memory-backend-data-agent-workspace-61345e3f-daff-5e51-a8c1-76fc27c8a7cd/fc5df741-d0ac-45d1-8585-4a9c2ddcdcc3.jsonl:94`

```text
schedule_results True True
concurrent_consumptions 2
```

根因是旧实现只按协调器对象内 `_in_flight` 去重，两个消费者都能在数据库状态仍为
pending 时把同一 message 排入 thread；不是 Dream writer、DeepSeek 或页面轮询重复。

初版代码 Green 为 `a0cb5d6`：调用 Agent 前用 SQLite `BEGIN IMMEDIATE` 原子领取
`pending → dispatching`，写入 claim ID 与 epoch lease；fresh claim 不参与其他协调器
扫描，owner 在 turn 期间续租，租约过期后才允许一个协调器接管；只有 claim owner
能把已观察到完整终止帧的 turn ack 为 `dispatched`。相同幂等键在 `dispatching` 期间
返回既有 accepted fact，不安排第二个 turn。focused Green 连续 5 次均为
41 passed、12 subtests，相关回归为 174 passed、51 subtests。

首轮独立 reviewer 仍以 P1 打回：心跳只更新数据库而 dispatcher 仍携带首次 claim
metadata，Agent 重存隐藏 user message 可把已续租 lease 回退；单次续租暂态异常也会令
心跳永久退出。整改 `bea9dbe` 令服务端预持久化 confirmation turn 在 Agent 入口只校验
不可变 envelope 与 claim identity，不执行旧 snapshot 的 `INSERT OR REPLACE`；续租心跳
遇到单次暂态异常会继续尝试。整改 Red 为 4 failed/40 passed/12 subtests；Green focused
连续 5 次均为 44 passed/12 subtests，heartbeat 测试连续 10 轮，相关回归
177 passed/52 subtests。二次 reviewer 继续发现 incoming `metadata.kind` 可改/删后绕过
confirmation 权威校验并落入普通 Chat replace。最终整改必须先由数据库 canonical row/
message ID 判定预持久化 confirmation。`5497a25` 以 authoritative existing row、raw kind
与 `dream_confirm_` 保留前缀完成分类守卫；隐藏行必须完整验证，incoming kind 修改、
删除或 metadata 为空都不能进入普通 Chat replace。该整改 Red 为 4 failed/46 passed/
13 subtests；Green focused 连续 5 次均为 47 passed/16 subtests，攻击组连续 10 轮，
相关回归 180 passed/56 subtests。三次 reviewer 在联合重复中又观测 heartbeat 用例
1/22 失败：续租 deadline 在 executor/SQLite 写事务前计算，实际提交时已经过期，
`contender.reconcile_once()` 返回 1 并接管。最终修复必须在取得 SQLite 写事务后计算
deadline。`2200d28` 让 heartbeat/defer/cancel 只传 duration，在 `BEGIN IMMEDIATE`
获锁且 owner 校验后采样 clock 并写 `now + duration`；初始 claim 同样收敛。该整改 Red
为 3 failed/47 passed/16 subtests；Green focused 连续 5 次均为 50 passed/16 subtests，
关键双协调器组连续 50 轮，相关回归 183 passed/56 subtests。第四次独立 reviewer 已
PASS，并把事务延迟 heartbeat + 双协调器组连续提高到
100 轮、200/200 passed，无 flaky、无 hang。代码侧由 §6.4 的新 run transcript 完成
真实 Green；单元/回归计数没有被当作外部 Agent 验收替代品。

### 6.4 最终新 run 真实 Green

最终验收再次使用 Deck `e843a442-94fa-4466-8c68-42a2d1e4b240` 与命令
`/drama-forge:drama-init`，但创建全新的：

- run：`run_2cb652215c38423398544133ff1b38c1`；
- 隐藏技术 thread：`f9f9e1d9-ed20-57c6-a767-b903211c1c7d`；
- launch metadata：`dispatchStatus=dispatched`。

DeepSeek Dream Agent 再次真实完成 writer 链：

| stage | revision / 数量 | 页面内容与 source |
|---|---|---|
| characters | r1 / 4 | 江辰、周明远、苏晴雨、林海；截图 `frontend/output/playwright/dream-writer-trigger/final-characters-r1.png` |
| scenes | r1 / 3 | 天辰集团总裁办公室、滨海湾天台、雨夜街道 |
| storyboards | r1 / 1 | `EP01「睁眼」—47镜分镜`，88.5 秒；source `stories/rebirth-gate/episodes/EP01/storyboard.yaml`；截图 `frontend/output/playwright/dream-writer-trigger/final-storyboards-r1.png` |

发起初态截图为 `frontend/output/playwright/dream-writer-trigger/final-after-launch.png`。
三个页签均显示 r1；人物、场景和分镜仍由 `dream-files` REST 轮询渐进出现。

确认只点击一次，`POST dream-confirmation` 返回 202：

- message：`dream_confirm_cf33f584bf1f616627242e5b9e46dd5435c7f36901936c75dac7df0aa442cf3b`；
- request：`bd5cf129-31dc-4afa-8d28-5c7e95bf540e`；
- 稳定等待 30 秒后，该 thread 数据库计数为 user 2 / assistant 2：一条 launch source、
  一条 confirmation、一个首 turn assistant、一个 continuation assistant；
- transcript 中 confirmation envelope 只出现 1 次，同一 Dream Agent continuation 只执行
  1 次；没有第二个排队 turn；
- hidden confirmation row 最终 `dispatch_status=dispatched`，claim ID 与 lease 已清空，
  `dispatch_ack_claim_sha256=b81742010cb1d03882812b43b52693fd707e6d9d4b2d47524eec10979ae5d810`。

页面显示最终确认与“同一 Dream Agent 正在继续”，无旧 Chat 主体称谓、无 pageerror；
截图为
`frontend/output/playwright/dream-writer-trigger/final-confirmation-completed.png`，trace 为
`frontend/output/playwright/dream-writer-trigger/trace-final-success.zip`。验收使用的后端与
浏览器已关闭，用户原有 5173 Vite 保留。

### 6.5 诚实边界

- `WorkflowRun.status` 在本次生成完成后仍为 `queued`；stage 文件与 revisions 才是 Dream
  页面生产事实，旧状态聚合仍为 G1 技术遗留；
- writer events 请求当前返回 404；页面依靠 `dream-files` REST 轮询仍完整显示人物、
  场景、分镜三个 revision 1，主动 run-scoped SSE 仍为 G4 遗留；
- 浏览器未出现 page runtime error；控制台唯一已知请求错误为上述 writer events 404。

## 7. 按设计实现 vs 诚实遗留

| 项目 | 状态 | 说明 |
|---|---|---|
| Dream 专用发起页 | 已实现 | 无 run 时选择 Deck/目标，不复用 ChatView |
| 服务端可信发起 | 已实现 | 客户端只交 strict camelCase 三字段；source/preflight/run/context 由服务端派生 |
| 服务端专用 Dream adapter | 已实现 | 普通 turn 默认不注入；Dream turn 首次 pack 前选择 |
| 同一 Dream Agent 连续性 | 已实现并真实验证 | 隐藏 Agent thread/message 是技术载体，不改变 Dream 业务归属；SQLite claim、权威行守卫与事务内 lease 时间戳通过第四次 reviewer，新 run 只有一个 continuation |
| run → characters → scenes → storyboards writer 链 | 已实现 | adapter/context 指令 + MCP exact run binding + writer |
| 页面读取与一次确认 | 已实现并真实验证 | actor-scoped REST、唯一 confirmation fact、单 continuation 与页面继续态均通过真实 Green |
| G3：Dream UI 发起到 preflight/run/首 turn | 已实现 | atomic claim、冻结 binding replay、binding CAS 与 strict wire 已完成 Red → Green 并通过终审 |
| G5：Dream 文件 projection | 已实现 | actor-scoped `dream-files` REST |
| G1：旧 `WorkflowRun.status` | 技术遗留 | create 后仍为 `queued`；不等于缺少生产 Dream Agent |
| G6：入口六态聚合 | 遗留且降级隐藏 | 服务端聚合端点仍缺位 |
| writer 主动 run-scoped SSE | 遗留，不影响正确性 | REST 轮询是真相源与刷新保证 |
| 丰富 Outline / 镜头结构字段 | 字段级占位 | 当前 stage items 仍是通用摘要结构 |
| 真实外部 Agent E2E | 已验证 | DeepSeek 实际完成 run + 三个 stage writer + 单次 confirmation continuation |
| 真实浏览器验收 | 已通过 | 生成、渐进页面渲染、最终确认与同一 Dream Agent 继续均有截图/trace/DB/transcript 证据 |
| 归档、驳回、失败、人工重试业务流程 | 本期不做 | 未增加相关业务状态、按钮或时序 |

## 8. 更新后的设计文档清单

1. `docs/architecture/术语表.md`；
2. `docs/design/story-workspace/design_005_dream-module-dataflow-and-sequence.md`；
3. `docs/design/story-workspace/design_006_dream-protocol-dir-mapping.md`；
4. `docs/design/story-workspace/design_007_dream-business-module-interaction.md`；
5. `docs/design/story-workspace/story-workspace-prd.md`；
6. `docs/design/story-workspace/2026-08-04-dream-launch-writer-integration-implementation-record.md`。

没有执行文档归档。

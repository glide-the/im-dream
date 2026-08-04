# Dream 协议与业务交互任务三实施记录

> 日期：2026-08-04
> 范围：`.dream` 运行内容层、一次确认、同一 Chat Agent 后续执行、Dream 页面与执行协作页
> 设计依据：`design_006_dream-protocol-dir-mapping.md`、`design_007_dream-business-module-interaction.md`、`story-workspace-prd.md`
> 术语依据：`docs/architecture/术语表.md`

## 1. 结论

任务三已实现任务二确认的主链：

```text
Agent 产出 → 页面渲染 → 用户修改并一次确认 → 同一 Chat Agent 后续执行
```

运行期元信息写入 `.dream/runtime/runs/<run_id>/`，静态 `workspace.json` 保持 `dream-surface/v1` 和 pack 时刻冻结语义。Agent 不能用通用文件工具修改 `.dream`，只能使用受控 MCP 工具写 `run.json` 和三类 stage 文件。

Dream 后续执行页已替换旧五态/指导侧栏实现，改为：

1. Assets / Outline 索引与叙事主工作面；
2. 选中人物、场景或分镜后，在同一主工作面切换到聚焦上下文层；
3. 页面只展示工作空间文件与 revision 更新；
4. 不提供驳回、失败、重试、归档或第二次确认业务入口。

本次没有执行归档操作。

## 2. 独立提交

| 单元 | 提交 | 结果 |
|---|---|---|
| F1 Dream 本地草稿状态 | `91979eb`、`99d7464`、`4714a01` | 五个页面状态、逐 stage 到达、本地编辑、revision 冲突、一次确认命令 |
| U1 Dream 文件协议核心 | `cbb3a99`、`681ab16`、`003f334`、`223ac2a`、`881562a`、`cde9e85`、`2f2b5c4` | `run.json` / stage schema、actor/thread/source 校验、CAS、原子替换、持久性与并发保护 |
| U2 Dream 文件读取 API | `33641da`、`d518425`、`5bbf2eb` | actor-scoped GET、只读零创建、camelCase wire 响应、固定工作区根 |
| U3 一次确认与续跑 | `687b39d`、`c421410` | 隐藏消息审计、幂等、revision 双读、原 thread 排队续跑；修复 in-flight turn 锁竞争 |
| U4 受控 MCP 写工具 | `a2e026b` | 只开放 `write_dream_run` / `write_dream_stage`，身份与来源字段不可由插件伪造 |
| F2 文件读取 Hook | `18b44a3` | 严格解析、同 run SSE 失效、waiting/continuing 轮询、旧响应隔离 |
| F3 确认提交与 Chat 隐藏 | `f0f673b` | 单 in-flight Promise、202 解析、确认与 guidance 控制消息过滤 |
| U5 插件文件同步说明 | `6cfe62d` | 明确人物、场景、分镜各自写入时点及确认后的写回顺序 |
| F4 Dream 修改与确认页 | `8ee0b06` | 三模块 manuscript、右侧编辑器、冲突选择、唯一确认条、跳转后续执行 |
| F5 后续执行协作页 | `6f16b01` | Assets / Outline、主工作面、聚焦层、revision 更新流；删除旧常驻指导与五态 UI |
| F6 入口旧分支收敛 | `582668d` | 只显示四个生命周期桥接入口；旧聚合分支与替代尝试保持隐藏 |
| B1 持久确认与派发恢复 | `15f3c4a` | GET 投影确认事实、同 actor+run 单次约束、pending/dispatched 审计、同键恢复派发、多 workspace 精确鉴权 |
| F7 持久生命周期与路由隔离 | `1c4d3cc` | 刷新后恢复只读继续态；execution 以确认事实门禁；run 深链不挂旧审阅页；editing 轮询 |
| B2 `.dream` Bash 写保护加固 | `7f59458` | 阻止 find delete/exec、env wrapper、glob/brace、相对/绝对/symlink 绕过，保留确定只读命令 |
| B3 MCP 合同唯一 owner | `58ae0d6` | Agent-visible Dream tool 输入模型迁入 canonical contracts，tool 层只导入/校验 |
| B4 刷新合同如实说明 | `8cb0e46` | REST 作为真相源；5 秒轮询保证；匹配 run 的兼容事件仅作加速；writer 主动 SSE 明确遗留 |
| B5 MCP run workspace 精确解析 | `90608e8` | 通过 run_id + owner JOIN 使用 run.workspace_id；同 actor 多 workspace 正常，跨 actor/未知 run fail-closed |
| B6 后台确认协调 | `69ab6c1` | pending 隐藏消息作为 durable work item；启动/周期协调、in-flight 去重、Agent stream 成功消费后 ack、异常/取消/重启自动恢复 |
| B8 Dream workspace Bash 隔离 | `900ef4a` | 存在 `.dream` 时 Bash 默认只读；动态代码、预写脚本、伪装 executable 与 PATH 注入均 hard deny |
| F8 前端公共符号命名 | `b1d65b2` | Task3 公共导出统一 `StoryWorkspace` / `storyWorkspace` / `STORY_WORKSPACE` 前缀；React hooks 保持 `useStoryWorkspace*` |
| B9 后端公共符号命名 | `14da100` | Task3 公共 module 符号统一 `StoryWorkspace` / `story_workspace_` / `STORY_WORKSPACE_` 前缀；静态守门禁止旧 alias |
| B10 确认成功判定与退避 | `912ae87` | 仅 `message-final` + 非 error 终止帧可 ack；取消/截断保持 pending；逐 message ID 指数退避，成功清理 |
| F9 Dream 上下文状态隔离 | `90bada3` | Dream 路由固定投影 `story_workspace_dream` / “Dream 协作中”，不透出旧 run 驳回、失败、取消状态或动作 |
| B11 后端边界命名补全 | `ed79b1d` | Dream router/gateway 新公开函数统一前缀；AST seam 扫描全部 Dream route handler 与 Task3 gateway 函数 |
| F10 执行页两层深度与视觉约束 | `887f91f` | overview 单一工作面；focus 全层替换；移除固定 rail/grid；执行页 CSS 只保留一条虚线主边界 |

任务二设计文档提交为 `d5ab609`，不计入上述任务三代码单元。

## 3. TDD 与评审执行

### 3.1 Red → Green

各单元先由失败测试锁定合同，再实现通过。主要证据：

- 文件协议：`backend/tests/test_story_workspace_dream_files.py:449` 起覆盖首次写、重放、revision 冲突；`:560` 起覆盖路径逃逸；`:710` 起覆盖写失败保持旧文件；`:759` 与 `:790` 覆盖线程/进程并发；`:1070` 起覆盖持久性不确定窗口；
- GET API：`backend/tests/test_story_workspace_dream_api.py:187`、`:286`、`:342`、`:420` 覆盖 alias、零创建、actor 传递和数据库异常；
- MCP：`backend/tests/test_story_workspace_dream_mcp_tool.py:175`、`:204`、`:259`、`:282`、`:305` 覆盖不可伪造参数、真实写入、跨 actor/thread、CAS 与禁止猜 run；
- 一次确认：`backend/tests/test_story_workspace_dream_confirmation.py:313`、`:414`、`:421`、`:453`、`:485`、`:509`、`:533` 覆盖审计、身份、revision、幂等、双读、回滚与并发；
- 持久确认与恢复：`backend/tests/test_story_workspace_dream_confirmation.py:291-309`、`:479-558`、`:788-928` 覆盖确认事实投影、同 actor+run 单次约束、pending 重放与 dispatched 审计；`backend/tests/test_story_workspace_dream_api.py:602-731` 覆盖 multi-workspace 和刷新后禁用确认；
- MCP owner 与 multi-workspace：`backend/tests/test_story_workspace_dream_mcp_tool.py:211-263`、`:321-405` 覆盖 canonical 合同唯一归属和 run-owned workspace；
- Bash 写保护：`backend/tests/test_claude_agent_runner.py:1047-1141` 覆盖 find/env/glob/brace、相对/绝对/symlink 绕过及只读放行；
- 后台确认协调：`backend/tests/test_story_workspace_dream_confirmation.py:902-955` 覆盖逐 message ID 指数退避和成功清理；`:1092-1178` 覆盖 `message-final` + 非 error 终止帧成功、stop-only 取消与截断不 ack；其余用例覆盖启动/停止、周期扫描、in-flight 去重、进程重启、legacy metadata 和 run/thread/actor/workspace authority；
- Dream workspace Bash 隔离：`backend/tests/test_claude_agent_runner.py` 追加动态 `chr(46)` 路径、预写脚本、basename executable 伪装、PATH 注入与无 Dream surface 回归；
- 前端状态：`frontend/src/components/story-workspace/__tests__/StoryWorkspaceDreamState.test.ts:121` 到 `:550` 覆盖五态、三 stage、不可变草稿、冲突合并和防重复确认；
- 读取 Hook：`frontend/src/hooks/story-workspace/__tests__/useStoryWorkspaceDreamFiles.test.ts:79` 到 `:170` 覆盖严格解析、认证、轮询、SSE 失效与旧响应隔离；
- 页面视图模型：`frontend/src/pages/story-workspace/__tests__/StoryWorkspaceDreamViewModel.test.ts:48` 与 `frontend/src/pages/story-workspace/__tests__/StoryWorkspaceExecutionViewModel.test.ts:68` 覆盖可编辑字段、Assets / Outline、聚焦上下条和无审批状态模型；
- 持久前端生命周期与路由：`StoryWorkspaceDreamViewModel.test.ts:70-112`、`StoryWorkspaceExecutionViewModel.test.ts:99-107`、`frontend/src/router/__tests__/storyWorkspacePath.test.ts:49-77` 覆盖刷新只读继续态、确认事实门禁、run stage 深链与旧审阅页隔离；
- 公共符号命名 seam：前端静态检查 Task3 public exports 的 `StoryWorkspace` / `storyWorkspace` / `STORY_WORKSPACE` 前缀并禁止旧 alias；后端 `test_story_workspace_public_symbols.py:46-116` 以 AST 扫描 Dream 服务、MCP、router、gateway 与 lifecycle 边界；
- Dream 上下文隔离：`frontend/src/router/__tests__/storyWorkspaceDreamContext.test.ts:23-43` 覆盖 rejected/failed/cancelled 底层状态一律投影为“Dream 协作中”，并验证非 Dream 旧标签不回归；
- 执行页布局：`frontend/src/pages/story-workspace/__tests__/StoryWorkspaceExecutionPageLayout.test.ts:18-42` 以页面级结构 seam 覆盖 overview 无固定 rail/grid、focus 全层替换且无 tab/index、CSS 仅一条 `dashed`；
- 入口收敛：`frontend/src/components/story-workspace/__tests__/StoryWorkspaceSurfaceLinkButton.test.tsx:45`、`:91` 覆盖四个可显示入口及旧分支隐藏。

已保存的 Red 证据包括：缺少实现模块、缺少导出、旧 label table 仍含六态、旧聚合分支仍渲染等失败；Green 后均由对应单元测试和全量回归覆盖。

### 3.2 Subagent-Driven 与双阶段评审

- U1/U2 的实现与独立复核已完成；
- U3 首轮独立规格评审发现“运行中的原 thread 被 lifecycle 预检误判为 already running”，修复提交 `c421410` 改为让续跑任务在同一 thread lock 后排队；
- U4、F2～F6 与插件单元实施期间，子代理调用曾被平台使用额度阻断，因此这些单元由主代理按同一 Red/Green/独立提交纪律完成；没有把主代理自检冒充独立评审；
- 任务三首轮最终规格评审结论为 **FAIL**：发现确认事实未持久投影、Dream run 路由仍挂旧审阅页、执行页沿用旧 run status 门禁、派发 false 无恢复路径、多 workspace 误取默认 workspace；
- 首轮最终质量评审结论为 **FAIL**：另发现 Bash 写保护可被 find/env/glob 绕过，以及 Agent-visible MCP 输入模型不在 canonical contracts；
- B1～B5 与 F7 分别由子代理执行 Red/Green 并独立提交；
- 第二轮规格复审仍为 **FAIL**：精确同键重放不是产品可达的自动恢复，且 create_task 后即记 dispatched 不代表 Agent 已消费；
- 第二轮质量复审仍为 **FAIL**：另发现动态代码/预写脚本可绕过 Bash 词法保护，以及 Task3 公共符号未完全满足 DEC-004；
- 第三轮质量复审仍为 **FAIL**：发现 cancel 的 `finishReason="stop"` 会被误认成功、pending 每 2 秒重投缺少逐消息退避，以及 router/gateway 的新增公开符号不在静态命名守门范围；
- 第三轮规格复审仍为 **FAIL**：发现 Dream 路由把底层 `WorkflowRun.status` 原样传入上下文栏，可能显示“已驳回/运行失败/已取消”；
- B10 用 `message-final` + 终止帧双条件和逐消息退避修复消费确认，F9 固定 Dream 上下文投影，B11 补齐 router/gateway 命名及 AST 扫描；
- 第四轮规格复审仍为 **FAIL**：发现执行页仍是固定 rail + main 双栏、执行页 CSS 同时有四处虚线、PRD 运行层路径漏写 run 目录、实施记录评审未闭环且变更清单使用通配/组合路径；
- F10 把 overview 收敛为单一工作面、focus 改为全层替换并只保留一条虚线主边界；同时修正 PRD 路径并按 `git diff --name-status d5ab609..HEAD` 逐路径重写变更清单；
- F10 后的独立规格终审由只读代理 `post_fix_final_spec_review` 执行，结论为 **PASS**：逐项确认 overview/focus 全层互斥、单虚线、PRD run-scoped 路径、逐路径清单，以及四阶段、插件 stage 写入、一次确认、静态冻结和遗留边界；
- F10 后的独立质量终审由只读代理 `task3_quality_review` 执行，结论为 **PASS**：复核 F10 结构/CSS/截图，同时确认 B10/B11/F9、安全、并发、持久恢复、合同 owner 与 `backend/database.py` 零 diff 未回归；
- 两名终审代理均未修改文件。最终验证证据为后端 876 passed、前端 92 passed、构建 2668 modules、改动文件 ESLint、插件验证和 `git diff --check` 全部通过。

这是对早期“每个实现单元一个子代理”的明确执行偏差；首轮 FAIL、整改提交与最终只读复审均如实记录，不把主代理自检冒充独立评审。

## 4. 实现证据

### 4.1 合同与运行内容层

- 后端唯一合同 owner：`backend/story_workspace/contracts.py:106-539`；其中 Agent-visible MCP 输入合同在 `:190-238`，REST 确认事实在 `:418-461`；
- `run.json` 与 stage 写入口：`backend/services/story_workspace/dream_file_service.py:1163-1320`；
- reader 与聚合投影：`backend/services/story_workspace/dream_file_service.py:1382-1578`；
- 临时文件 `fsync`、原子替换、目录 `fsync` 与可见 revision 检查：同文件 `:811`、`:930-1040`；
- `backend/database.py` 无改动、无本期 DDL。

### 4.2 REST 与一次确认

- GET：`backend/routers/story_workspace.py:1191-1208` 的 `story_workspace_get_workflow_run_dream_files`；响应包含持久 `confirmationAccepted` / `confirmationDispatched`，已确认时 `canConfirm=false`；
- POST 一次确认：`backend/routers/story_workspace.py:1211-1238` 的 `story_workspace_submit_workflow_run_dream_confirmation`；
- 隐藏命令明确“先写 canonical 文件与 stage revision，再继续同一插件且不再次确认”：`backend/services/story_workspace/dream_confirmation_service.py:135-152`；
- 同一 thread 排队续跑与 `message-final` + 非 error 终止帧消费判定：`backend/services/story_workspace/dream_confirmation_service.py:487-581` 的 `story_workspace_build_dream_confirmation_turn_dispatcher`；
- actor/thread、幂等指纹、revision 双读、actor+run 单次约束与 SQLite 原子插入：同文件 `:732-1008` 的 `StoryWorkspaceDreamConfirmationService.submit_confirmation`；
- pending/dispatched 持久审计、authority 校验与启动/周期协调：同文件 `:288-484`、`:584-748`；其中 `:649-707` 为 in-flight 与逐消息指数退避，`:709-741` 为消费后 ack；生命周期接线在 `backend/server.py:870-952`；
- GET/POST 按 run 精确解析所属 workspace：`backend/services/deck/story_workflow_gateway.py:169-198`、`:645-864`。

### 4.3 受控 Agent 写入

- MCP 只暴露两个工具；Agent-visible 输入合同唯一归 `backend/story_workspace/contracts.py:190-238`，tool 层在 `backend/libs/claude_agent_kit/server/story_workspace_tool.py:29-68` 只导入、生成 schema 与校验；
- run、owner、thread、五字段由 host/数据库解析；同一 actor 多 workspace 时按 run 精确取 `run.workspace_id`：`story_workspace_tool.py:137-177`；
- 通用 Write/Edit/MultiEdit 不能写 `.dream`；存在 Dream surface 时 Bash 只允许确定只读白名单，覆盖动态代码/脚本、find actions、env/PATH、glob/brace、绝对/相对与 symlink 绕过：`backend/libs/claude_agent_kit/server/agent_runner.py:588-773`；
- MCP stdio 注入当前 thread/actor：同文件 `:1110-1123`、`:2318`。

### 4.4 插件何时更新 `.dream`

`plugins/ink-dream-story/references/dream-file-sync.md` 给出插件实际执行顺序：

- `:24-38`：host-bound Dream turn 开始先写 `run.json`；
- `:40-50`：人物 canonical 文件全部完成后写 `characters` stage；
- `:52-59`：场景 canonical 文件完成后写 `scenes` stage；
- `:61-73`：canonical `storyboard.yaml` 完成后写 `storyboards` stage，并明确上游 drama-forge 自身不写 `.dream`；
- `:75-90`：收到隐藏确认后先写用户修改的 canonical 文件，再 CAS 更新受影响 stage，然后在同一 Chat thread 继续。

插件 Skill 在 `plugins/ink-dream-story/skills/dream-story-workflow/SKILL.md:11-32` 把上述顺序设为唯一生命周期，并禁止逐项审批、驳回、重试、归档和再次确认。

### 4.5 前端四阶段

- Dream 纯状态与一次确认命令：`frontend/src/components/story-workspace/dreamState.ts:322-625`；
- GET 严格解析、waiting/editing/continuing 至少 5 秒轮询和匹配 run 的兼容事件失效：`frontend/src/hooks/story-workspace/useStoryWorkspaceDreamFiles.ts:224-241`、`:347-361`；
- 确认单 in-flight 请求：`frontend/src/hooks/story-workspace/useStoryWorkspaceDreamConfirmation.ts:118-159`；
- 三模块页面、唯一确认条与刷新后的持久只读继续态：`frontend/src/pages/story-workspace/dreamViewModel.ts:72-93`、`frontend/src/pages/story-workspace/StoryWorkspaceDreamPage.tsx:114-135`、`:491-505`；
- Assets / Outline 与聚焦层：`frontend/src/pages/story-workspace/StoryWorkspaceExecutionPage.tsx:212-358`；overview 与 focus 由条件分支全层替换，结构守门见 `StoryWorkspaceExecutionPageLayout.test.ts:18-42`；
- 后续执行纯文件视图模型：`frontend/src/pages/story-workspace/executionViewModel.ts:64-128`；
- execution 访问门禁只认持久确认事实：`frontend/src/pages/story-workspace/executionViewModel.ts:48-52`；
- 旧聚合分支隐藏：`frontend/src/components/story-workspace/surfaceLink.ts:43-101`；Dream/run-aware 路由隔离旧审阅页：`frontend/src/router/storyWorkspacePath.ts:160-178`、`frontend/src/router/story-workspace.tsx:203-285`；Dream 上下文固定投影在 `frontend/src/router/storyWorkspaceDreamContext.ts:8-27`，标签在 `frontend/src/components/story-workspace/workflow/storyWorkspaceWorkflowContext.ts:7-28`。

## 5. 变更文件清单

### 5.1 后端

| 状态 | 路径 | 说明 |
|---|---|---|
| 修改 | `backend/claude_agent/service.py` | 隐藏确认消息与 Agent stream 终止帧衔接 |
| 修改 | `backend/claude_agent/thread_pool.py` | 同 thread 续跑排队与锁语义 |
| 修改 | `backend/libs/claude_agent_kit/server/agent_runner.py` | MCP 注入及 Dream workspace 通用文件/Bash 写保护 |
| 新增 | `backend/libs/claude_agent_kit/server/story_workspace_mcp_server.py` | Dream MCP server tool list/call 边界 |
| 新增 | `backend/libs/claude_agent_kit/server/story_workspace_mcp_stdio.py` | Dream MCP stdio 入口 |
| 新增 | `backend/libs/claude_agent_kit/server/story_workspace_tool.py` | 两个受控写工具及 host 身份解析 |
| 修改 | `backend/routers/story_workspace.py` | actor-scoped GET dream-files 与 POST dream-confirmation |
| 修改 | `backend/server.py` | 后台确认协调器 startup/shutdown 生命周期 |
| 修改 | `backend/services/claude_plugin/workspace_init.py` | 静态 README 写边界及 REST 轮询/兼容事件说明 |
| 修改 | `backend/services/deck/story_workflow_gateway.py` | run-owned workspace 的读取/确认编排 |
| 新增 | `backend/services/story_workspace/dream_confirmation_service.py` | 单次确认、pending work item、双帧成功判定、恢复与退避 |
| 新增 | `backend/services/story_workspace/dream_file_service.py` | Dream reader/writer、CAS、原子替换与安全边界 |
| 修改 | `backend/story_workspace/contracts.py` | Dream 存储、wire、确认与 MCP 输入合同唯一 owner |
| 修改 | `backend/tests/test_claude_agent_runner.py` | `.dream` 通用写保护及非 Dream 回归 |
| 修改 | `backend/tests/test_claude_agent_service.py` | 隐藏消息与 Agent stream 回归 |
| 修改 | `backend/tests/test_claude_agent_thread_factory.py` | 同 thread 排队续跑回归 |
| 新增 | `backend/tests/test_ink_dream_story_skill.py` | 插件 Skill 与文件同步约束测试 |
| 修改 | `backend/tests/test_server_claude_agent.py` | 协调器生命周期接线测试 |
| 新增 | `backend/tests/test_story_workspace_dream_api.py` | Dream GET/POST、actor 与多 workspace API 测试 |
| 新增 | `backend/tests/test_story_workspace_dream_confirmation.py` | 单次确认、持久恢复、双帧判定与退避测试 |
| 新增 | `backend/tests/test_story_workspace_dream_files.py` | schema、CAS、并发、持久性与路径测试 |
| 新增 | `backend/tests/test_story_workspace_dream_mcp_tool.py` | MCP 合同、身份、run workspace 与写入测试 |
| 新增 | `backend/tests/test_story_workspace_public_symbols.py` | DEC-004 后端公共符号 AST 守门 |
| 修改 | `backend/tests/test_workspace_init_surfaces.py` | Dream 静态 README 与运行层说明测试 |

### 5.2 前端

| 状态 | 路径 | 说明 |
|---|---|---|
| 删除 | `frontend/src/components/story-workspace/StoryWorkspaceExecutionAssetPanel.tsx` | 移除旧执行资产卡片分支 |
| 删除 | `frontend/src/components/story-workspace/StoryWorkspaceExecutionProgressTable.tsx` | 移除旧五态进度表 |
| 删除 | `frontend/src/components/story-workspace/StoryWorkspaceGuidanceSidebar.tsx` | 移除 Dream 执行页常驻指导栏 |
| 修改 | `frontend/src/components/story-workspace/StoryWorkspaceSurfaceLinkButton.tsx` | 四个生命周期桥接入口 |
| 新增 | `frontend/src/components/story-workspace/__tests__/StoryWorkspaceDreamState.test.ts` | 五态、草稿、冲突与一次确认纯 seam 测试 |
| 新增 | `frontend/src/components/story-workspace/__tests__/StoryWorkspacePublicExports.test.ts` | DEC-004 前端公共导出守门 |
| 修改 | `frontend/src/components/story-workspace/__tests__/StoryWorkspaceSurfaceLinkButton.test.tsx` | 入口显示/隐藏回归 |
| 新增 | `frontend/src/components/story-workspace/dreamState.ts` | Dream 五态、本地草稿与 revision 冲突状态机 |
| 删除 | `frontend/src/components/story-workspace/executionState.ts` | 删除旧执行审批/失败状态 seam |
| 修改 | `frontend/src/components/story-workspace/index.ts` | Story Workspace 公共导出收敛 |
| 修改 | `frontend/src/components/story-workspace/layout/StoryWorkspaceLayout.css` | Dream 页面主区域布局适配 |
| 修改 | `frontend/src/components/story-workspace/surfaceLink.ts` | 四阶段入口与旧分支隐藏规则 |
| 修改 | `frontend/src/components/story-workspace/workflow/WorkflowContextBar.tsx` | 支持状态无关的 Dream 协作上下文 |
| 新增 | `frontend/src/components/story-workspace/workflow/storyWorkspaceWorkflowContext.ts` | Dream/非 Dream 上下文标签纯 seam |
| 新增 | `frontend/src/hooks/story-workspace/__tests__/useStoryWorkspaceDreamConfirmation.test.ts` | 一次确认、202 合同与 Chat 隐藏测试 |
| 新增 | `frontend/src/hooks/story-workspace/__tests__/useStoryWorkspaceDreamFiles.test.ts` | 严格解析、轮询、事件与旧响应隔离测试 |
| 修改 | `frontend/src/hooks/story-workspace/contracts.ts` | 前端局部 Dream wire 合同唯一 owner |
| 修改 | `frontend/src/hooks/story-workspace/index.ts` | Dream hooks 公共导出 |
| 新增 | `frontend/src/hooks/story-workspace/useStoryWorkspaceDreamConfirmation.ts` | 一次确认请求与 in-flight 去重 |
| 新增 | `frontend/src/hooks/story-workspace/useStoryWorkspaceDreamFiles.ts` | actor-scoped 读取、轮询与兼容事件失效 |
| 修改 | `frontend/src/lib/__tests__/story-workspace-guidance.test.ts` | Dream 确认消息隐藏回归 |
| 修改 | `frontend/src/lib/story-workspace-guidance.ts` | Chat 控制消息统一过滤 |
| 新增 | `frontend/src/pages/story-workspace/StoryWorkspaceDreamPage.css` | Dream 修改页暖纸视觉与三栏骨架 |
| 修改 | `frontend/src/pages/story-workspace/StoryWorkspaceDreamPage.tsx` | 三 stage 修改页与唯一确认条 |
| 新增 | `frontend/src/pages/story-workspace/StoryWorkspaceExecutionPage.css` | Assets/Outline 单层工作面与全宽聚焦层视觉 |
| 修改 | `frontend/src/pages/story-workspace/StoryWorkspaceExecutionPage.tsx` | 后续执行索引、工作面与聚焦深度切换 |
| 新增 | `frontend/src/pages/story-workspace/__tests__/StoryWorkspaceDreamViewModel.test.ts` | Dream REST 投影与持久生命周期测试 |
| 删除 | `frontend/src/pages/story-workspace/__tests__/StoryWorkspaceExecutionPage.test.tsx` | 删除旧执行页五态/指导 UI 测试 |
| 新增 | `frontend/src/pages/story-workspace/__tests__/StoryWorkspaceExecutionPageLayout.test.ts` | overview/focus 深度切换、无固定 rail 与单虚线守门 |
| 新增 | `frontend/src/pages/story-workspace/__tests__/StoryWorkspaceExecutionViewModel.test.ts` | Assets/Outline、聚焦邻接与门禁测试 |
| 新增 | `frontend/src/pages/story-workspace/dreamViewModel.ts` | Dream REST 到本地字段映射 |
| 新增 | `frontend/src/pages/story-workspace/executionViewModel.ts` | Dream 文件到执行工作面投影 |
| 新增 | `frontend/src/router/__tests__/storyWorkspaceDreamContext.test.ts` | Dream 上下文状态隔离测试 |
| 修改 | `frontend/src/router/__tests__/storyWorkspacePath.test.ts` | run stage 深链、execution 与旧审阅隔离测试 |
| 修改 | `frontend/src/router/story-workspace.tsx` | Dream/run-aware 路由、执行页与固定协作上下文接线 |
| 新增 | `frontend/src/router/storyWorkspaceDreamContext.ts` | 底层 run status 到 Dream 协作态的安全投影 |
| 修改 | `frontend/src/router/storyWorkspacePath.ts` | Dream stage/execution 路径解析与旧审阅隔离 |

### 5.3 插件与文档

| 状态 | 路径 | 说明 |
|---|---|---|
| 修改 | `plugins/ink-dream-story/.claude-plugin/plugin.json` | 插件制品描述同步 |
| 新增 | `plugins/ink-dream-story/references/dream-file-sync.md` | run/人物/场景/分镜/确认后的精确写入顺序 |
| 修改 | `plugins/ink-dream-story/skills/dream-story-workflow/SKILL.md` | 四阶段 Agent 工作流规则 |
| 修改 | `docs/architecture/术语表.md` | 任务三状态、确认协调与 Dream 上下文术语 |
| 修改 | `docs/design/story-workspace/design_006_dream-protocol-dir-mapping.md` | 协议实现状态、轮询、持久确认与退避语义 |
| 修改 | `docs/design/story-workspace/design_007_dream-business-module-interaction.md` | 四阶段实现状态、业务时序与布局边界 |
| 修改 | `docs/design/story-workspace/story-workspace-prd.md` | 生命周期、运行路径、布局验收与诚实边界 |
| 新增 | `docs/design/story-workspace/2026-08-04-dream-protocol-task3-implementation-record.md` | 任务三提交、证据、评审、验证与遗留 |

未夹带 `install_service.py`、`PluginReceiptBadge.tsx`、`i18n.ts`、`test_install_service_reinstall.py` 等其他工作线文件。

## 6. 验证结果

| 验证 | 结果 |
|---|---|
| `cd backend && ../.venv/bin/python -m pytest -q tests` | **876 passed, 1 skipped, 19 warnings, 412 subtests passed，44.15s** |
| `cd frontend && npx playwright test src/ --reporter=line --workers=1` | **92 passed** |
| `cd frontend && npm run build` | **exit 0；tsc + Vite，2668 modules transformed**；仅既有 dynamic import / chunk size warning |
| 改动 TypeScript 文件 ESLint | **exit 0，0 warning** |
| `claude plugin validate plugins/ink-dream-story` | **Validation passed** |
| 插件 digest 重复迁移 | 第一次 `installations=1 refs=5 locks=1`；第二次 `0/0/0`，幂等 |
| `git diff --check` | **exit 0** |

后端 warnings 为既有 FastAPI `on_event` 弃用提示和 event bus coroutine resource warning，本专项没有新增测试失败。

### 6.1 浏览器视觉核验

在真实 Chromium、1440×900、本地 Vite 与真实 actor-scoped run read 下，拦截合法 dream-files 投影完成浏览器核验：

- 标题：`故事协作工作台`；
- tabs：`Assets / Outline`；
- Outline manuscript：3 项；
- overview：`overviewDepth=1`、`focusDepth=0`、`rail=0`、`tablist=1`、`manuscript=1`；
- focus：`overviewDepth=0`、`focusDepth=1`、`rail=0`、`tablist=0`、`manuscript=0`，且 focus layer 与 1200px 工作面同宽；
- 返回故事线、上一条、下一条各 1；执行页 CSS 的 `dashed` 仅 1 处；
- `.story-workspace-guidance-sidebar`：0；
- “驳回/失败/重试/归档/确认并继续”等后续执行禁用文案命中：0；
- 聚焦层：标题、返回故事线、来源文件、上下条均存在；
- 第二次确认按钮：0；
- browser console error：0。

截图证据：

- `frontend/output/playwright/dream-ui-task3/execution-overview.png`
- `frontend/output/playwright/dream-ui-task3/execution-focus.png`

两图均为 1440×900，并在 F10 后于 20:13:30 / 20:13:31 重新覆盖；截图与一次性测试数据不进入 git 提交，含测试令牌的临时脚本已删除。

## 7. 按设计实现 vs 留占位

| 项目 | 状态 | 说明 |
|---|---|---|
| `.dream` 静态/运行分层 | 已实现 | `workspace.json` 不回写 run 事实；运行事实进入 `runtime/runs/<run_id>` |
| 人物/场景/分镜写入时点 | 已实现 | 插件先写 canonical 文件，再调用 stage MCP 工具；页面按文件出现 |
| Agent `.dream` 写边界 | 已实现 | 仅两个 MCP 工具可写运行内容层；存在 `.dream` 的 workspace 中通用 Bash 只允许确定只读命令，动态代码/脚本也不能间接写入 |
| GET dream-files | 已实现 | actor/run/thread/source 校验，REST 为页面真相源 |
| 页面修改与一次确认 | 已实现 | 三个允许字段、本地草稿、revision 冲突、actor+run 单次确认、隐藏原-thread 命令；刷新后不再二次确认 |
| 同一 Chat Agent 续跑 | 已实现（at-least-once） | 确认先持久为 pending；后台协调器在提交后、周期扫描和服务重启后透明交付；只有 `message-final` 与非 error 终止帧同时出现才确认 dispatched，其他结果保持 pending 并按 message ID 指数退避 |
| 后续执行布局 | 已实现 | Assets / Outline 处于单一 overview 工作面；选择条目后 focus 全层替换 overview，无固定 rail/grid 或常驻第三栏 |
| 驳回/失败/重试/归档/二次确认 UI | 已移除 | 旧执行五态与指导侧栏删除，旧聚合入口隐藏；Dream 工作流上下文固定为“Dream 协作中”，不透出底层 rejected/failed/cancelled |
| G1/G3：初始 queued run 自动推进与 Dream 发起接线 | **遗留** | 本期没有新增初始生产推进方；受控 MCP 只接受 host 已绑定的 run/thread，不猜最近 run |
| G6：六态聚合端点 | **遗留且降级隐藏** | 聚合端点仍缺位；前端不本地推导。最终 Dream UI 只接受四个生命周期桥接展示值 |
| writer 主动发送 run-scoped SSE | **遗留，不影响正确性** | REST 是真相源；writer 自身不发事件，waiting/editing/continuing 使用至少 5 秒轮询；只有携带匹配 runId 的兼容事件可提前读取 |
| completed 自动判定 | **依赖既有运行推进方** | execution 访问门禁只认持久确认事实；文件合同不自造完成事实。执行页以既有 WorkflowRun completed 决定完成文案与停止轮询；Dream 修改页为持续观察 revisions 保持活跃态轮询 |
| 聚焦层丰富镜头结构/带时间历史 | **字段级占位** | 当前 stage item 只有名称、摘要、relations、sourceFile；聚焦层据此渲染。详细镜头列表与带时间历史需未来扩展 canonical stage schema |
| 文件与 SQLite 跨域原子性 | **明确边界** | 确认采用 revision 双读与 SQLite 事务，不能把文件系统和 SQLite 变成单一原子域 |
| 派发 exactly-once | **不承诺；提供 at-least-once** | 隐藏消息本身是零 DDL durable work item；异常/取消/调度中断保持 pending。Agent stream 完成后、SQLite ack 前进程退出会以同一 message ID 重复交付，但不会出现“已记 dispatched 而 Agent 尚未消费”的丢单窗口 |
| 视频模块、画布交互、拖放决策控件 | 本期不做 | 沿 SUO-198 边界，没有纳入 Dream 业务主链 |

## 8. 更新后的设计文档清单

任务二已更新并作为本期实现输入：

1. `docs/architecture/术语表.md`；
2. `docs/design/story-workspace/design_004_story-workspace-dream-surface-execution-page.md`；
3. `docs/design/story-workspace/design_006_dream-protocol-dir-mapping.md`；
4. `docs/design/story-workspace/design_007_dream-business-module-interaction.md`；
5. `docs/design/story-workspace/story-workspace-prd.md`；
6. `docs/design/story-workspace/story-workspace-layout-design.md`；
7. `docs/design/story-workspace/2026-08-04-dream-protocol-task2-design-implementation-record.md`；
8. `docs/design/story-workspace/2026-08-04-dream-protocol-task2-review-revision-implementation-record.md`。

任务三新增本实施记录。没有执行文档归档。

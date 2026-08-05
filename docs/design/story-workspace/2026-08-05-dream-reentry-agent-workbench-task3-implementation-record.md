# Dream 可恢复入口与 Dream Agent 工作台：任务三实施记录

> 日期：2026-08-05  
> 设计输入：`design_008_dream-reentry-and-agent-workbench.md:663-698`  
> 记录范围：U1～U5 的实现、测试、独立复审、质量门禁与真实环境验收。代码符号保持英文；本记录使用中文。

## 1. 实施结论

Dream 工作台的工作区实现已形成四个独立边界：服务端持久 run 聚合、run-bound Dream Agent 安全消息 adapter、右侧 Dream Agent rail、Dream 专属悬浮 dialog。`.dream` stage 仍由既有 REST polling 读取，消息流不取得 stage 或本地 draft 的 owner。

本地契约、单元/Node seam、类型检查、构建与改动前端文件 ESLint 均已通过；但 U3/U4 的独立 commit 硬约束被只读 `.git` 阻断，故不是满足全部 Task 3 硬约束的完成态。真实浏览器和真实外部 Agent 的新增 run 验收也受执行环境阻断，未把静态或模拟测试写成真实端到端成功。详细边界见第 2、6、7、8 节。

## 2. 单元 Red → Green → 评审 → commit 记录

| 单元 | 实现范围 | Red / Green 证据 | 独立评审 | commit |
|---|---|---|---|---|
| U1 | durable Dream re-entry 查询、actor/Deck/run 物理映射校验、集合合同 | Red：缺 service/route 时 `4 failed`；Green：最终相关组合 `100 passed, 77 subtests passed`。`backend/tests/test_story_workspace_dream_reentry.py:303-377,379-464,476-516` 覆盖 lifecycle、foreign/forged binding、stable ordering、actor scope | 独立 U1 评审经历三轮返工后 PASS：Dream manifest identity、全部 active + top-20 recent、批量 confirmation 与单次必要文件读取均闭合 | `ff6d62f`,`f36d58a`,`15914b1`,`62afc0c` |
| U2 | canonical `/story-workspace/dream` 恢复入口、`?run=` 定位、Deck 辅助入口和顶部 context 迁移 | Red：缺 `useStoryWorkspaceDreamRuns` module/export；Green：最终专项 `35 passed`，另有本轮全量 Node seam（第 5 节）。行为 seam 见 `StoryWorkspaceDreamReentryLayout.test.ts:17-48` | 独立 U2 评审经历两轮返工后 PASS：权限回退、legacy replace、严格 parser 与 abort 均闭合 | `54baf96`,`81b0f70`,`d1c7adc` |
| U3 | Dream Agent snapshot、filtered SSE、同 run/thread 安全发送与持久 claim | Red：专项首轮 `1 failed, 4 passed`（缺 SSE keepalive），返工 CAS Red 为 `1 failed, 15 passed`；Green：专项 `16 passed`，组合回归 `410 passed, 1 skipped, 184 subtests passed`。覆盖见 `test_story_workspace_dream_agent_messages.py:102-414,449-529,565-611` | 独立 U3 评审经历两轮返工后 PASS：source 证明、expected-turn、lease/CAS、busy、workspace binding 与截断均闭合 | 续接后 `.git` 仅允许只读，未创建 SHA；实现保留在工作区，未暂存 |
| U4 | Dream adapter/view model、rail、dialog、焦点/窄屏/未读交互 | 过程偏差：最初先写 adapter/组件骨架才落测试，未把该阶段冒充 Red；主代理叫停后取得真实 Red（缺 send/recovery/focus seam export），最终专项 `12 passed`，全量 Node seam 见第 5 节 | 独立 U4 经两轮返工后 PASS：认证 fetch SSE、terminal reconciliation、rail 无逐 token `aria-live`、未读与焦点循环均闭合 | 当前 `.git` 仅允许只读，未创建 SHA；实现保留在工作区，未暂存 |
| U5 | 跨单元质量门禁、真实环境审计、本文档 | 第 5～8 节 | 不替代 U3/U4 独立评审；仅汇总可复核输出 | 不提交（`.git` 只读） |

**独立 commit 硬约束：BLOCKED。** U3、U4 有专项 Red/Green 与独立复审证据，但不能在只读 `.git` 中分别提交；它们是“已在工作区实现并验证、未完成独立 commit 交付”的状态，不能表述为 Task 3 全量 PASS。

## 3. 变更文件与组件边界

### 3.1 U1/U2 已提交的完整文件集合

下列是 `git show --format= --name-only ff6d62f f36d58a 15914b1 62afc0c 54baf96 81b0f70 d1c7adc | sort -u` 的完整输出：

| 路径 | 说明 |
|---|---|
| `backend/routers/story_workspace.py` | U1 Dream run 聚合路由。 |
| `backend/services/deck/story_workflow_gateway.py` | U1 actor-scoped 聚合 gateway。 |
| `backend/services/story_workspace/dream_reentry_service.py` | U1 run/Deck/thread 物理映射、排序和投影。 |
| `backend/story_workspace/contracts.py` | U1 re-entry DTO（U3 在此 canonical owner 扩展消息 DTO）。 |
| `backend/tests/test_story_workspace_dream_reentry.py` | U1 pytest。 |
| `frontend/src/App.tsx` | U2 Deck 辅助导航。 |
| `frontend/src/api/storyWorkspaceApi.ts` | U1/U2 re-entry transport。 |
| `frontend/src/components/DeckEditorModal.tsx`、`DeckManager.tsx` | U2 Deck → canonical Dream 入口。 |
| `frontend/src/hooks/story-workspace/__tests__/useStoryWorkspaceDreamRuns.test.ts` | U2 Node seam。 |
| `frontend/src/hooks/story-workspace/contracts.ts`、`index.ts` | U1/U2 前端合同/export（U4 在同一 owner 扩展消息合同）。 |
| `frontend/src/hooks/story-workspace/useRunDeepLink.ts`、`useStoryWorkspaceDreamRuns.ts` | U2 query 解析与服务端 run 发现。 |
| `frontend/src/pages/story-workspace/StoryWorkspaceDreamLaunch.tsx`、`StoryWorkspaceDreamPage.tsx`、`.css` | U2 首页/re-entry 与 Dream 页面组合（U4 在同页面追加 rail/dialog）。 |
| `frontend/src/pages/story-workspace/__tests__/StoryWorkspaceDreamReentryLayout.test.ts` | U2 layout seam。 |
| `frontend/src/router/story-workspace.tsx`、`storyWorkspacePath.ts`、`__tests__/storyWorkspacePath.test.ts` | U2 canonical 路由和 legacy deep-link 降级。 |

### 3.2 U3/U4 当前工作区的 Dream 文件（未提交）

| 路径 | 说明 |
|---|---|
| `backend/story_workspace/contracts.py` | run-bound Dream Agent command、safe message、snapshot/accepted DTO；唯一后端 Story Workspace 合同 owner。 |
| `backend/services/story_workspace/dream_agent_message_service.py` | allowlist snapshot、filtered SSE、幂等 claim/lease 与同 thread dispatch。 |
| `backend/services/deck/story_workflow_gateway.py` | 可信 run/Deck/thread 上下文读取与消息 gateway。 |
| `backend/routers/story_workspace.py` | run scoped snapshot、events、send 路由。 |
| `backend/claude_agent/service.py`、`thread_factory.py`、`thread_pool.py` | 仅复用底层消息持久化/expected-turn transport，不把 ChatView 置入 Dream。 |
| `backend/tests/test_story_workspace_dream_agent_messages.py` | U3 Red/Green pytest。 |
| `frontend/src/hooks/story-workspace/contracts.ts` | 唯一前端 Story Workspace 局部合同 owner。 |
| `frontend/src/hooks/story-workspace/useStoryWorkspaceDreamAgent.ts` | Dream 专属 snapshot + SSE + reconciliation adapter。 |
| `frontend/src/components/story-workspace/dream/StoryWorkspaceDreamAgentRail.tsx` | 右侧收起态 context/status/preview 入口。 |
| `frontend/src/components/story-workspace/dream/StoryWorkspaceDreamAgentDialog.tsx` | 展开态 Dream 专属历史、输入、Escape/焦点/aria 交互。 |
| `frontend/src/components/story-workspace/dream/storyWorkspaceDreamAgentFocus.ts` | 窄屏 modal 焦点循环。 |
| `frontend/src/pages/story-workspace/StoryWorkspaceDreamPage.tsx`、`.css` | rail/dialog 组合、桌面与窄屏布局；保留编辑器。 |
| `frontend/src/router/story-workspace.tsx` | Dream route 移除顶部完整 `WorkflowContextBar` owner。 |
| `frontend/src/**/__tests__/useStoryWorkspaceDreamAgent.test.ts`、`StoryWorkspaceDreamAgentLayout.test.ts` | U4 Playwright Node seam。 |
| `docs/design/story-workspace/2026-08-05-dream-reentry-agent-workbench-task3-implementation-record.md` | U5 集成记录、17 项矩阵、质量门禁与真实验收边界。 |
| `docs/design/story-workspace/2026-08-05-dream-reentry-agent-workbench-task1-problem-decision-record.md`、`design_008_dream-reentry-and-agent-workbench.md`、`2026-08-05-dream-reentry-agent-workbench-task2-design-record.md` | Task 1/2 决策、设计与评审输入；不替代 U3/U4 的独立 commit。 |

`backend/database.py` 没有 diff；本期没有新增 DDL。与 Claude 子代理、侧栏、i18n 等并行工作线的文件均未被本单元编辑、暂存或回滚。

## 4. 用户 17 项验收证据矩阵

| # | 验收项 | 证据 | 结论 |
|---:|---|---|---|
| 1 | 离开后从 canonical 入口恢复同 run | re-entry run 集合和 canonical layout seam：`test_story_workspace_dream_reentry.py:303-325`、`StoryWorkspaceDreamReentryLayout.test.ts:17-23` | 契约通过；真实浏览器阻断 |
| 2 | 刷新恢复同 run/stage revisions | `useRunDeepLink.test.ts:53-65`、`useStoryWorkspaceDreamFiles.test.ts:88-200` | Node seam 通过；真实刷新阻断 |
| 3 | 重新登录依赖后端持久事实 | `test_story_workspace_dream_reentry.py:327-369,466-516` 与 layout 中禁用 localStorage：`StoryWorkspaceDreamReentryLayout.test.ts:17-23` | 契约通过；真实登录阻断 |
| 4 | 外部用户/错误 Deck 不可访问 | `test_story_workspace_dream_reentry.py:327-369`、`test_story_workspace_dream_agent_messages.py:449-466` | pytest 通过 |
| 5 | 多 run 分组、排序、显式选择 | `test_story_workspace_dream_reentry.py:303-325,379-411,431-452` | pytest 通过 |
| 6 | snapshot 后再追加增量 | `useStoryWorkspaceDreamAgent.test.ts:27-47,56-78` | Node seam 通过 |
| 7 | 重连不重不漏 | `useStoryWorkspaceDreamAgent.test.ts:100-150` 实际执行 “A → 断流 → snapshot 对账 → `after=A` → replay A+B”，断言 A 一次、B 不漏、latest cursor B；SSE cursor 过滤见 `test_story_workspace_dream_agent_messages.py:232-253` | 自动化 seam/pytest 通过；真实浏览器断网恢复未验证 |
| 8 | 仅公开 assistant 内容 | `test_story_workspace_dream_agent_messages.py:102-230,232-271` | pytest 通过；reasoning/tool/credential 断言不外泄 |
| 9 | 点击 rail 打开专属 dialog | `StoryWorkspaceDreamAgentLayout.test.ts:15-32` | Node seam 通过；真实点击阻断 |
| 10 | Escape 关闭并归还焦点 | `StoryWorkspaceDreamAgentLayout.test.ts:22-39` | Node seam 通过；真实键盘阻断 |
| 11 | 发送复用同一 run/thread | `test_story_workspace_dream_agent_messages.py:396-415` | pytest 通过 |
| 12 | 快速连续发送不重复 dispatch | `test_story_workspace_dream_agent_messages.py:273-383,508-529` | pytest 通过 |
| 13 | 消息不覆盖未确认 local draft | adapter 不依赖 draft reducer：`StoryWorkspaceDreamAgentLayout.test.ts:41-47`；stage dirty rebase：`StoryWorkspaceDreamState.test.ts:380-432` | Node seam 通过 |
| 14 | stage 仍由文件 REST revision 驱动 | `useStoryWorkspaceDreamFiles.test.ts:81-200`、`test_story_workspace_dream_files.py:449-496` | Node seam/pytest 通过 |
| 15 | Dream 源码/运行时不挂 ChatView | `StoryWorkspaceDreamAgentLayout.test.ts:15-21`；本轮 `rg` 对 Dream page/adapter/components 无命中 | 源码通过；运行时 DOM 阻断 |
| 16 | 无业务驳回、失败、人工重试、归档按钮 | Dream 文件 `rg` 无业务按钮/状态命中（仅技术注释 `StoryWorkspaceDreamPage.tsx:169`） | 静态通过；运行时 DOM 阻断 |
| 17 | desktop 与 390px 窄屏无严重遮挡/溢出 | `StoryWorkspaceDreamAgentLayout.test.ts:49-58`（420px 宽、窄屏 media、88dvh、reduced-motion） | layout seam 通过；真实 viewport 截图阻断 |

## 5. 已执行质量门禁

| 命令 | 输出摘要 | 状态 |
|---|---|---|
| `backend/.venv/bin/python -m pytest -q tests/test_story_workspace_dream_reentry.py tests/test_story_workspace_dream_api.py tests/test_story_workspace_dream_files.py tests/test_story_workspace_dream_confirmation.py tests/test_story_workspace_dream_launch.py tests/test_story_workspace_dream_launch_api.py tests/test_story_workspace_dream_agent_messages.py` | `160 passed, 55 subtests passed in 4.05s` | PASS |
| `frontend: npx playwright test $(find src -path '*/__tests__/*' ...) --reporter=line --workers=1` | `122 passed (824ms)` | PASS |
| `frontend: npx tsc -b` | exit 0 | PASS |
| `frontend: npx vite build` | `✓ built in 675ms`；仅既有 chunk-size/dynamic-import 警告 | PASS |
| `frontend: npx eslint <全部当前改动的前端 TS/TSX/JS/JSX>` | exit 0 | PASS |
| `git diff --check` | 无输出，exit 0 | PASS |
| `git diff -- backend/database.py` | 无输出 | PASS |
| `rg -n "ChatView|ChatWidgetUI" <Dream page/adapter/components>` | 无命中 | PASS |

一次误触发的无文件参数 `npx eslint` 会扫描整个历史仓库，报出 69 个既有 error/20 个 warning；它不属于当前改动文件，也未被本轮修复或夹带。上表的定向 ESLint 命令实际覆盖本轮所有改动的前端代码文件并通过。

## 6. 真实数据与浏览器验收

### 6.1 只读真实数据证据

使用 SQLite immutable 只读连接审计 `backend/data/ink-and-memory.db`：

- 已存在真实 drama-forge Deck：`e843a442-94fa-4466-8c68-42a2d1e4b240`；
- 已存在完整真实 run：`run_2cb652215c38423398544133ff1b38c1`；
- 其绑定 thread：`f9f9e1d9-ed20-57c6-a767-b903211c1c7d`；
- 三个 stage 物理文件均存在：`backend/data/agent-workspace/f9f9e1d9-ed20-57c6-a767-b903211c1c7d/.dream/runtime/runs/run_2cb652215c38423398544133ff1b38c1/stages/{characters,scenes,storyboards}.json`；
- 同一 thread 当前数据库计数：assistant `2`、user `2`；
- 最新同 Deck 已有另一个完整 run `run_95e3a4e9dfd54ad1bb93b2e5dab48760` / thread `2d6028d1-6a80-531d-9492-82fac9196e09`，说明多 run 真实数据条件存在。

这是对既有真实 run 的只读恢复证据，不是本轮新发起的外部 Agent run，也不能取代浏览器流程。

### 6.2 诚实阻断

1. Playwright CLI 技能要求的 wrapper `/Users/dmeck/.codex/skills/playwright/scripts/playwright_cli.sh` 已按 open → snapshot 顺序调用，但 `npx --package @playwright/mcp` 因 DNS `ENOTFOUND registry.npmjs.org` 失败；离线重试为 `ENOTCACHED`。随后确认仓库现有 `playwright 1.62.1` 与 Chromium 可执行文件存在，并尝试不绑定端口的 route-fulfilled runtime（真实 `frontend/dist` + 真实 run/stage 只读事实 + mock transport）；Chromium 进程启动后被 macOS sandbox 拒绝 Mach port 注册：`FATAL mach_port_rendezvous_mac.cc:159 bootstrap_check_in ... Permission denied (1100)`，15 秒超时；`--no-sandbox`、禁用 GPU 均不能越过该限制。未生成可用 browser session、screenshot 或 trace。
2. 用户原有前端 PID `37471` 显示监听 `5173`，但本执行网络命名空间对 `127.0.0.1:5173` 和 `[::1]:5173` 都报 connection refused；未关闭该 PID。
3. 本单元启动自己的 `uvicorn server:app --host 127.0.0.1 --port 8017`，PID `2659` 完成 startup 后 bind 被沙箱拒绝：`[Errno 1] operation not permitted`，并已自动 shutdown/退出。没有存活的本单元后端 PID；没有连接到真实认证会话，因此没有安全方式发起 `/drama-forge:drama-init`、重新登录、确认或发送新消息。

因此，生成中离开、浏览器刷新、重新登录、390px 实际截图/trace、dialog 实际发送一次以及新增 run 的数据库前后计数，均是 **未验证**，不是失败状态，也没有被补造。

### 6.3 产物

浏览器产物目录已按约束创建：`/Users/dmeck/project/ink-dream-memory/output/playwright/dream-agent-workbench-20260805/`。由于上述阻断，目录为空（没有有效截图/trace）；没有伪造或复用旧截图。

## 7. 按设计实现 vs 诚实遗留

| 设计项 | 状态 | 证据/遗留 |
|---|---|---|
| durable canonical re-entry 与多 run 选择 | 已实现并测试 | §4 #1–5、§5 pytest/Node seam |
| 右侧唯一 context/status owner | 已实现并测试 | §4 #9、`StoryWorkspaceDreamReentryLayout.test.ts:25-28` |
| 安全 snapshot + filtered SSE + reconciliation | 已实现并测试 | §4 #6–8、§5 pytest/Node seam |
| 专属 Dream dialog、焦点与窄屏规则 | 已实现并测试 | §4 #9–10、#17 |
| 同 run/thread 安全发送和并发 claim | 已实现并测试 | §4 #11–12 |
| `.dream` truth/local draft 隔离 | 已实现并测试 | §4 #13–14 |
| 重连 cursor A/B 自动化路径 | 已实现并测试 | §4 #7；不等同于真实浏览器断网恢复 |
| 使用真实 drama-forge 新建 run 的完整浏览器流 | 未验证 | §6.2 的 CLI/端口/认证阻断 |
| 新增真实 run 的截图、trace、重新登录和 DB 前后计数 | 未验证 | §6.2；只保留 §6.1 既有真实 run 的只读证据 |
| U3/U4 独立 commit | 未完成（硬约束 BLOCKED） | `.git` 只读；见 §2，不能作为全量 PASS 交付 |

## 8. 工作区隔离、终端与归档

- 本单元没有修改、暂存、回滚或提交 `backend/claude_agent/subagent_projection.py`、`frontend/src/components/chat/SubagentPanel.tsx`、`.folder.md`、i18n 与其他并行工作线文件。
- U1/U2 在权限降级前已形成独立 commit。续接后 `.git` 变为只读；U3 实现代理曾尝试仅暂存 U3 文件，但创建 `.git/index.lock` 被环境以 `Operation not permitted` 拒绝，且不存在遗留 lock。此后 U3/U4/U5 均未暂存或提交；没有执行 `git reset`、`git checkout` 或归档操作。
- 只启动过本单元 PID `2659`（port `8017`），已因 bind 拒绝自动退出；未关闭用户 PID `37471` 或其他用户服务。没有仍需关闭的本单元后端、浏览器或临时终端。
- 调研 PDF 生成的 `tmp/pdfs/ui-design-v2/page-04.png` 与 `page-05.png` 已在根级收尾中删除，`tmp/` 已移除；浏览器产物目录因阻断保持为空。
- 明确声明：**未执行归档操作。**

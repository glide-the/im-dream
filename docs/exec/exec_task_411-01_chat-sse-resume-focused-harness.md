<!-- [Input] SUO-424 checkout, task_411-01 N1-03 regression contract, current Chat source contract, and the two provider-free focused harnesses. -->
<!-- [Output] Durable attribution, fixture changes, exact focused-test receipts, rollback guidance, and completion disposition. -->
<!-- [Pos] ExecTaskAgent report for the Chat SSE/resume focused-harness unblock child of task_411-01. -->
<!-- [Sync] 2026-09-05: repaired current Chat boot/hydration fixtures and restored both focused regression gates. -->
<!-- [Sync] 2026-09-06: rebased current Dream source references from the retired frontend/src tree to frontend/app/_dream. -->

# Exec Report: task_411-01 — Chat SSE/resume focused harness

## 1. 执行上下文

- Task ID：`task_411-01`，仅覆盖 `N1-03-regression` 的 Chat harness 解阻子边界。
- Execute Issue：[`SUO-424`](/SUO/issues/SUO-424)，`standard` / `high`，checkout 后状态为 `in_progress`。
- Parent Issue：[`SUO-419`](/SUO/issues/SUO-419)；本子 Issue 独占两个 Chat provider-free harness，父任务不得并行改写。
- 当前 task 内容：归因并修复或正式 rebaseline `ChatDreamReconnect.test.ts` 与 `ChatQueuedSend.test.ts`，恢复 SSE/reconnect/resume 与 lazy queued-send focused gate。
- Task 文档：[`task_411-01_frontend_root-web-shell-vite-exit.md`](../task/task_411-01_frontend_root-web-shell-vite-exit.md)。
- Requirement：[`TASK-REQUIREMENT-task_411-01_frontend_root-web-shell-vite-exit.md`](../task/TASK-REQUIREMENT-task_411-01_frontend_root-web-shell-vite-exit.md)。
- 通用模板：[`TASK-REQUIREMENT-FORMAT.md`](../task/TASK-REQUIREMENT-FORMAT.md)。
- Stage：[`stage_mcp-apps-system-architecture.md`](../stage/stage_mcp-apps-system-architecture.md) Stage 1；本轮只回填 `N1-03-regression`，不宣告其余 Stage 1 或后续 Stage 通过。
- 直接设计引用：[`dream-frontend-node-framework-migration-assessment.md`](../design/claude-agent/dream-frontend-node-framework-migration-assessment.md) §3.2、§5.3、§9—§11、DEC-005；[`mcp-apps-system-architecture-execution-checklist.md`](../design/claude-agent/mcp-apps-system-architecture-execution-checklist.md) §5.1、§10—§12。
- 执行 Agent：`ExecTaskAgent`（`2a7a15fe-2ebb-4dc5-91a8-48ae2bcc5471`）。
- 执行时间：2026-09-05 17:32 +08:00。
- Checkout：`POST /api/issues/54698801-8e48-47b8-af62-aaba3a901ce0/checkout` 成功；唯一 assignee 为本 Agent，无 user assignee 或第二执行责任人。

## 2. TASK-REQUIREMENT-FORMAT.md 填充摘要

### 2.1 唯一绑定与执行目标

- 输入 Issue：[`SUO-424`](/SUO/issues/SUO-424) 及 CEOOrchestrator 的 execute-readiness 评论。
- 输入 Task：`task_411-01` 的 `N1-03-regression` Chat 子边界；不合并 411-02/03。
- 执行目标：先只读核对当前生产 Chat boot、history hydration 和 reconnect 合同，再仅修复两个失配 fixture，使 Issue 指定的两个原始命令均 exit `0`。
- 不代表：根 Next/App Router、Vite rollback、pnpm/standalone、Runtime、P0、Phase 1 或 production Apps Gate 通过。
- 共享 owner：`frontend/pnpm-lock.yaml` 仍为 411-03 exclusive writer；本轮未读取后写入、更未重锁。

### 2.2 验收、路径与测试填充

| 字段 | 填充值 |
|---|---|
| 验收条件 | 两个 Issue 原始 Playwright focused 命令均 exit `0`；记录关键输出与归因。 |
| 允许修改 | `frontend/app/_dream/components/chat/__tests__/ChatDreamReconnect.test.ts`、`ChatQueuedSend.test.ts`、同目录 `.folder.md`、两个测试 header、本文。 |
| 禁止修改 | 其余生产源码、根 Next/App Router、Vite rollback、locks、backend/schema、production Apps、design/issue/stage/task 文档及其他 dirty paths；未列路径默认禁止。 |
| 测试要求 | 从 `frontend/` 逐条运行两条原始命令；复用系统 Chrome；记录命令、退出码和关键输出；provider-free 技术验证。 |
| Hard stop | 若归因为生产缺陷，停止写入并在 Issue 记录目标路径、owner/action；若目标文件并发 dirty，停止且不得覆盖。 |
| 阻塞信息 | 无；CEO 已裁定 source/test owner，并在 checkout 释放后正式移交。 |

### 2.3 dirty-tree 与 single-assignee

- 执行前命令：`git status --porcelain=v1 --untracked-files=all`。
- 工作树存在大量与本子任务无关的既有修改和生成物；全部保持原状。目标两个测试和测试目录 `.folder.md` 在本轮前均为 clean。
- 目标文件修改前 SHA-256：`ChatDreamReconnect.test.ts` 为 `8e9c4d28a3bb678282422af2e09aaf91b83d3933d8d188b13fce907905d89139`；`ChatQueuedSend.test.ts` 为 `605d11a702f74aeb96901fee9e004f093d05555ce7b621e7215f9b40c1476212`。
- 本轮未 reset、restore、格式化或修改任何未授权 dirty path。

## 3. 模型生成的执行任务

模板填充通过后，模型生成并完成了以下单一执行任务；范围校验未发现越权路径：

1. 用 Issue 原命令复现两个失败并记录退出码。
2. 只读检查 `ChatView.tsx`、`threadSessionHydration.ts`、`claudeAgentSkillApi.ts` 与相关 API helper，确定当前 source contract。
3. 仅在两个 harness 中补齐现有生产契约所需 fixture；不改生产源码或业务语义。
4. 更新两个测试 header 与测试目录合同，执行两条原始命令、focused ESLint、Markdown 路径和差异检查。
5. 生成本文、回写 Issue 回执并将子 Issue 标记 `done`。

## 4. 归因与实现变更记录

### 4.1 归因

- `ChatDreamReconnect.test.ts` 返回的是旧 history body。当前共享 `fetchClaudeThreadMessages()` 分页 hydration 要求 `has_more`、`unchanged`，并使用 `latest_message_id` / `known_latest_message_id` 做 idle stabilization；fixture 缺字段导致 hydration fail closed、ChatPanel 不挂载，因此永远没有 SSE GET。生产行为符合当前合同。
- `ChatQueuedSend.test.ts` 的 unknown-request guard 未覆盖当前 Chat composer 的只读 `GET /api/claude-agent/skill-commands` boot contract。生产 helper 对失败会降级为空列表，但 strict fixture 应显式提供 `commands: []`，而不是把合法请求记为 unexpected。
- 结论：两项均为 provider-free fixture 漂移；两个既有命令仍是有效 `task_411-01` regression gates，无需 rebaseline 或替换命令。

| 文件 | 操作 | 说明 |
|---|---|---|
| `frontend/app/_dream/components/chat/__tests__/ChatDreamReconnect.test.ts` | update | 为 messages fixture 补齐分页与 latest-ID stabilization metadata，并按 query 回传 `unchanged`。 |
| `frontend/app/_dream/components/chat/__tests__/ChatQueuedSend.test.ts` | update | 显式 fixture 当前只读 common Skill catalog GET，返回空 command collection。 |
| `frontend/app/_dream/components/chat/__tests__/.folder.md` | update | 补登记 Dream reconnect harness，并同步两个 fixture 的当前合同。 |
| `docs/exec/exec_task_411-01_chat-sse-resume-focused-harness.md` | create | 记录填充模板、归因、变更、测试、证据、风险、回滚与完成状态。 |

未修改：任何生产源码、root Next/App Router、Vite/Docker/deploy、lock、backend/schema、production Apps、design/issue/stage/task 文档。

## 5. 测试与验证

### 5.1 浏览器前置

- 系统 Chrome：`Google Chrome 152.0.7977.77`；只做一次轻量可用性检查，未下载 Playwright Chromium revision。

### 5.2 失败基线

| 命令（cwd=`frontend/`） | Exit | 关键输出 |
|---|---:|---|
| `pnpm exec playwright test app/_dream/components/chat/__tests__/ChatDreamReconnect.test.ts --reporter=line --workers=1` | 1 | `Test timeout of 30000ms exceeded`；`page.waitForRequest` 未观察到 `/threads/thread-dream-chat/stream`。 |
| `pnpm exec playwright test app/_dream/components/chat/__tests__/ChatQueuedSend.test.ts --reporter=line --workers=1` | 1 | `unexpectedApiRequests` 为 `GET /api/claude-agent/skill-commands`。 |

### 5.3 修复后精确回执

| 命令（cwd=`frontend/`） | Exit | 关键输出 |
|---|---:|---|
| `pnpm exec playwright test app/_dream/components/chat/__tests__/ChatDreamReconnect.test.ts --reporter=line --workers=1` | 0 | `1 passed (5.3s)`。 |
| `pnpm exec playwright test app/_dream/components/chat/__tests__/ChatQueuedSend.test.ts --reporter=line --workers=1` | 0 | `1 passed (4.8s)`。 |

这两项是 provider-free、真实本机 Chrome 技术验证，不是本机真实业务测试或真实模型验收。

### 5.4 补充验证

- `pnpm exec eslint -- app/_dream/components/chat/__tests__/ChatDreamReconnect.test.ts app/_dream/components/chat/__tests__/ChatQueuedSend.test.ts`：exit `0`，无输出。
- `git diff --check -- frontend/app/_dream/components/chat/__tests__/ChatDreamReconnect.test.ts frontend/app/_dream/components/chat/__tests__/ChatQueuedSend.test.ts frontend/app/_dream/components/chat/__tests__/.folder.md docs/exec/exec_task_411-01_chat-sse-resume-focused-harness.md`：exit `0`，无输出；另以 trailing-whitespace scan 覆盖未跟踪的新报告。
- Markdown inventory：逐一 `test -e` 本文引用的 template、requirement、task、stage 与两份 design 文档，exit `0`。

## 6. 风险与阻塞

- 风险：fixture 需要随共享 history pagination 与 Chat boot collection 合同演进；unknown-request guard 继续保持 fail closed，可捕获未来未声明请求。
- 阻塞：无。
- 需要上游澄清的问题：无。
- 父任务恢复：[`SUO-419`](/SUO/issues/SUO-419) 可通过本子 Issue 的 blocker resolution wake 继续，不在本轮直接修改其 checkout 边界。

## 7. 完成状态与 Stage handoff

- [x] 已完成实现
- [x] 已完成两条必需 focused 测试
- [x] 已记录变更、归因和验证证据
- [x] 已满足本子 Issue 验收条件
- [x] 可标记子 Issue `done` 并解除父任务 blocker

本报告只完成 Stage 1 `N1-03-regression` 的两个 Chat focused harness；其余 `N1-*`、411-02/03、Phase 1、P0、standalone 与 production Apps 仍按各自 owner/readiness 处理。

## 8. 回滚建议与执行完成报告

- 回滚对象仅为本轮四个授权路径；不要回退工作树其他既有变更。
- 回滚方式：反向移除 Dream fixture 的四个 pagination/stabilization 字段与 query 计算、queued-send 的 common Skill GET fixture、对应 header/folder 条目，并删除本文；随后重跑两条原始命令确认回到失败基线。
- 回滚触发条件：当前生产 Chat contract 被正式改回非分页 history hydration，或 common Skill catalog 不再是 Chat boot 的只读依赖；不得仅因无关测试失败回滚。
- 注意事项：回滚会重新引入本 Issue 已确认的两个 harness 假失败，因此只应与生产合同变更原子执行。
- 最终结论：source/test owner 已解析，两个原始 gate 均有效并恢复为 exit `0`；无生产缺陷、无替代 gate、无遗留 blocker，可进入上游 review/audit。

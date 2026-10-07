<!-- [Input] User-applied Admin 0077, approved v3 design and normal localhost Dream/Admin/Gateway services. -->
<!-- [Output] Post-release real-business E2E scope, commands, UI evidence and remaining verification limits. -->
<!-- [Pos] Real-business acceptance receipt; earlier isolated validation remains separately preserved. -->
<!-- [Sync] 2026-10-07: retain two real preflight failures, exact v3 authority repair, verified config edits, and pending normal Admin reload; no successful scheduled model turn is claimed. -->

# 0077 发布后定时任务真实业务 E2E

## 本轮优化提示词

Optimized Prompt: 使用现有登录账户 dmeck@suoxya.com 和正常本机 Dream、Admin、Gateway、PostgreSQL，验证用户已应用的 0077/v3 capability。通过可见界面创建任务、查看对话标记与右侧详情、等待真实定时触发，核验源会话继续执行、选中模型、自动笔记写入、最后结果与会话导航；再编辑重复规则与新会话选项、立即运行、暂停及恢复。只创建本轮具名业务实体，不改已有正文或账户，不重启用户服务，不执行迁移。API/数据库仅用于读取并核对已经执行的界面业务事实。保留所有真实任务/Thread/Run/Gateway回执，结束前暂停自有周期任务。失败先区分产品、harness、环境与文档问题，再修复并重新验证。明确报告真实验收与隔离技术验证的区别。

## 影响范围与测试资源

| 业务事实 | 权威来源与执行 owner | 页面消费者 | 本轮影响 |
|---|---|---|---|
| 定时任务配置和 revision | Admin v3 service / PostgreSQL | Chat 任务标记、详情、Calendar | 创建及编辑唯一具名验收任务 |
| Thread 与 Claude session | 既有 ClaudeAgentService / ThreadFactory | Chat 历史、任务会话链接 | 验证 source resume 和新 Thread 模式 |
| Run 与模型调用 | 既有 Agent turn / Gateway | 运行结果和正常 Admin 日志 | 真实调用，保留回执 |
| Writing 笔记 | Editor tools / Session API 持久化 | Writing 与 Diary | 仅新增具名验收笔记并追加验收文字 |
| Project、Episode、canonical/private artifact 与 Hook | 既有 Dream 工作台文件及发布流程 | Dream 工作台 | 不涉及，无资产写入或发布 |
| 其他任务、笔记、账户、账本 | 既有业务记录 | 所有既有消费者 | 保持原状；不清理历史真实验收记录 |

前端 5173、后端 8765、Admin/Gateway 3000 均复用正常服务。浏览器使用已安装 Chrome 和已登录现有账户，不创建测试身份或直接写认证数据库。不重启服务、不执行故障注入；重启、竞争、失败注入由已有隔离技术回执覆盖，不能称为本轮真实流程验证。

## 预定义用户旅程

1. Writing 新建具名验收笔记；Chat 自然语言创建每分钟任务，运行时只向该笔记追加具名文字。
2. 对话显示任务标记；右侧显示任务信息、会话、任务周期；等待自然定时触发并核验结果。
3. 通过 Calendar 查看最后结果、打开对应聊天；核验任务快照、Thread、Run、模型及 Gateway 回执。
4. 编辑每小时、每天、工作日、每周和自定义，验证保存与 revision；选用新聊天和可用模型并立即运行。
5. 暂停、恢复后重新暂停本轮任务；保留正常业务历史及截图供复核。

## 执行回执

### 结论与当前门禁

**真实完整业务 E2E 尚未通过。** 0077/v3 capability 已在正常数据库发布，Chat 创建任务、任务标记/右侧详情、五类重复配置、模型及新聊天选项均已通过真实 UI 操作核验。两次自然触发均在模型调用前失败，错误为 `SCHEDULE_PREFLIGHT_FAILED`；后端终端给出的具体原因是 Admin 返回 `SCHEDULE_AUTHORITY_OPERATION_DENIED (403)`。

原因归类为 **Admin 产品代码遗漏 + 正常运行进程仍加载旧构建**：`resolveScheduledChatAuthority()` operation allowlist 缺少已注册的 `scheduled-trigger.v3.authority.resolve`。本轮补入精确 operation，保留签名、service、owner、Thread、claim、lease 的全部校验；不使用通配符，不修改 schema 或普通 turn 协议。单元/隔离 PostgreSQL/类型/lint/独立 build 已通过，但没有把这些回执当作正常进程已加载的证据。

正常 Admin 3000 的 PID 为 `8399`，由 `pnpm start` 运行。读取构建产物可核对：当前 `.next/server/chunks/2970.js` 的该 allowlist 不含 v3；独立 `.next-e2e-scheduled0077-20261007/server/chunks/2970.js` 含 v3。独立构建没有覆盖运行中的 `.next`。仓库禁止 E2E 停止用户已有服务，已请求正常 Admin 重启授权；收到授权/用户重启后继续自然触发和真实模型复测。

### 本轮正常业务实体

| 实体 | ID / 当前事实 |
|---|---|
| 账户 | 已登录的 `dmeck@suoxya.com`，未创建新身份或写认证表 |
| 任务 | `d30f3f2d-2617-49bb-a936-730a2271e2b2`，标题 `0077周期验收-20261007140101` |
| 创建 Thread | `f5f2a657-6256-4c29-842b-c53192db6631` |
| 新增验收笔记 | `ab91b475-d92f-415f-be1b-5cbc5c4894a4`，只允许本轮任务操作这条笔记 |
| 第一自然触发 | `1aba7988-51c3-4056-be80-59fa350fb93d`，2026-10-07 22:02:37.611 +08:00，revision 1，failed |
| 第二自然触发 | `a673493d-0bf6-44fc-ba29-ef417812bc78`，2026-10-07 22:07:56.242 +08:00，revision 3，failed |
| 结束前配置 | revision 9，`paused`，`next_run_at=null`，每隔 10 分钟，新 Thread，`gpt-5.6-luna` |

两个失败 trigger 都正确保存了 source Thread、目标 Thread、input message、mode/model/revision 快照；`target_turn_id`、`final_message_id` 为 null。它们没有启动 scheduled Agent turn，不能声明已验证 Claude resume、Run/Gateway 结算或笔记自动写入。只读核对显示验收笔记保留初始文字，未出现追加标记。

### 需求—设计—实现—测试追踪

设计依据为 [现行 v3 设计](codex-repeat-and-run-options.md)；产品布局由 [定时任务 PRD](../../prd/scheduled-tasks/codex-repeat-and-run-options.md) 所有。

| 业务流程 | 生产入口 / 实现 | 本轮正常业务事实 | 尚需验收 |
|---|---|---|---|
| 创建定时任务 | Chat → `mcp__user__create_scheduled_task` → Admin v3 | 真实模型 Tool 创建成功，revision 1 | 无 |
| 查看配置、对话任务标记、右侧详情 | `ScheduledTaskMarker` / `ScheduledTaskDetailSidebar` | 可见任务信息、会话、任务周期；未以 conversation 卡片替代任务 | 无 |
| 到时触发 | `ScheduledTaskCoordinator` → claim/prepare | 两次自然触发均写入正常业务 trigger | 修复加载后重新自然触发 |
| 生产入口继续会话、Claude turn | authority.resolve → ThreadFactory | prepare 绑定 source Thread 和 input；authority 被拒 | source resume 的成功 turn |
| Task、Thread、执行结果 | Admin definition/trigger / 既有 turn 持久化 | 失败历史可见；没有成功 turn/final message | 成功记录、Gateway 与 Token 回执 |
| 最新结果与打开聊天 | Calendar 最近结果 / 对应 Thread 导航 | 失败结果视图可打开；无成功结果正文 | 成功结果和准确运行 Thread 导航 |
| 编辑、revision、重复选项 | Calendar 主编辑 + 高级日程 | revision 5 每小时、6 每天、7 工作日、8 每周、9 自定义 10 分钟；POST 200、重开回显一致 | 新 revision 实际执行快照 |
| 暂停、恢复 | 既有 pause/resume | 第一次失败后暂停；恢复产生第二自然触发；再次暂停后配置编辑不触发 | 成功运行后的暂停/恢复 |
| 新聊天及模型 | v3 definition / trigger 快照 | 保存并回显 `new_thread_each_run`、`gpt-5.6-luna` | 新 Thread 的真实模型执行 |
| 自动笔记写入、不需确认 | 固定 Editor target + per-tool approval policy | 未到达工具执行阶段 | 实际写入、正文保留、无需确认 |
| 失败反馈 | Calendar failed + 最近结果 | 页面展示失败；后端记录安全 error code，真实根因已定位 | 修复加载后的恢复 |
| 重复触发、并发、进程恢复、删除/停用 | lease / unique constraints / reconcile / 状态机 | 本轮不注入正常服务故障或删除业务记录；隔离合同与 provider-free UI 回归另列 | 不把技术结果称为真实模型恢复验收 |
| 普通 Chat、Tool 创建、事件流 | 公开 Chat POST / 工具输出 / 历史 | 本轮创建 turn 正常完成、标记和详情正常 | scheduled source resume/cancel 全链路仍未覆盖 |

### 技术验证命令与结果

命令分别在明确标注的仓库工作目录执行。

| 目录 | 完整命令 | 退出码 | 关键输出 / 边界 |
|---|---|---|---|
| Dream 根 | `python3 .agents/skills/ink-dream-playwright-qa/scripts/preflight.py` | 0 | 已安装 Chrome 154.0.8037.98；未下载浏览器 |
| Dream frontend | `E2E_WEB_BASE=http://127.0.0.1:5173 pnpm exec playwright test e2e/scheduled-task-calendar.spec.ts --workers=1 --reporter=line --output=test-results/scheduled-v3-post0077-20261007` | 0 | 13 passed (51.3s)，provider-free 拦截 DTO；非真实模型验收 |
| Dream frontend | `pnpm exec eslint e2e/scheduled-task-calendar.spec.ts` | 0 | 无 lint 错误 |
| Admin 根 | `pnpm exec vitest run app/lib/dream/chatScheduledTaskAuthority.test.ts app/lib/dream/chatScheduledTaskRegistration.test.ts` | 0 | 2 files，9 tests passed |
| Admin 根 | `node scripts/run-chat-scheduled-task-contract.mjs` | 0 | 78/78 migration、7 PostgreSQL 集成通过；runner 自有隔离数据库及临时 PostgreSQL 已清理，正常库未被迁移 |
| Admin 根 | `pnpm exec eslint app/lib/dream/chatScheduledTaskAuthority.ts app/lib/dream/chatScheduledTaskAuthority.test.ts app/lib/dream/chatScheduledTaskPostgres.integration.test.ts` | 0 | 无 lint 错误 |
| Admin 根 | `pnpm exec tsc --noEmit` | 0 | 无类型错误 |
| Admin 根 | `INK_ADMIN_E2E_DIST_DIR=.next-e2e-scheduled0077-20261007 NODE_ENV=production pnpm build` | 0 | Compiled successfully in 67s，static pages 20/20；独立输出，未启动服务或迁移数据库 |
| Dream frontend | `pnpm exec eslint e2e/scheduled-task-real.spec.ts` | 0 | 修正后的真实 harness 静态验证 |
| Dream frontend | `pnpm exec tsc --noEmit` | 0 | 无类型错误 |
| Dream frontend | `pnpm exec playwright test e2e/scheduled-task-real.spec.ts --list` | 0 | 仅收集 1 个用例；未执行或宣称真实模型通过 |
| Dream 根 | `python3 frontend/test-results/scheduled-v3-calendar-20261007-final/check-docs.py` | 0 | 现行 6 份文档的 11 个本地链接有效 |
| Dream 根 | `node frontend/test-results/scheduled-v3-calendar-20261007-final/check-mermaid.mjs` | 0 | 现行设计 4/4 Mermaid 解析成功；仅文档检查 |
| 两仓库根 | `git diff --check` | 0 | 无 whitespace 错误 |

隔离数据库名为 `ink_scheduled_chat_test_contract_b623c53470`，自有临时目录为 `/var/folders/bn/m6tkvhx160d9nx6v6rkkkrj80000gn/T/ink-scheduled-chat-contract-o5xAOm`，自有 PostgreSQL 端口 53919；runner 只清理这些具名资源。正常数据库仍为用户本机服务。

只读辅助查询首次误用 `dream.chat_scheduled_task` 返回 `42P01`、退出码 1，归类为验证脚本的 schema 名错误；依据 Admin Drizzle `pgTable` 声明改为 `public` 后退出码 0。这不是产品缺陷，没有为此改 schema。

### 已修正的测试及文档错误

1. 旧 `scheduled-task-real.spec.ts` 直接读取签名键、签发 token 并 INSERT 登录记录，不符合公开正常认证流程。本轮真实验收使用已登录 Chrome，没有执行旧脚本；脚本已改为要求正常公开登录产生的 `INK_REAL_SCHEDULED_TASK_STORAGE_STATE`，再用 `/auth/session` 核对指定账户，缺失即失败。修正没有追认旧回执。
2. 旧脚本会遍历暂停历史同名前缀 QA 任务；改为 finally 只暂停本轮精确 task ID，保留其他业务记录。
3. 旧 poll 等待 `succeeded`，会在已出现 failed 终态后持续等待；改为终态即结束，再单独严格断言成功，没有放宽成功条件。
4. 旧编辑步骤把分钟输入当作主弹窗控件；改为先打开当前“高级日程”二级弹窗、编辑并应用，再主保存。
5. 正式时序和 operation 合同补充 v3 authority resolution 门禁；数据 capability 发布与运行中代码加载分别核验。

### 可复核产物

- 创建后的对话标记与详情截图（本机保留，未随公开 PR 提交：`../../../frontend/test-results/v3-real-post0077-20261007/chat-task-sidebar.png`）
- 第一次真实触发失败截图（本机保留，未随公开 PR 提交：`../../../frontend/test-results/v3-real-post0077-20261007/first-trigger-failed.png`）
- 新聊天及模型编辑回显截图（本机保留，未随公开 PR 提交：`../../../frontend/test-results/v3-real-post0077-20261007/edit-new-chat-model.png`）
- 最终暂停配置的原生 Chrome 截图（本机保留，未随公开 PR 提交：`../../../frontend/test-results/v3-real-post0077-20261007/final-paused-edit-native.png`）
- 真实任务创建回执（本机保留，未随公开 PR 提交：`../../../frontend/test-results/v3-real-post0077-20261007/task-created.json`）
- 真实配置修改 HTTP 回执（本机保留，未随公开 PR 提交：`../../../frontend/test-results/v3-real-post0077-20261007/mutations.json`）
- 正常数据库只读核对回执（本机保留，未随公开 PR 提交：`../../../frontend/test-results/v3-real-post0077-20261007/database-receipt.json`）

所有业务回执保留。当前唯一未继续的必需步骤是正常 Admin 加载修复后，重新执行 source/new Thread 的真实模型及自动笔记写入验收；不能标记为完整完成。

收尾时 Chrome 扩展控制提示需要更新；改用同一 Chrome 的原生窗口读取并保存最终配置截图，未更改浏览器、安装扩展或影响产品服务。该工具问题没有被报告为产品缺陷。

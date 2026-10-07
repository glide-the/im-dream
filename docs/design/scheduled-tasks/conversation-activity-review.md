<!-- [Input] 对话定时任务活动 PRD 与正式交互设计的实施前评审。 -->
<!-- [Output] 独立评审结论、问题闭合与技术验证证据。 -->
<!-- [Pos] 当前功能设计门禁与回执；不替代真实业务验收。 -->
<!-- [Sync] 2026-10-07: 独立设计评审通过，补充实现与 Provider-free 技术验证回执。 -->

# 对话定时任务活动评审

设计范围：创建 Thread 和定时任务执行 Thread 的活动记录、既有详情入口及 owner-scoped 只读投影。

实施前独立评审：`/root/activity_design_review` 完成只读评审，结论为**可实施，没有阻塞项**。评审完成后才开始功能代码。

- 已有 source_thread_id、owner 索引、target_thread_id 唯一约束和删除置空规则足以支持读取，无需 schema 变化。
- 复用严格 DTO、active subject、Thread owner 和 Runtime delegation 拒绝规则。
- 已修正新 operation 到整个 dreamOperations 末尾追加，保留 notionSyncRun 在内的旧 descriptor 顺序和 hash。
- 已补齐 Loading 中切换 Thread 的取消/清空及同 Thread 重试保留数据。
- 复用活动刷新周期、onConversationSettled、任务标记及共享详情回调；定义与执行状态独立。
- 桌面/窄屏骨架、正常/恢复时序、状态图与验收矩阵完整。

评审只执行只读核对，没有运行测试、调用模型或操作服务。

相关文件：[PRD](../../prd/scheduled-tasks/conversation-activity.md)、[正式设计](conversation-activity.md)。

## 实现范围

Admin 新增 `scheduled-task.v2.thread` 用户只读 operation；Dream 新增 `GET /api/claude-agent/threads/{thread_id}/scheduled-tasks` 认证入口。读取已有 source/target 关系，使用当前用户与 Thread owner 校验；没有新增 schema、迁移或后台执行入口。

PlanButton 读取当前 Thread 投影，TaskActivityContent 复用 ScheduledTaskMarkerList 渲染定时任务卡片。ChatView 将活动入口和创建消息入口绑定到同一个详情回调。创建回合结束、打开弹层、页面重新可见和既有刷新周期更新记录；切换 Thread 取消旧请求，读取失败保留同 Thread 已读取的记录。

## 技术验证回执

验证由 `/root/scheduled_activity_validation`（`luna_test_runner`）执行，使用已安装 Chrome、隔离 Vite fixture 和依赖注入。以下结果属于技术验证；未调用真实模型、访问正常业务数据库或执行真实业务验收。

| 工作目录 | 命令 | 退出码 | 关键输出 |
|---|---|---|---|
| `ink-admin-memory` | `pnpm exec vitest run app/lib/dream/chatScheduledTaskRegistration.test.ts app/lib/dream/chatScheduledTaskThread.test.ts` | 0 | 最终 9/9 通过：注册合同、owner 范围、创建/执行关系、历史与尚未运行任务、空关系、拒绝越权与额外字段。首轮 8/8；并行 registration 增补后复验为 5+4。 |
| `ink-dream-memory/backend` | `.venv/bin/python -m pytest tests/test_scheduled_task_activity.py tests/test_scheduled_task_consumer.py -q` | 0 | 13/13 通过：认证、公开路由与严格 DTO、缺少 operation/capability 时拒绝、来源 task/trigger ID 匹配。 |
| `ink-dream-memory/frontend` | `pnpm exec playwright test app/_dream/components/chat/__tests__/ScheduledTaskActivity.browser.test.ts app/_dream/components/chat/__tests__/TaskActivityPopover.browser.test.ts app/_dream/components/chat/__tests__/ScheduledTaskMarker.test.ts --workers=1 --reporter=line --output=test-results/scheduled-activity-20261007` | 0 | 4/4 通过，14.2 秒：仅有定时任务也显示入口、创建和执行记录、同一详情动作、独立状态、失败重试、创建后刷新、切换响应隔离、键盘与 390px 窄屏。 |
| `ink-dream-memory/frontend` | `pnpm exec tsc --noEmit --incremental false` | 0 | 前端类型检查通过。 |
| `ink-admin-memory` | `pnpm exec eslint app/lib/dream/chatScheduledTaskDto.ts app/lib/dream/chatScheduledTaskService.ts app/lib/dream/operationRegistry.ts app/lib/dream/chatScheduledTaskRegistration.test.ts app/lib/dream/chatScheduledTaskThread.test.ts` | 0 | 相关 Admin 文件 lint 通过。 |
| `ink-dream-memory/frontend` | `pnpm exec eslint app/_dream/api/scheduledTaskApi.ts app/_dream/components/chat/PlanPanel.tsx app/_dream/components/chat/TaskActivityContent.tsx app/_dream/components/chat/ScheduledTaskMarker.tsx app/_dream/components/chat/ChatView.tsx app/_dream/i18n.ts` | 0 | 最终 0 error、0 warning；捕获稳定 ref 对象后，请求清理提示已消除。 |
| `ink-dream-memory/frontend` | `pnpm exec playwright test app/_dream/components/chat/__tests__/ScheduledTaskActivity.browser.test.ts --workers=1 --reporter=line --output=test-results/scheduled-activity-20261007` | 0 | 请求清理调整后最终复验 1/1 通过，覆盖完整创建、执行、导航、失败恢复和切换流程。 |
| 两仓库 | `git diff --check` | 0 | 改动无空白错误。 |

首轮浏览器检查的断言失败已修正：详情原有文案为“创建任务的会话”，关闭弹层后节点沿用隐藏状态。上表为修正后的完整成功运行，未将首次失败汇报为通过。

Admin 全量 `pnpm exec tsc --noEmit --incremental false` 最终退出码为 2，仅剩本轮未修改的 `output/admin-pr-20261007/original-owned-files-before/tests/e2e/provider-routing.config.ts:5` 无法解析 `../../playwright.config`（TS2307）。首轮另有并行 `chatScheduledTaskTime.ts:155` 类型错误，最终复验已不再出现。Admin 全量类型检查仍未通过，不能将相关单测通过等同于全库类型检查通过。

两份 README 均为 15 个标题且层级一致，相关功能事实一致。新业务目录 Markdown 清单与链接已验证；两份现行正式设计稿合计 6 块 Mermaid 均由 Chrome `mermaid.parse` 解析通过。清单中的“未迁移文件（跳过）”表是历史迁移说明，不能当作当前目录文件清单。

可重复的文档检查命令（在 `frontend` 执行）：`node test-results/scheduled-activity-20261007/check-scheduled-activity-docs.cjs`，退出码 0，13 个本地 Markdown 链接及 94 项当前目录清单均存在，另已验证 workspace 文档迁移目标。Mermaid 检查命令：`node test-results/scheduled-activity-20261007/check-scheduled-activity-mermaid.mjs`，此前 6/6 解析退出码 0。脚本为本轮验证生成物，未进入生产代码。

截图：桌面活动（本机保留，未随公开 PR 提交：`../../../frontend/test-results/scheduled-activity-20261007/app-_dream-components-chat-02c73-and-isolates-Thread-changes/scheduled-activity-desktop.png`）、窄屏活动（本机保留，未随公开 PR 提交：`../../../frontend/test-results/scheduled-activity-20261007/app-_dream-components-chat-02c73-and-isolates-Thread-changes/scheduled-activity-mobile.png`）。

本轮 operation 初次生成时逐项核对原有 242 个 descriptor，追加第 243 项，`scheduled-task.v2.thread` hash 为 `8a49ad6c633e89d2272e187fb3ad85239fad22bbaa6fef823c2b0c22f565b389`。随后共享 Admin 工作区有其它 v3 调度改动；本回执不将初次计数作为后续全库数量或覆盖其它工作。

## 工作区与运行范围

Dream 位于 `develop`，Admin 位于 `main`；本轮未提交、推送或创建 PR。保留已有用户和其它 Agent 改动。未执行数据库写入、迁移、部署或服务重启；只关闭本轮自建浏览器/Vite 进程。现有正常服务未改动。真实模型和正常业务链路未验收，上述 Provider-free 检查不能替代发布前业务门禁。

<!-- [Input] User-reported stale Notion schedule, current production sources and read-only local Admin observations. -->
<!-- [Output] Diagnosis, selected status repair, proposed local execution configuration and validation receipts. -->
<!-- [Pos] Current Notion scheduling incident, technical validation and user-authorized local service recovery record. -->
<!-- [Sync] 2026-10-13: exact operations/schema published, claim gate and execution timings absent; source repair passes focused technical validation; user-authorized local service restart restores normal scheduled synchronization at 10:43 +08:00. -->

# Notion 自动同步状态修复

## 背景与问题

用户报告 `connector_sync_failed`，页面显示健康且下次计划停在 10 月 7 日 06:21。2026-10-13 本机 Admin 公开 capability 只读检查 exit 0：request、claim、renew、finish 四项 operation 的摘要以及依赖 schema 均与 Dream 固定合同精确匹配。候选读取 exit 0：授权 authenticated、七个来源、最近成功 2026-10-07 06:06:27 +08:00，策略 revision 2、status applied，投影计划为 06:21:29。

本机 Admin `.env.local` 和启动父环境均没有 `NOTION_SYNC_OWNERSHIP_CLAIMS_ENABLED`、`NOTION_SYNC_EXECUTION_POLICY_JSON`。Admin 配置的默认行为是在 claim 前返回 `NOTION_SYNC_CLAIMS_DISABLED`；领取关闭时不会创建 run，也不会写入 failed policy。Dream 原 worker 将所有异常合并为 `connector_sync_failed`。因此认证仍有效、上次成功索引仍在，但计划没有被执行，页面没有失败回执可读。

## 目标与边界

修正状态真实性、后台原因诊断与页面读取更新。保留原生产同步入口、最近成功索引和保存策略；不迁移数据库、不启用旧 writer、不增加第二个控制通道、不自动要求重新授权。初次诊断时 Dream 后端由用户的 Visual Studio Code 调试进程运行，没有自动重载；用户随后授权重启，恢复过程见文末回执。

源码验证阶段只读核查正常服务，故障注入和浏览器断言只使用已有命名内存 fixture，不更改真实账户、来源、正文或数据库。授权恢复阶段使用本机正常服务和已有来源，由正常后台 worker 写入同步结果；两个阶段均不调用模型。

## 概念与规则

- `applied` 表示策略已保存；`schedule_due` 表示服务器判断计划已到期。
- `worker_error_code` 是绑定 actor、connector、updated_at 的进程内观察，不能充当 Admin 执行终态。候选移除、连接版本改变或下一次合法裁决后不再使用旧观察。
- 页面按服务器扫描间隔串行读取，隐藏时停止，切换 actor 或写操作时取消旧 GET。状态刷新不保存、不重试同步，不覆盖未保存草稿。
- 日志只输出封闭错误码；未知异常或任意上游字符串统一为 `NOTION_SYNC_FAILED`。
- 选用现有 worker 和公开读取的附加投影；排除伪造 failed run、旧 patch 写状态、把计划滚到未来和新增持久化表的方案。正式规则及业务图分别见[PRD](../prd/notion-session/resource-connector.md)与[交互设计](../design/notion-session/connector-interaction.md#7-调度状态观察与恢复2026-10-13)。

## 本机运行配置（10:41 已按用户授权应用）

```dotenv
NOTION_SYNC_EXECUTION_POLICY_JSON={"lease_seconds":120,"heartbeat_seconds":30,"renewal_budget_seconds":20}
NOTION_SYNC_OWNERSHIP_CLAIMS_ENABLED=true
```

这些值是本机执行配置候选，不是产品同步频率或配额。预算 20 秒覆盖当前 10 秒 Admin HTTP timeout，heartbeat 加预算低于 120 秒 lease；同步仍按用户保存的 15 分钟策略执行。

原 Admin 发布合同要求先停止全部旧 Dream writer 和旧 Admin ingress，再证明旧写入口已拒绝，最后启用 claims。依据为 Admin 当前 `docs/design/notion-sync-ownership.md` 第 87 行和本仓[原集成记录](./notion-sync-ownership-dream-integration-20261007.md#1-optimized-prompt-与实施前门禁)。初次诊断时没有完整排空回执，因此保持开关关闭。用户随后明确授权重启对应服务；以下恢复回执只针对本机正常 Admin 与 Dream，不扩展为远程实例发布证明。正常同步记录保留供复核。

## 验证回执

本轮由专属 `luna_test_runner` 执行隔离技术验证，主执行者已读取原始日志确认结果。所有命令复用已安装依赖与本机 Chrome。

| 工作目录 | 命令 | 退出码 | 关键输出 |
| --- | --- | --- | --- |
| `backend/` | `.venv/bin/python -m pytest tests/test_notion_sync_scheduler.py tests/test_notion_sync_ownership.py tests/test_notion_store.py tests/test_notion_sync_cancellation_edges.py -q` | 0 | 45 passed, 10 subtests passed |
| `frontend/` | `pnpm exec playwright test app/_dream/api/__tests__/resourceConnectorApi.test.ts --reporter=line --workers=1 --output=/tmp/notion-status-validation-20261013-01/api-results-r2` | 0 | 14 passed |
| `frontend/` | `pnpm exec playwright test e2e/notion-settings-save-recovery.spec.ts --grep 'scheduled status\|mounted actor\|missing server due' --reporter=line --workers=1 --output=/tmp/notion-status-validation-20261013-01/browser-results-r4` | 0 | 3 passed；到期、领取失败、恢复、旧后端字段缺失和用户切换；零自动业务写入 |
| `frontend/` | `pnpm exec tsc --noEmit --incremental false` | 0 | 无类型错误，不改 tsbuildinfo |
| `frontend/` | `pnpm exec eslint app/_dream/api/resourceConnectorApi.ts app/_dream/components/dashboard/ConnectorNotionDetailPage.tsx app/_dream/components/dashboard/ConnectorSettingsSection.tsx app/_dream/hooks/useConnectorStatusRefresh.ts` | 0 | 无错误、无警告 |
| 仓库根 | `git diff --check -- backend/notion backend/tests/test_notion_sync_scheduler.py backend/tests/test_notion_sync_ownership.py docs/prd/notion-session docs/design/notion-session docs/exec/notion-scheduled-sync-status-repair-20261013.md frontend/app/_dream/api frontend/app/_dream/components/dashboard/ConnectorSettingsSection.tsx frontend/app/_dream/components/dashboard/ConnectorNotionDetailPage.tsx frontend/app/_dream/hooks/useConnectorStatusRefresh.ts frontend/e2e/notion-settings-save-recovery.spec.ts frontend/e2e/notion-connector-settings.spec.ts` | 0 | 无空白错误 |

文档验证另行记录：八个作用域文档与目录清单的链接、新源文件登记检查通过；当前 PRD 和交互稿合计九张 Mermaid 图，在已安装 Chrome 与 Mermaid 运行时全部完成解析及 SVG 渲染。历史清单中的 `resource-connector-ui.html` 已缺失，`exec_*.md` 是模式条目，均不是本轮新增引用；不把文档检查称为功能验收。

首次 pytest 从仓库根执行时 exit 4，`conftest.py` 无法导入 `tests`，未执行用例；改用现行 `backend/` 工作目录后通过。首次 Mermaid driver 从根目录解析 `playwright` 模块失败，改用已安装前端运行时后通过。这两次属于 harness 前置失败。首次代码检查指出本轮策略 effect 的依赖警告；拆出 desired 标量依赖后，代码检查与相关浏览器用例重新通过。

原始最终日志和首次 harness 失败记录保存于 gitignored `output/notion-scheduled-sync-status-20261013/validation/`。测试创建的 Chrome、Playwright 和 Vite 资源均已关闭；技术验证期间，用户已有 Next、Dream、Admin 及 PostgreSQL 未停止或修改，没有真实业务同步、模型调用、数据库迁移或正常业务数据写入。其结果仅证明源码合同；之后的本机服务恢复与实际后台同步结果由下节单独记录。


## 用户授权后的本机恢复回执

用户明确指示“你来重启对应的服务”。恢复前确认 Dream 后端已停止、8765 没有监听；本机 Admin 3000 由正常仓库的唯一 production Next 实例及 embedded supervisor 承载，当前构建包含旧写入口拒绝逻辑。读取现有 `ink-memory` 数据库并调用 Admin 已有 `check-notion-sync-readiness.ts`，exit 0：精确 capability、actor-lock 实现及权限均 ready，候选执行配置合法；没有 migration 或数据库业务写入。

只追加两项已审阅的 Notion 配置到 Admin `.env.local`。确认 supervisor 身份后向原 PID 55498 发送 SIGTERM，旧实例正常退出；随后在正常 Admin 仓库执行 `pnpm run start:embedded`，保留同一个持久 PostgreSQL 目录与数据库。Admin 于 10:41:51 正常启动，在正常 Dream `backend/` 执行 `.venv/bin/python server.py`，PID 8812，公开 `/api/health` 返回 HTTP 200。前端已有 5173 服务未停止，无数据库迁移、替代 Gateway、影子账户或隔离数据库。

正常 Dream 后台 worker 的第一次扫描已完成真实的轻量索引同步。10:43:19 +08:00 通过正常 Admin connector DTO 只读复核：

| 字段 | 恢复前 | 恢复后 |
| --- | --- | --- |
| 最近成功时间 | 2026-10-07 06:06:27 +08:00 | 2026-10-13 10:43:10 +08:00 |
| 下次计划 | 2026-10-07 06:21:29 +08:00 | 2026-10-13 10:58:10 +08:00 |
| 策略状态 | applied，但计划已到期 | applied，schedule_due=false |
| 策略 revision | 2 | 2 |
| 已选来源 | 7 | 7 |
| 最近错误码 | null | null |

这次正常后台同步由部署中的生产 worker 自动执行，正常数据库保存成功结果；不是注入 fixture 的技术测试，也没有调用模型或执行页面正文下载。精确合同复核 exit 0，Dream 健康读取 HTTP 200，正常候选读取 exit 0。配置/重启和正常结果摘要分别保存于 `output/notion-scheduled-sync-status-20261013/local-restart-receipt.json` 与 `local-sync-observations.jsonl`。两个服务继续运行，不清理正常同步回执；运行位置已从原调试会话切换为本轮启动的正常终端进程。

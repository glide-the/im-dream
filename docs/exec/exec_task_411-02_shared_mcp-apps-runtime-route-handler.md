<!-- [Input] SUO-427 checkout, task_411-02, its independent requirement, Stage 2, DEC-002/004/005, and this run's fresh dirty-tree ledger. -->
<!-- [Output] The sole task_411-02 execution report: implementation, verification, blockers, cleanup, rollback, and Stage 3 handoff evidence. -->
<!-- [Pos] ExecTaskAgent-owned durable report; historical MCP Apps evidence remains read-only and evidence-disabled. -->
<!-- [Sync] 2026-09-05: record the partial implementation, focused passing evidence, and two fail-closed completion blockers. -->
<!-- [Sync] 2026-09-06: rebased current Dream source references from the retired frontend/src tree to frontend/app/_dream. -->

# Exec Report: task_411-02 - Runtime package、薄 Route Handler 与只读 Host

## 1. 执行上下文

- Task ID：`task_411-02`
- Execute Issue：[SUO-427](/SUO/issues/SUO-427)，standard，medium，single assignee `ExecTaskAgent`
- Canonical Task-stage：[SUO-412](/SUO/issues/SUO-412)；Parent：[SUO-373](/SUO/issues/SUO-373)
- 前序：[SUO-419](/SUO/issues/SUO-419)；合同修复：[SUO-425](/SUO/issues/SUO-425)；Stage 同步：[SUO-426](/SUO/issues/SUO-426)
- Task：`docs/task/task_411-02_shared_mcp-apps-runtime-route-handler.md`
- Requirement：`docs/task/TASK-REQUIREMENT-task_411-02_shared_mcp-apps-runtime-route-handler.md`
- Stage：`docs/stage/stage_mcp-apps-system-architecture.md`，仅 Stage 2
- 直接设计：Node Runtime bridge、Client Host communication、DEC-002 iframe、integration、support research、execution checklist §5/§11/§12 与 DEC-005 migration assessment
- 执行 Agent：ExecTaskAgent (`2a7a15fe-2ebb-4dc5-91a8-48ae2bcc5471`)
- 执行 run：`7373efb7-2fff-467d-a9fb-f190c65c33b8`
- Checkout：由本 run harness 预先取得；heartbeat context 复核 single assignee 且无既有 blocker edge

## 2. TASK-REQUIREMENT-FORMAT.md 填充摘要

- 模板路径：`docs/task/TASK-REQUIREMENT-FORMAT.md`；读取顺序为模板 → Issue/Task/独立 requirement → Stage 2 → 直接设计
- 输入 Issue：仅 [SUO-427](/SUO/issues/SUO-427)；输入 Task：仅 `task_411-02`
- 执行目标：建立唯一 server-only Node package、根 App Router 薄委派、Python 最小短时连接投影、Browser 同源只读 Host、ordinary fallback，且 `production_apps_effective=false`
- 验收条件：`R2-graph`—`R2-gate`
- 允许/禁止文件：严格使用 Task §6.1/§6.3 精确闭集；lock、legacy `app/_dream/server`、schema/Gateway、设计/Issue/Stage/Task、Phase 2/3 与 production enablement 禁止
- 测试：Node/Python/frontend focused、official protocol、Chrome、closed-set/Markdown/README/secret；生成物只进本 run scratch
- Fresh model input：上述字段、dirty ledger 与 No-Go 均已填入；当前 Codex 执行模型据此生成本报告 §3 的执行任务后才开始实现

## 3. 模型生成的执行任务

- 新建 `frontend/packages/mcp-apps-runtime/**` 唯一 Runtime owner，显式 `server-only`，不反向导入 root/React/DOM
- 以 process-global composition root、完整 connection key、single-flight acquire、reference lease、revision revalidation 与 teardown 管理标准 MCP Client
- 让唯一 `[serverRef]/route.ts` 只导出 Node GET/POST/DELETE 薄委派，并在 Runtime composition/upstream 前拒绝 preview/origin/query/auth/serverRef 异常
- 复用 managed MCP repository/snapshot loader，增加 service-authenticated、单 Server、短时、最小披露 Python view；解密前校验 ownership/scope/enabled/revision/catalog
- 在 ordinary tool result 下条件挂载同源 Browser Client/标准 AppBridge，两层 sandbox 执行 server-owned 零权限 policy；失败仍保留 ordinary result
- 对缺失 official artifact 与不完整 Chat result identity 严格 No-Go，不使用自建 Server、旧 evidence、联网安装或越权修改替代

## 4. Dirty tree 与归属证据

- 首次业务写入前保存 `git status --porcelain=v2 --untracked-files=all`、tracked diff、untracked inventory、逐路径 ledger 与 allowed-target SHA-256 到 `$PAPERCLIP_RUN_SCRATCH_DIR`
- 基线：1125 dirty paths；906 个 `frontend/.next/**` 为 `pre-existing/generated`、只读、`evidence-disabled`；50 个历史 MCP Apps/旧 Exec/evidence/legacy path 为 `pre-existing/historical`、只读、`evidence-disabled`
- 25 个现存 target 保存 SHA-256 后才接续；144 个其他路径保持 `pre-existing/read-only`
- 最终状态对比：1150 dirty paths；新增 25、删除 0。新增 25 个路径全部属于 Task §6.1/§6.3；无新越界路径
- 本 run 修改的基线目标 hash 均能由 `pre-write-allowed-sha256.txt` 对照；未修改的既有目标（包括 sandbox route、`ToolMessagePart`/result parser、Python router/snapshot）按原 hash 保留并仅作 reviewed/adopted input
- `unknown/conflict`：0；未 reset、restore、clean、宽格式化或覆盖其他 owner 文件

## 5. 实现与文件变更

### 5.1 本 run 创建

| 路径 | 说明 |
|---|---|
| `frontend/packages/.folder.md` | 登记唯一 sibling package owner |
| `frontend/packages/mcp-apps-runtime/package.json`、`tsconfig.json`、`tsconfig.integration.json`、`.folder.md` | 私有 server-only package、严格 focused/integration type boundary；不 install/relock |
| `frontend/packages/mcp-apps-runtime/src/index.ts`、`runtime.ts` | 公共 `server-only` entry 与 process-global composition root；preview-only、production-off |
| `frontend/packages/mcp-apps-runtime/src/contracts.ts`、`config-provider.ts`、`sdk-connector.ts` | 严格 DTO/selector/parser、Python service boundary 与标准 SDK upstream connector |
| `frontend/packages/mcp-apps-runtime/src/persistent-connector-manager.ts` | actor/workspace/serverId/serverRef/config/credential revision key、并发 single-flight、lease/refcount/invalidation/teardown |
| `frontend/packages/mcp-apps-runtime/src/http-adapter.ts` | 标准 stateful Streamable HTTP GET/POST/DELETE session；tools/resources allowlist；页面 `tools/call` 不触发 upstream |
| `frontend/packages/mcp-apps-runtime/src/*.test.ts` | route pre-reject、manager、session/scope、zero-upstream-call 与 teardown focused tests |
| `frontend/e2e/mcp-apps/.folder.md` | 官方 artifact、Chrome 与 run-owned output 的 E2E 父目录契约 |
| `docs/exec/exec_task_411-02_shared_mcp-apps-runtime-route-handler.md` | 唯一正式报告 |

### 5.2 本 run 最小修改

| 路径 | 说明 |
|---|---|
| `frontend/app/api/mcp-apps/[serverRef]/route.ts` | 从 legacy owner 切换到 canonical package，保持固定 Node GET/POST/DELETE 薄委派 |
| `frontend/app/api/mcp-apps/phase1-status/route.ts` | 发布不可变、零权限、无敏感值的 server-owned Host policy；production 始终 false |
| `frontend/app/_dream/components/chat/mcp-apps/ImMcpAppHostAdapter.tsx`、`McpAppReadOnlyPanel.tsx` | 同源 Client、标准 AppBridge/transport、policy revision、outer sandbox、metadata/CSP/permission 校验与 teardown/fallback |
| `backend/claude_mcp/contracts.py`、`service.py` | 为 connection key 增加 opaque `serverId`；保持单 Server、短时、最小披露、解密前拒绝 |
| `backend/tests/mcp_apps_phase1/test_connection_view.py` | 官方 descriptor identity、serverId、pre-decryption/redaction/production-off assertions |
| `README.md`、`README.zh.md` | 同结构记录唯一 package/route/Python/Browser/official fail-closed/production-off 与相同 focused commands |
| §6.3 精确 folder contracts、`docs/exec/.folder.md` | 更新受影响 architecture/file table/sync；未刷新无关历史 |

### 5.3 既有目标的审查接续

- `backend/claude_mcp/runtime_snapshot.py` 已有单 Server config loader；本 run hash 未改，regression 通过
- `backend/routers/claude_mcp.py` 已有双身份 Node-only endpoints；本 run hash 未改，router regression 通过
- `frontend/app/mcp-apps-sandbox/route.ts` 已有两层 iframe proxy/header policy；本 run hash 未改
- `frontend/app/_dream/components/chat/ToolMessagePart.tsx` 与 `mcp-apps/result.ts`/test 已有 ordinary-result 条件挂载与完整结果 parser；本 run hash 未改并通过 focused lint/type/test
- 旧 `frontend/e2e/mcp-apps/phase-1/phase1-readonly-loop.spec.ts` 未修改、未运行、`evidence-disabled`：它仍导入 self-built fixture 且写历史 `docs/exec/mcp-apps/**`，不符合当前合同

## 6. 测试与验证

| 验收 | 结论 | 真实命令、退出码与关键 evidence | 未完成 owner/action |
|---|---|---|---|
| `R2-graph` | focused pass / standalone pending | `frontend/node_modules/.bin/tsc --noEmit -p frontend/packages/mcp-apps-runtime/tsconfig.json` → 0；integration tsconfig → 0；scan 仅 route import `@ink-dream/mcp-apps-runtime`，entry 有 `import 'server-only'`，Runtime 无 root/React/DOM 反向 import，Browser 无 Runtime/provider secret import | 411-03 owner：安装/重锁后做真实 workspace link 与 fresh standalone trace；既有 `.next` 禁用 |
| `R2-route` | focused pass | Node tests → 0；8/8 中覆盖 disabled/origin/query/auth/serverRef pre-composition rejection，以及标准 adapter initialize/session/GET/POST/DELETE | official integration 随 `R2-official` 阻塞 |
| `R2-manager` | focused pass | Node tests → 0；同 key 并发只 connect 1 次、两 leases、末 lease close，revision change/invalidate/scope mismatch 均关闭或拒绝旧 session | restart/断线 real trace 随 official loop 阻塞 |
| `R2-python` | pass | `PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python -m pytest backend/tests/mcp_apps_phase1 -q` → 0，6 passed；在 `backend/` 跑四个既有 Claude MCP regression → 0，27 passed | 无 |
| `R2-official` | **No-Go / blocked** | `npm view @modelcontextprotocol/server-basic-vanillajs@1.7.5 dist --offline --json` → 1，`ENOTCACHED`；repo 无锁定 tarball/artifact | CEOOrchestrator / Integration owner：提供 task 锁定 SRI 的已验证只读 offline cache，再 fresh retry；不得联网或自建替代 |
| `R2-host` | component focused pass / E2E blocked | exact ESLint → 0；integration typecheck → 0；result parser tests → 0，2 passed；同源 URL、server-owned zero-permission policy、ordinary fallback/teardown 在代码边界成立 | CEOOrchestrator / Chat owner：明确可持久化的 stable `serverRef`/resource identity 投影；Integration owner：official Chrome loop |
| `R2-negative` | Node pass / page probe blocked | Node adapter test 对页面 `tools/call` 返回 read-only error且 upstream call count=0；unknown method 由标准 Server 拒绝；Host capability 无 open-link/window.im | official Browser 页面四类反向 probe 随 artifact 与 Chat identity 阻塞 |
| `R2-gate` | focused partial | manager release/invalidate/revision/closeAll、Host unmount/result-policy dependency teardown、resource failure fallback 均有 unit/static evidence；`PRODUCTION_APPS_EFFECTIVE=false` 与 Browser status false 扫描通过 | refresh/reopen/Thread switch/disable/restart/断线全矩阵需 official Chrome loop |

补充命令：

- `pnpm --dir frontend exec eslint -- app/_dream/components/chat/mcp-apps app/_dream/components/chat/ToolMessagePart.tsx` → exit 0
- `frontend/node_modules/.bin/tsc --noEmit -p frontend/packages/mcp-apps-runtime/tsconfig.integration.json` → exit 0
- `node --experimental-strip-types --test frontend/app/_dream/components/chat/mcp-apps/result.test.ts` → exit 0，2 passed
- `git diff --check` → exit 0
- Markdown/link inventory（20 个本轮维护文档）→ exit 0，`MARKDOWN_INVENTORY_OK files=20`
- route/owner/secret/legacy static scan → exit 0；唯一动态 `[serverRef]` route，Browser 无 Node provider/env/credential import，legacy owner 无 active import
- `test ! -e frontend/pnpm-lock.yaml` → exit 0，`PNPM_LOCK_ABSENT`
- 全 root `pnpm --dir frontend exec tsc --noEmit --incremental false` 曾返回 exit 2：canonical package 尚未由 411-03 workspace install/link，另有既有 ChatMarkdown/ThreadImageCard/png-stitch 与 legacy `app/_dream/server` 错误；本 run 修正自身 Host tuple error后，focused package+root integration typecheck 均为 exit 0
- Playwright 指定命令未运行：当前 spec 会使用禁止的 self-built fixture、既有 `.next` 和历史 screenshot 路径；运行会制造无效证据并触碰非本轮 owner

## 7. 风险、阻塞与上游动作

1. **官方 artifact 缺失**：[SUO-428](/SUO/issues/SUO-428) 跟踪。无法核对 SRI/provenance、stateless `/mcp`、`get-time` descriptor、`ui://get-time/mcp-app.html`、`text/html;profile=mcp-app`、同一 time payload 或启动/停止回执。恢复条件是上游提供精确已验证 offline artifact/cache 与 run-owned harness 输入。
2. **Chat 稳定身份投影缺口**：[SUO-429](/SUO/issues/SUO-429) 跟踪。当前普通 Claude Agent tool event/persistence 可确认的字段为 toolCallId/toolName/input/output；仓库搜索未发现既有 serverRef owner。官方 Server 的标准 `CallToolResult` 也不应自行携带 IM 私有 serverRef。Task 禁止本 agent 越权修改 Claude Agent transport/service 或猜测字段，因此 Host parser 虽安全 fail closed，但真实普通结果无法证明可挂载。恢复条件是 Chat owner 明确/实现允许闭集内可消费的 stable result identity，或上游正式扩展授权闭集。
3. `frontend/pnpm-lock.yaml` 仍缺失且只读；`frontend/package-lock.json` 保持 pre-existing dirty/read-only。本 task 不 install/relock，最终 package graph/standalone 属于 411-03。
4. Stage 3 继续锁定；本报告不得被解释为 Phase 1 Go 或 production Apps enablement。

## 8. 完成状态与执行完成报告

- [x] checkout、single assignee、fresh requirement fill、model-generated task
- [x] canonical package/route/manager/Python/Host 的非阻塞实现闭集
- [x] focused Node/Python/frontend/static/maintenance 验证
- [x] 变更、dirty ledger、旧 evidence 禁用、回滚与 cleanup 回执
- [ ] exact official artifact/read-only loop/Chrome lifecycle evidence
- [ ] stable Chat result identity 的生产来源
- [ ] 全部 `R2-graph`—`R2-gate` 验收完成
- [ ] 可进入 review/audit 或交接 411-03

最终状态：**blocked（部分实现已落地，禁止标记 done）**。两个阻断解除并重新确认 checkout/hash 后才可 retry；不得自行解锁 Stage 3。

## 9. Cleanup 与回滚建议

- 已删除本轮精确 Python `__pycache__/*.pyc`，验证目录不存在；最终 Python 验证使用 `PYTHONDONTWRITEBYTECODE=1`
- offline npm preflight 曾产生 `/Users/dmeck/.npm/_logs/2026-09-05T13_28_28_730Z-debug-0.log`；已精确删除并验证不存在
- 本 run 未启动 official demo、Next、Vite、Chrome、监听端口或持久数据库；无需停止进程/清理端口。scratch 由 Paperclip run owner 管理，未触碰其他 run/用户资源
- 回滚顺序：保持 `production_apps_effective=false` → 移除本 task Host/Browser Client 挂载 → `closeMcpAppsRuntime()` 拒绝旧 session并回收 connector → 移除 canonical package/route/Python projection 的本 task 增量 → 保留 ordinary MCP/Chat/Python/数据库/用户数据
- 不得以回滚恢复 legacy `frontend/app/_dream/server/mcp-apps/**`、nested Next、自建 AppServer、旧 evidence 或 production flag

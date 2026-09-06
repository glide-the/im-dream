<!-- [输入] 411-01/02 当前实现、唯一 pnpm workspace、DEC-002/004/005 和 Phase 0 harness。 -->
<!-- [输出] 最终 pnpm lock、根 build/start/standalone、同 lock P0-01/P0-04/P0-08 与回滚证据。 -->
<!-- [定位] N1 release/P0 集成工作项；不启用 production Apps。 -->
<!-- [同步] 2026-09-06：按唯一 lock、当前候选和 P0 证据重构。 -->

# task_411-03：pnpm、root standalone 与 Phase 0 重验

配套 requirement：[TASK-REQUIREMENT-task_411-03_shared_pnpm-standalone-phase0-gate.md](./TASK-REQUIREMENT-task_411-03_shared_pnpm-standalone-phase0-gate.md)

## 1. 目标

使 `frontend/pnpm-workspace.yaml` 和 `frontend/pnpm-lock.yaml` 成为唯一 Node 依赖事实源；验证根 build/start/standalone 收入 Runtime production dependencies；在同一 lock、源码、Browser 和入口上重跑 P0-01→P0-04→P0-08。

## 2. 技术依赖

- 411-01 根 workspace/App Router/Web Shell 和业务回归。
- 411-02 Runtime package、薄 Route Handler、server-only graph、Python/result identity/Host/official read-only contract。
- 本机兼容 Chrome、Phase 0 harness 和官方离线 artifact。
- 可验证的 Vite image 与当前 Next image 回滚路径。

## 3. 实现范围

- 根 pnpm workspace/lock、package scripts 和旧 npm lock 退役。
- 根 Docker/Compose/本机启动与 standalone tracing 的最小修正。
- Phase 0 harness、P0 证据索引、唯一 P0-08 decision 和相关 docs/`.folder.md`。
- 不新增 Phase 2/3、数据库 schema、Gateway、外部 Server 配置或 production Apps。

## 4. 验收

| ID | 验收 |
|---|---|
| R3-lock | frozen install 使用唯一 pnpm lock；无 package-lock、第二 lock 或隐式在线补包。 |
| R3-root | 从 `frontend/` 无位置参数执行 dev/build/start。 |
| R3-standalone | `frontend/.next/standalone/server.js` 包含 Runtime package 和生产依赖，可在隔离环境启动 health 与 MCP route。 |
| R3-p0-01 | 记录当前依赖树、lock digest、SDK/renderer/AppBridge/Playwright 版本。 |
| R3-p0-04 | 当前 Chrome 验证 permissions、双 iframe、CSP/Permissions-Policy、来源拒绝、teardown 和 no-replay。 |
| R3-p0-08 | 同一指纹的 P0-02—P0-07 有效，唯一 decision 原位为 Go/No-Go。 |
| R3-regression | auth/OAuth/SSE/cancel/resume/voice/runtime config/普通 Chat 回归。 |
| R3-rollback | 当前 Next image 与 Vite image 的回滚命令、digest、smoke 和清理可复核。 |
| R3-production-off | 所有验证前后 `production_apps_effective=false`。 |

旧 npm lock、旧 P0 Go、旧 Chrome trace、nested standalone 和 self-built Server 不能作为当前验收输入。

## 5. 回滚

依赖或 P0 失败时保持 No-Go 和 production Apps 关闭。回滚到已验证 Next image或 Vite image，不恢复嵌套 Next、legacy Runtime、第二 lock 或自建 Server。只清理本轮具名 container/network/process/port/scratch。

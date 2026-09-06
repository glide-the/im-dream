<!-- [输入] DEC-005、现有 Dream SPA、根 frontend 结构和 Next.js 迁移评估。 -->
<!-- [输出] 根 workspace、单一 App Router、client-only Web Shell、Vite 退出和业务回归合同。 -->
<!-- [定位] 已完成 N1 平台迁移合同；保留范围、验收与回滚边界。 -->
<!-- [同步] 2026-09-06：依据 54f3bbe5 与 N1 回执，标记根 Next/pnpm/app/_dream 迁移已完成。 -->

# task_411-01：根 Web Shell 与 Vite 退出

配套 requirement：[TASK-REQUIREMENT-task_411-01_frontend_root-web-shell-vite-exit.md](./TASK-REQUIREMENT-task_411-01_frontend_root-web-shell-vite-exit.md)

## 当前状态

本工作项已完成：`frontend/` 是唯一 pnpm workspace/Web/Next.js 16 root，`frontend/app/**` 是唯一 App Router，`frontend/app/_dream/**` 是唯一 Dream 应用源码 owner。当前验收见 [N1 Build、Health 与 Rollback](../exec/mcp-apps/phase-1/n1-build-health-rollback.md)；Vite 只允许存在于已记录的不可变回滚镜像或隔离测试 harness，不是当前开发/构建/生产入口。

## 1. 目标

将 `frontend/` 收敛为唯一 workspace、Web package 和 Next root；`frontend/app/**` 收敛为唯一 App Router；用 client-only compatibility shell 承载现有 Dream SPA，并在行为回归通过后退出 Vite 默认生产入口。

## 2. 边界

本工作项不实现 Node MCP Runtime、Python Apps 配置、Host、P0 重验、最终 pnpm lock 或 production Apps。`frontend/pnpm-lock.yaml` 的最终重锁和 digest 由 411-03 统一完成。

不得改变认证、OAuth、Python API、Agent SSE、cancel/resume、语音 WebSocket、运行时配置、动态资源或普通 Chat 语义。

## 3. 实现范围

- 根 `frontend/package.json`、`pnpm-workspace.yaml`、Next config、tsconfig、next-env 与 App Router。
- client-only shell、根 layout/page、health 和现有公开 route 迁移。
- 现有 SPA route-level 文件按 reuse-first 迁入私有 `app/_dream/views/**`。
- Docker、Compose、本机启动脚本和双语 README 中与根 Next 命令直接相关的最小更新。
- 删除嵌套 Next 配置和 Vite 默认生产入口，但保留可验证的 Vite image 回滚制品。

## 4. N1 验收

| ID | 验收 |
|---|---|
| N1-01 | `frontend/` 根只有一个 workspace/package/Next root；不存在 `frontend/app/app/**`。 |
| N1-02 | server render 不访问 `window`、`document`、localStorage 或 AudioContext。 |
| N1-03 | 静态/参数 URL、刷新、JWT auth、OAuth callback、Python API、SSE、cancel/resume、voice、runtime config 和普通 Chat 回归。 |
| N1-04 | health、MCP Apps 和 sandbox route 只由根 App Router 拥有；本工作项不创建 Runtime 第二实现。 |
| N1-05 | 根 dev/build/start 可运行；完整 standalone tracing 留给 411-03。 |
| N1-RB | immutable Vite image 可隔离启动和回读；回滚不恢复嵌套 Next。 |

## 5. 证据

记录根 tree、route manifest、client boundary 扫描、dev/build/start、focused tests、Chrome 用户旅程、Docker/Vite image digest、工作树差异和清理结果。未运行项必须保留命令和具体原因。

## 6. 回滚

切回已验证 Vite image；不恢复嵌套 Next、legacy Runtime 或第二 lock。数据库、用户数据、普通 MCP/Chat 和公开状态 `productionAppsEffective=false` 不变。

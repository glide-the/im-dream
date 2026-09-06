<!-- [输入] task_302 旧自建 AppServer 路线及其 Phase 1 验证回执。 -->
<!-- [输出] 旧 N1/C1/S1/M1/H1 实现、成功、失败和废止原因的历史记录。 -->
<!-- [范围] 只作历史技术证据；DEC-004/005 已使旧目录、自建 Server、npm lock 与 P1 结论失效。 -->
<!-- [同步] 2026-09-06：保留真实命令回执，并链接已完成的当前 canonical 候选验收。 -->

# task_302 Phase 1 历史执行证据

## 1. 适用范围与废止原因

本报告记录 2026-09-05 旧候选的 provider-free、自建 AppServer 只读闭环。该候选曾实现 Next→Node manager→AppServer→Browser Host，并留下 N1/C1/S1/M1/H1 证据。

其当前结论已失效：

- DEC-004 要求原样使用官方 `@modelcontextprotocol/server-basic-vanillajs@1.7.5`，旧 repo-owned/self-built fixture 不能作为 S1。
- DEC-005 要求 `frontend/` 为唯一 pnpm workspace、`frontend/app/**` 为唯一 App Router、`frontend/packages/mcp-apps-runtime/**` 为唯一 Node Runtime。
- 旧 `frontend/app/_dream/server/mcp-apps/**`、旧 npm lock、旧独立 Next project 和旧 P1 `Go` 不能作为当前实现或发布依据。

## 2. 历史实现事实

旧候选包含：

- Python 单 Server 静态/短时建连投影与解密前 identity/revision/enabled 校验；
- 进程级 connector manager、标准 Streamable HTTP GET/POST/DELETE、opaque session、连接隔离、allowlist、逐请求重验和 teardown；
- `ToolMessagePart` 普通结果与 Apps Host 同位置展示；
- Browser 只访问同源 endpoint，页面 `tools/call` 被拒绝；
- `AppBridge` / `PostMessageTransport` Host、独立 iframe、CSP/Permissions-Policy 和生命周期清理；
- `production_apps_effective=false`。

这些事实可帮助回归，但不能替代当前 canonical tree、官方制品和 pnpm lock 上的重新实现与验证。

## 3. 实际命令与结果

| 命令 / 检查 | Exit | 关键结果 |
|---|---:|---|
| `node --test backend/tests/fixtures/mcp_apps_phase1/*.test.mjs` | 0 | 2 passed。 |
| `node --experimental-strip-types --test src/server/mcp-apps/*.test.ts src/components/chat/mcp-apps/result.test.ts`（`frontend/`） | 0 | 9 passed。 |
| `PYTHONPATH=backend ./.venv/bin/python -m pytest backend/tests/test_claude_mcp_runtime_snapshot.py backend/tests/test_claude_mcp_repository.py backend/tests/test_claude_mcp_router.py backend/tests/mcp_apps_phase1 -q` | 0 | 24 passed。 |
| focused ESLint（`frontend/`） | 0 | no findings。 |
| `npm run build`（`frontend/`） | 0 | Next 16.1.6 编译完成，5 个动态路由和 not-found 生成。 |
| standalone health/compat/sandbox probe（具名端口 43127） | 0 | 95 ms ready；health Apps false；compat 200；CSP/Permissions-Policy 存在。 |
| `npm exec vite build`（`frontend/`） | 0 | 3,092 modules，产生 rollback bundle。 |
| `npm exec playwright test e2e/mcp-apps/phase-1 --reporter=line --workers=1` | 0 | installed Chrome，`1 passed in 4.7s`。 |
| 本地部署脚本 Next/Vite build/start dry-run | 0 | 命令选择符合旧候选，未创建远程资源。 |
| `git diff --check` | 0 | 无空白错误。 |

## 4. 保留的失败事实

- Backend 原命令未注入 repository import root 时在 collection 阶段失败；增加 `PYTHONPATH=backend` 后相同测试目标 24 项通过。
- 从 `backend/` 使用 `./.venv/bin/python` 时解释器路径不存在；改用 repo-root `.venv` 后通过。
- 首次 Chrome harness 因测试 StrictMode remount 产生 2 次 resource read；移除测试 harness 的 StrictMode 后通过，首次 `tools/call` 始终为 1。
- 从仓库根运行 `npm --prefix frontend exec vite build` 时 npm 保留错误 cwd，Vite 找不到 `index.html`；从 `frontend/` 运行实际 rollback 命令后通过。
- `npm run build:vite` 的 TypeScript 前置检查仍命中范围外既有 `@ts-expect-error` 漂移；实际 Vite bundler 与 deploy dry-run 通过。
- 未执行远程/Docker 部署、真实业务数据库写入、外部 provider 或 production Apps 切换。

## 5. 历史验收与当前含义

| 范围 | 旧候选结果 | 当前含义 |
|---|---|---|
| N1-01—N1-05 | pass | 旧目录/构建证据；当前 root pnpm/standalone 必须重跑。 |
| C1-01—C1-06 | pass | 可作为 Python 安全回归输入；当前投影仍需在新 graph 验证。 |
| S1-01 | pass | 自建 fixture 路线已废止，不能作为当前 S1。 |
| M1-01—M1-08 | pass | 旧 `src/server` 路径已废止，当前 Runtime package 必须重建证据。 |
| H1-01—H1-08 | pass | 旧 Host/Browser 证据；当前 result identity、官方制品和 Browser 入口必须重验。 |
| P1 | historical Go | 只适用于旧 preview；不能授权当前 Phase 2 或生产发布。 |

## 6. 后续解决与当前边界

当前 canonical 候选已在同一 pnpm lock、根 Next、官方 AppServer 制品和源码指纹上完成 N1/C1/S1/M1/H1 provider-free 验收，见 [Phase 1 当前证据索引](mcp-apps/phase-1/index.md) 与 [当前候选统一回执](mcp-apps/current-candidate-validation.md)。这些回执覆盖 root build/standalone、Runtime contracts、官方制品、Browser Host、server-owned result identity、sandbox/lifecycle 和 teardown。

该结果是技术 preview，不是公开应用或生产验收。真实账号、真实外部 MCP Server、真实 OAuth/权限和生产运维回滚尚未验收；`productionAppsEffective=false`，Production 仍为 `No-Go`。

## 7. 回滚

当前实现不得恢复旧自建 AppServer、旧 `frontend/app/_dream/server/mcp-apps/**`、第二 lock 或旧 Next 项目。历史资源若仍存在，只能由明确的技术清理变更删除；普通工具结果、Chat、Python managed MCP 和 production-off 安全边界继续保留。

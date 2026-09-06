<!-- [输入] task_302、旧 Phase 0 结论与旧自建 AppServer 候选。 -->
<!-- [输出] 旧 Phase 1 候选使用的 N1/C1/S1/M1/H1 技术输入与验证边界。 -->
<!-- [范围] 历史执行输入；DEC-004/005 后不得作为当前实现或发布结论。 -->
<!-- [同步] 2026-09-06：保留旧候选合同、失败语义与当前重验要求。 -->

# task_302 历史执行输入

## 1. 旧候选目标

旧候选尝试完成 Next→Node manager→repo-owned AppServer→Browser Host 的 provider-free 只读闭环，覆盖：

- N1：Next shell、Node composition root、build/start/standalone 和 Vite rollback；
- C1：Python 静态/单 Server 建连投影、解密前 identity/revision/enabled 校验；
- S1：repo-owned deterministic AppServer fixture；
- M1：进程级 connector manager、标准 MCP endpoint、连接隔离、allowlist、逐请求重验与 teardown；
- H1：完整结果、普通 fallback、同源 Browser Client、Host adapter、iframe policy 与生命周期；
- 全程 `production_apps_effective=false`。

## 2. 旧候选允许范围

旧执行输入曾允许：

- `backend/tests/fixtures/mcp_apps_phase1/**`
- `backend/tests/mcp_apps_phase1/**`
- `backend/claude_mcp/**` 中列明的最小投影文件
- `backend/routers/claude_mcp.py`
- 旧 `frontend/app/**` 与 Next 配置
- 旧 `frontend/app/_dream/server/mcp-apps/**`
- `frontend/app/_dream/components/chat/mcp-apps/**` 和精确 Chat 集成文件
- `frontend/e2e/mcp-apps/phase-1/**`
- 精确 package/deploy 增量和本目录证据

禁止数据库 schema/migration/runtime DDL、Browser secret、外部 provider、独立 Gateway/MQ、真实生产连接和普通 Agent/Thread/Runner/EventBus/SSE/voice 语义变化。

## 3. 旧验收

| 范围 | 条件 |
|---|---|
| N1-01—N1-05 | Next shell、Client/Server boundary、现有 ingress、composition root、standalone 和 rollback。 |
| C1-01—C1-06 | 最小披露、服务身份、scope/revision/expiry、解密前拒绝、secret 不泄漏。 |
| S1-01 | deterministic descriptor/resource/result、计数、teardown 和 ordinary fallback。 |
| M1-01—M1-08 | 标准 endpoint/session、进程级复用、隔离、allowlist、旧 revision 失效、页面 call 拒绝。 |
| H1-01—H1-08 | 完整结果、原位置挂载、同源网络、resource proxy、iframe 安全、fallback 和 teardown。 |
| P1 | 标准 Client 与 Browser→Node→Manager→同一 Server 闭环；production Apps 关闭。 |

## 4. 旧验证命令

- Backend projection 与普通 managed MCP regression tests；
- Node AppServer/manager/result focused tests；
- changed-file ESLint；
- Next build/start/standalone/health；
- Vite rollback bundle 与本地部署 dry-run；
- installed Chrome 单 worker Playwright；
- secret scan、path allowlist、`git diff --check` 和具名资源清理。

原命令无法运行时必须保留原始失败；修正 cwd、import root 或解释器路径后的命令只证明实际覆盖的目标。

## 5. 当前适用性

DEC-004 已废止自建 AppServer，DEC-005 已废止旧 Runtime 目录和 npm lock。因此当前实施必须使用：

- [task_411-01](../../../task/task_411-01_frontend_root-web-shell-vite-exit.md) 的根 Web/Next tree；
- [task_411-02](../../../task/task_411-02_shared_mcp-apps-runtime-route-handler.md) 的 sibling Runtime、C1/M1/H1 与 result identity；
- [task_411-03](../../../task/task_411-03_shared_pnpm-standalone-phase0-gate.md) 的唯一 pnpm lock、standalone 和 P0 重验；
- [task_434](../../../task/task_434_shared_official-appserver-offline-supply.md) 的官方离线制品。

旧输入和旧 `Go` 只作历史对照，不能启动 Phase 2 或 production Apps。

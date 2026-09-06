<!-- [输入] task_301、Phase 0 设计合同与当前 pnpm lock 候选。 -->
<!-- [输出] 当前候选使用的技术输入、写入边界、验收和测试。 -->
<!-- [范围] Provider-free Phase 0 执行输入；不构成 production Apps 许可。 -->
<!-- [同步] 2026-09-06：以当前 pnpm/source/Chrome 指纹完成 P0 合同。 -->

# task_301 当前执行输入

## 1. 目标

在隔离、provider-free 的当前 pnpm 候选上验证 P0-01—P0-08：

- 固定 MCP Apps、MCP SDK、Host 与 Browser 测试依赖；
- Browser 经 IM endpoint 完成 initialize、tools/list 和 resources/read；
- 从同一次完整 `CallToolResult` 挂载 App，首次工具调用不重放；
- 验证两层 iframe、CSP、Permissions-Policy、来源/schema、权限正反向 probe 与 teardown；
- 验证 Node locality、fresh session 和 Chat save/refresh 五字段；
- 生成唯一 `Go|No-Go`，并保持 `production_apps_effective=false`。

## 2. 输入与边界

输入包括：

- [task_301](../../../task/task_301_shared_mcp-apps-phase0-protocol-security-poc.md)；
- [对应 requirement](../../../task/TASK-REQUIREMENT-task_301_shared_mcp-apps-phase0-protocol-security-poc.md)；
- [技术执行计划](../../../stage/stage_mcp-apps-system-architecture.md)；
- named fixture、Browser harness、现有 Chat save/list/hydration 入口和隔离证据目录。

允许改动当前 pnpm manifest/lock、`frontend/e2e/mcp-apps/phase-0/**`、`backend/tests/{fixtures/,}mcp_apps_phase0/**` 和本 Phase 0 证据。禁止数据库 schema/migration/runtime DDL、真实账号/凭证/连接、部署和普通 MCP/Agent/Thread/Runner/EventBus/SSE/voice 语义变更。

## 3. 验收

| ID | 条件 |
|---|---|
| P0-01 | 精确版本、可复现 lock、无 `latest`。 |
| P0-02 | Browser 只经 IM endpoint 完成标准 MCP 只读方法。 |
| P0-03 | resource URI 正确解析，首次工具调用计数等于 1。 |
| P0-04 | Chrome 中 CSP/origin/source/schema/permissions/teardown 全部有正反向证据。 |
| P0-05 | stdio、localhost、Node 可达 HTTP/SSE 有实测 locality 结论。 |
| P0-06 | fresh Node session 不依赖 Claude Agent 原物理连接。 |
| P0-07 | refresh 保留 `serverRef`、tool、`toolCallId`、input、完整 result，无 schema 变化。 |
| P0-08 | 同一源码、lock 和 Browser 指纹下汇总唯一结论；任一安全证据缺失即 No-Go。 |

## 4. 验证

- 依赖树与 lock digest；
- provider-free Backend focused tests；
- installed Chrome 的单 worker Playwright；
- secret/路径/closed-set 扫描；
- `git diff --check`；
- 具名进程、端口和临时目录清理。

Browser 无法启动属于 harness 前置失败，不能据此判断产品通过或失败。

## 5. 当前适用性

该输入已在 `frontend/pnpm-lock.yaml`、当前 Browser 入口、当前源码和本机 Chrome 上执行。P0-08=`Go` 仅允许下游技术验收，production Apps 仍关闭。

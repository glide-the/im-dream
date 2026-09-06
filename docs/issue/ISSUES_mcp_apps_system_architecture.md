<!-- [输入] DEC-002/004/005、系统架构执行清单、技术执行计划和对应 task/requirement。 -->
<!-- [输出] MCP Apps 已实现工作内容、技术依赖、现行证据与生产缺口索引。 -->
<!-- [定位] MCP Apps 当前技术工作项、证据与回滚索引。 -->
<!-- [同步] 2026-09-06：依据 54f3bbe5 与当前回执，将失效派工状态改为实现/证据/生产缺口语义。 -->

# MCP Apps 技术工作项索引

## 1. 来源

- [系统架构执行清单](../design/claude-agent/mcp-apps-system-architecture-execution-checklist.md)
- [Phase 0→3 技术执行计划](../stage/stage_mcp-apps-system-architecture.md)
- [Next.js 迁移评估](../design/claude-agent/dream-frontend-node-framework-migration-assessment.md)
- [Node MCP Runtime 设计](../design/claude-agent/mcp-apps-node-runtime-bridge.md)
- [Browser/Host 通信设计](../design/claude-agent/mcp-apps-client-host-communication.md)
- [iframe 与权限设计](../design/claude-agent/mcp-apps-iframe-interaction.md)

## 2. 不可变边界

- `frontend/` 是唯一 workspace、Web package 和 Next root。
- `frontend/app/**` 是唯一 App Router。
- `frontend/packages/mcp-apps-runtime/**` 是唯一 Node MCP Runtime。
- 依赖方向固定为 `frontend/app/api/** → @ink-dream/mcp-apps-runtime`。
- Browser 只连接 IM 同源 endpoint，不获得上游 URL、headers、env、credential 或完整 snapshot。
- Node Runtime 持有进程级 `PersistentConnectorManager`；不得按 HTTP 请求创建第二连接管理器。
- Python 只提供经过鉴权、限定 actor/workspace/Server/revision/expiry 的最小配置投影。
- 首次工具调用由 Claude Agent Runtime 执行一次；Browser 渲染、refresh 和 reconnect 不重放。
- Phase 1 页面 `tools/call` 全部拒绝；高风险写工具在独立授权合同存在前继续拒绝。
- 全部实施和验证期间公开状态保持 `productionAppsEffective=false`。

## 3. 工作内容与当前证据

| 工作项 | 已落地内容 | 当前证据 | 适用边界 |
|---|---|---|---|
| MCPAPPS-411-01 | `frontend/` 是唯一 pnpm/Web/Next 16 root，`frontend/app/**` 是唯一 App Router，`frontend/app/_dream/**` 是唯一 Dream 应用源码树；Vite 只保留为具名不可变回滚镜像和隔离 harness 工具。 | [N1 回执](../exec/mcp-apps/phase-1/n1-build-health-rollback.md) | 根 Next build/start/standalone 已通过；不表示生产 Apps 启用。 |
| MCPAPPS-411-02 | `frontend/packages/mcp-apps-runtime/src/**` 是合法、独立、server-only 的唯一 Node Runtime owner；根 Route Handler 薄委派，Python 只投影最小配置，Chat/Host 保留 ordinary fallback。 | [C1/M1](../exec/mcp-apps/phase-1/c1-m1-contracts.md)、[H1](../exec/mcp-apps/phase-1/h1-browser.md) | provider-free 技术 preview 已验收；未使用真实外部 Server/credential。 |
| MCPAPPS-411-03 | 唯一 `frontend/pnpm-lock.yaml`、frozen install、root standalone 和同 lock P0-01—P0-08 重验。 | [P0 索引](../exec/mcp-apps/phase-0/index.md)、[P0-08](../exec/mcp-apps/phase-0/p0-08-decision.yaml) | P0=`Go` 只授权后续技术验收。 |
| MCPAPPS-434 | 未修改的官方 `server-basic-vanillajs@1.7.5` 固定 identity、离线制品和标准 Client/Inspector smoke。 | [S1 回执](../exec/mcp-apps/phase-1/s1-appserver.md) | 只证明官方测试制品可复核。 |
| MCPAPPS-003 | 服务端 allowlist 内的低风险 `tools/call`、现有 Chat ingress 的 `ui/message`、Host context 和 actor-effective `window.im`。 | [当前候选总回执](../exec/mcp-apps/current-candidate-validation.md) | 高风险、需确认和未分类工具仍 fail closed。 |
| MCPAPPS-004 | manifest/lifecycle、多维隔离、脱敏诊断、版本矩阵与可配置资源策略。 | [当前候选总回执](../exec/mcp-apps/current-candidate-validation.md) | Phase 3 技术 preview 完成；不替代生产发布。 |

上表是工作与证据映射，不是派工或审批队列。后续改动只能由真实技术依赖和当前候选的可回读证据驱动。

## 4. 验收分组

| 分组 | 验收内容 |
|---|---|
| N1 | 根 Next workspace、client boundary、业务回归、唯一 route、root build/start/standalone。 |
| C1 | Python 服务身份、actor/workspace/Server scope、revision/expiry、最小披露和 secret 边界。 |
| S1 | 官方 `server-basic-vanillajs@1.7.5` 的 tag/commit/SHA-1/SRI、完整闭包、离线安装和标准 `/mcp`。 |
| M1 | 进程级 manager、标准 MCP endpoint、catalog 过滤、逐次重验、lifecycle、脱敏诊断和 Phase 1 zero-call。 |
| H1 | server-owned result identity、普通 fallback、Host adapter、双 iframe、sandbox/CSP、refresh/reconnect 和 teardown。 |
| P0 | 当前 pnpm lock 上的依赖、Browser 协议、安全、locality、fresh session、Chat roundtrip 与唯一 Go/No-Go。 |
| I2 | 低风险页面调用、`ui/message`、`window.im`、capability feature detection 和负向权限测试。 |
| G3 | 插件生命周期、多维隔离、诊断、升级、资源策略和最终发布回滚。 |

## 5. 历史输入排除

以下内容继续保留以便追溯，但不能作为当前候选的通过证据或回滚目标：

- 旧 npm lock 与其 P0-08 Go。
- 嵌套 `frontend/app/app/**`、下沉 Next config 和 Vite 默认生产入口。
- `frontend/app/_dream/server/mcp-apps/**` 与任何 alias/dual-write。
- repo-owned/self-built Phase 1 AppServer 与对应 fixture。
- 旧 Phase 1 filled requirement、截图、trace、P1 decision 和 nested standalone 回执。
- 任何缺少当前源码、lock、Browser、制品或配置指纹的历史测试。

## 6. 当前实际缺口

- Phase 0—3 只有 provider-free 本机技术证据；未使用真实账号、真实外部 MCP Server、真实 OAuth/credential 或生产运维链路。
- 公开应用中 `productionAppsEffective=false`；存在的 Browser/Node 能力只是默认关闭的技术 preview，不是产品可用性声明。
- 生产启用需独立证明真实 Server 身份与运维、actor/workspace 权限、OAuth/credential 生命周期、观测、发布与回滚；缺任一项均继续 No-Go。
- 当前回执中记录的测试工件路径和当时分支名只是执行时指纹，不是可持久的生产配置。

## 7. 失败与回滚

- 任何必要安全条件失败都形成 No-Go，并保留原命令、退出码、失败原因和受影响验收 ID。
- Apps 投影失败时只移除 `mcpAppResult`，保留 ordinary part/output；不得重放初始工具。
- 官方制品验证失败时停止 demo，不在线补包、不修改 demo、不恢复自建 Server。
- Browser/Node/Python 发生身份、权限或 revision mismatch 时在上游调用前拒绝。
- 回滚只清理本轮具名资源；不恢复旧目录、第二 lock、私有协议或 production Apps。

## 8. 文档同步

实现或证据变化时同步对应 task/requirement、`docs/exec`、技术执行计划和最近的 `.folder.md`。行为、版本、命令、架构或部署边界变化时同步 `README.md` 与 `README.zh.md`。

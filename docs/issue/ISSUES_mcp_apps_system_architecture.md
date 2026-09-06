<!-- [输入] DEC-002/004/005、系统架构执行清单、技术执行计划和对应 task/requirement。 -->
<!-- [输出] MCP Apps 当前工作项、技术依赖、验收入口与历史输入排除清单。 -->
<!-- [定位] MCP Apps 当前技术工作项、证据与回滚索引。 -->
<!-- [同步] 2026-09-06：重构为技术工作项索引，保留范围、安全、验收和回滚事实。 -->

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
- 全部实施和验证期间保持 `production_apps_effective=false`。

## 3. 当前工作项

| 工作项 | 目标 | 技术依赖 | 验收入口 |
|---|---|---|---|
| MCPAPPS-411-01 | 根 workspace、Web Shell、单一 App Router 与 Vite 生产入口退出。 | DEC-005；现有 URL/auth/OAuth/SSE/voice/runtime-config 行为。 | [task](../task/task_411-01_frontend_root-web-shell-vite-exit.md) / [requirement](../task/TASK-REQUIREMENT-task_411-01_frontend_root-web-shell-vite-exit.md) |
| MCPAPPS-411-02 | sibling Runtime package、薄 Route Handler、Python 最小投影、Chat result identity、只读 Host。 | 411-01；DEC-002/004/005；官方离线制品。 | [task](../task/task_411-02_shared_mcp-apps-runtime-route-handler.md) / [requirement](../task/TASK-REQUIREMENT-task_411-02_shared_mcp-apps-runtime-route-handler.md) |
| MCPAPPS-411-03 | 唯一 pnpm lock、根 standalone、P0-01→P0-04→P0-08 当前候选重验。 | 411-01、411-02；兼容 Chrome；当前源码和 lock 指纹。 | [task](../task/task_411-03_shared_pnpm-standalone-phase0-gate.md) / [requirement](../task/TASK-REQUIREMENT-task_411-03_shared_pnpm-standalone-phase0-gate.md) |
| MCPAPPS-434 | 官方 AppServer 原始 tarball、完整离线依赖闭包、manifest/digest、零网络 smoke。 | npm/GitHub 一手来源；具名外部 artifact 目录；隔离 consumer。 | [task](../task/task_434_shared_official-appserver-offline-supply.md) / [requirement](../task/TASK-REQUIREMENT-task_434_shared_official-appserver-offline-supply.md) |
| MCPAPPS-003 | 受控 `tools/call`、`ui/message` 和 `window.im`。 | Phase 1 当前候选证据完整；服务端低风险 allowlist。 | [task](../task/task_303_shared_mcp-apps-phase2-controlled-interaction.md) / [requirement](../task/TASK-REQUIREMENT-task_303_shared_mcp-apps-phase2-controlled-interaction.md) |
| MCPAPPS-004 | 版本、生命周期、多会话隔离、诊断、资源策略和最终 QA。 | Phase 2 当前候选证据完整。 | [task](../task/task_304_shared_mcp-apps-phase3-governance-qa.md) / [requirement](../task/TASK-REQUIREMENT-task_304_shared_mcp-apps-phase3-governance-qa.md) |

工作项可在文件不重叠时并行准备。验收结论必须遵守真实技术依赖，并基于同一当前候选的可回读证据。

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

- 当前 pnpm lock 下的 P0-01/P0-04/P0-08 必须用同一候选重验。
- 官方离线供应必须证明完整 production dependency closure、逐文件 digest、离线安装与零网络运行。
- Phase 1 必须补齐 Backend、Node、Browser、Next standalone 和 result identity 的当前候选证据。
- Phase 2/3 只能依据实际代码和 E2E 标记完成，设计文档本身不代表实现。
- production Apps 在独立生产权限、外部 Server 运维、发布与回滚证据存在前继续关闭。

## 7. 失败与回滚

- 任何必要安全条件失败都形成 No-Go，并保留原命令、退出码、失败原因和受影响验收 ID。
- Apps 投影失败时只移除 `mcpAppResult`，保留 ordinary part/output；不得重放初始工具。
- 官方制品验证失败时停止 demo，不在线补包、不修改 demo、不恢复自建 Server。
- Browser/Node/Python 发生身份、权限或 revision mismatch 时在上游调用前拒绝。
- 回滚只清理本轮具名资源；不恢复旧目录、第二 lock、私有协议或 production Apps。

## 8. 文档同步

实现或证据变化时同步对应 task/requirement、`docs/exec`、技术执行计划和最近的 `.folder.md`。行为、版本、命令、架构或部署边界变化时同步 `README.md` 与 `README.zh.md`。

<!-- [输入] MCP Apps 系统架构执行清单、DEC-002/004/005、Phase 0/1 历史证据与当前实现候选。 -->
<!-- [输出] Phase 0→3 的技术执行顺序、必要依赖、验收证据和回滚边界。 -->
<!-- [范围] 只描述产品实现、技术依赖、验证关系与回滚边界。 -->
<!-- [同步] 2026-09-06：按技术依赖和当前证据重建 Phase 0→3 执行计划。 -->

# MCP Apps Phase 0→3 技术执行计划

本计划只以当前候选的可观察证据判断进度。所有阶段继续遵守：

- `production_apps_effective=false`，直至生产发布条件由当前候选的完整证据独立证明。
- Browser 只连接 IM 同源 Node endpoint，不获得上游 URL、headers、env、credential 或完整配置快照。
- Python 只提供经过服务端鉴权的最小配置投影，不参与 iframe 通信。
- Node Runtime 是唯一 MCP 上游连接 owner；Browser 不直连真实 MCP Server。
- 首次工具调用仍由 Claude Agent Runtime 执行一次；App 渲染和恢复不得重放。
- 缺少 capability、官方制品、有效 revision、权限或证据时 fail closed，并保留普通工具结果。

## 1. 来源与当前证据

- [系统架构执行清单](../design/claude-agent/mcp-apps-system-architecture-execution-checklist.md)：50 个 P0/N1/C1/S1/M1/H1/I2/G3 工作项和完整验收边界。
- [Phase 0 证据索引](../exec/mcp-apps/phase-0/index.md)：旧 npm lock 下的历史 PoC 证据；只能用于追溯，不代表当前 pnpm lock 通过。
- [Phase 1 历史证据索引](../exec/mcp-apps/phase-1/index.md)：旧目录和旧实现路线的历史记录；不能替代当前 canonical package、官方制品和当前 Browser 证据。
- [DEC-005 根 Web Shell 任务](../task/task_411-01_frontend_root-web-shell-vite-exit.md)：`frontend/` 根 workspace、单一 App Router 和 Vite 退出的技术合同。
- [Runtime 与 Route Handler 任务](../task/task_411-02_shared_mcp-apps-runtime-route-handler.md)：Node Runtime、Python 投影、Chat result identity、Host 与只读闭环的技术合同。
- [pnpm/standalone/P0 任务](../task/task_411-03_shared_pnpm-standalone-phase0-gate.md)：唯一 lock、root standalone 和同 lock P0 重验合同。
- [官方 AppServer 离线供应任务](../task/task_434_shared_official-appserver-offline-supply.md)：官方制品身份、离线依赖闭包和 smoke 的供应合同。

## 2. 证据语义

| 结论 | 必须具备的证据 |
|---|---|
| 已验证 | 当前候选上的命令、退出码、关键输出和可回读证据均存在，且测试版本、lock、入口和源码一致。 |
| 历史通过 | 旧版本或旧 lock 曾通过；保留事实，但当前候选必须重新验证。 |
| 尚缺证据 | 实现可能存在，但缺少当前候选上的某项命令、Browser 行为、供应链证明或生产关闭回执。 |
| 未实现 | 当前源码没有对应能力，或现有实现明确不满足设计合同。 |
| No-Go | 真实验证失败或必要安全条件不成立；记录失败命令和原因，保持安全默认值。 |

文档存在、类型声明、静态扫描或旧截图不能单独证明行为通过。浏览器 harness 无法启动时记录为运行前置缺失，不能据此判断页面或 API 有缺陷。

## 3. 技术依赖图

~~~mermaid
flowchart TD
    D[DEC-002 + DEC-004 + DEC-005] --> N1[N1 根 Next workspace 与 canonical tree]
    D --> S1[S1 官方 AppServer 可验证离线制品]
    N1 --> C1[C1 Python 最小配置投影]
    N1 --> M1[M1 进程级 Node Runtime 与同源 Route Handler]
    S1 --> M1
    C1 --> M1
    M1 --> H1[H1 Chat result identity + Browser Host + sandbox]
    H1 --> P1[Phase 1 当前候选验收]
    P1 --> I2[I2 受控页面调用与 ui/message]
    I2 --> G3[G3 插件治理、多会话与可观测性]
    N1 --> L[唯一 pnpm lock + root standalone]
    M1 --> L
    H1 --> L
    L --> P01[P0-01 当前 lock 基线]
    P01 --> P04[P0-04 同 lock Browser 安全重验]
    P04 --> P08[P0-08 唯一 Go 或 No-Go]
    P08 --> P1
~~~

## 4. Phase 0：协议、安全与最小 PoC

Phase 0 必须在当前 pnpm lock、当前 Browser 入口和当前源码上重建证据。旧 npm lock 的结果保留为历史事实。

| ID | 工作项 | 必要依赖 | 当前候选验收 |
|---|---|---|---|
| P0-01 | 固定 MCP SDK、Host renderer、AppBridge、Playwright 与相关依赖版本，记录 pnpm lock digest。 | 唯一 `frontend/pnpm-lock.yaml`。 | frozen install、依赖树和 Browser bundle 使用同一 lock；无第二 lock。 |
| P0-02 | Browser Client 经 IM Node endpoint 完成 initialize、tools/list、resources/read。 | P0-01、可运行的官方 demo。 | Browser 网络面只出现 IM endpoint；页面 resource 可读。 |
| P0-03 | Host 从 `_meta.ui.resourceUri` 取得资源，首次工具调用保持一次。 | P0-02。 | descriptor/resource trace 与调用计数可复核。 |
| P0-04 | 验证 DEC-002 permissions、两层 iframe、sandbox proxy、CSP/Permissions-Policy 和 teardown。 | P0-01、兼容 Chrome。 | requested/desired/effective/revision、outer/inner allow、header 与 Web API 正反向 probe 一致。 |
| P0-05 | 验证 Node 对 stdio、localhost 和远程 HTTP Server 的实际可达性。 | P0-02。 | 每类 topology 有实测结论。 |
| P0-06 | 验证新 Node session 不依赖 Claude Agent 原物理连接的私有状态。 | P0-02。 | 新 session 能读取同一业务状态，或明确证明共享状态来源。 |
| P0-07 | 验证现有 Chat message/part 能保存 Apps result identity 和完整结果。 | 当前 Claude Agent/Chat DTO。 | refresh/reconnect 后仍有 `serverRef`、tool、`toolCallId`、input 和完整 result；无 schema 变更。 |
| P0-08 | 汇总 P0-02—P0-07，原位形成当前 lock 的唯一 Go/No-Go 结论。 | 同一源码、lock、Browser 和入口指纹。 | 任一必要证据失败即 No-Go；两种结论都保持 production Apps 关闭。 |

Phase 0 回滚只删除本轮隔离 PoC、测试配置和具名临时资源；普通 MCP、Chat、数据库和历史证据不变。

## 5. Phase 1：只读 App 闭环

### 5.1 N1：根 Next workspace

- `frontend/` 是唯一 workspace、Web package 和 Next root。
- `frontend/app/**` 是唯一 App Router。
- `frontend/packages/mcp-apps-runtime/**` 是唯一独立 Node Runtime。
- 根 `dev/build/start` 与 standalone 必须从 `frontend/` 无位置参数运行。
- 登录、OAuth、Agent SSE、cancel/resume、语音、运行时配置和现有 Chat 行为必须回归。
- 旧嵌套 Next、Vite 生产入口、npm lock 和 `frontend/app/_dream/server/mcp-apps/**` 不得成为当前运行路径。

### 5.2 C1：Python 最小配置投影

- C1-01—C1-03 定义并提供单 actor/workspace/Server 的静态视图和短时建连配置。
- C1-04 在解密前校验服务身份、actor、workspace、Server、revision、enabled 和 expiry。
- C1-05 保持现有 `RuntimeSnapshotLoader.load()` 与 Agent turn 行为不变。
- C1-06 证明 URL secret、headers、env、token 和完整 snapshot 不进入 Browser、日志或错误。

### 5.3 S1：官方 AppServer

只允许未修改的 `@modelcontextprotocol/server-basic-vanillajs@1.7.5`：

- npm SHA-1：`855c0acd7df70d840b9fdb1bc0868a3f68288e7f`
- SRI：`sha512-q/uOxYZd7I1aMgUaQDj9ksM+5lN+4xKilwsuQTBq6q0CdeXh8pS+V+CqPq4Hv59uT/HjUyZRGQKjFV3JWMQwBQ==`
- Git tag/commit：`v1.7.5` / `92f46a574568a3ddac7600343b7d3c4c4ed7b588`
- 默认 stateless Streamable HTTP `/mcp`
- `get-time`、`ui://get-time/mcp-app.html` 和 `text/html;profile=mcp-app`

供应证据必须覆盖原始 tarball、完整 production dependency closure、逐文件 digest、离线安装、零网络运行验证和清理。缺少任一项时只记录尚缺证据，不用自建 fixture、在线补包或修改官方 demo 代替。

### 5.4 M1：Node Runtime 与同源 endpoint

- M1-01：GET/POST/DELETE 标准 MCP Route Handler 薄委派 Runtime package。
- M1-02—M1-03：进程级 `PersistentConnectorManager`，按 actor/workspace/Server/config revision/credential revision 隔离。
- M1-04—M1-05：过滤 catalog，并在每次上游请求前重验 `serverRef`、tool、URI 和 allowlist。
- M1-06：处理配置变更、OAuth 过期、断线、取消、Node 重启和关闭；未确认写操作不重放。
- M1-07：记录脱敏的阶段诊断，不包含 URL query、headers、env 或正文。
- M1-08：Phase 1 拒绝页面发起的全部 `tools/call`；禁用或 revision 变化会拒绝旧 session 并释放无引用连接。

### 5.5 H1：Chat result、Host 与 sandbox

- H1-01：server-owned result identity 从 live SSE、persisted part、Public DTO 到 refresh consumer 保持一致。
- H1-02：`ToolMessagePart` 在原结果位置挂载 Apps Host；普通工具、工具确认卡和无 UI fallback 不回归。
- H1-03—H1-04：Browser Client 只连接同源 endpoint；Host adapter 接收已连接 Client、tool input/result 与 immutable policy snapshot。
- H1-05：loading、error、timeout、close/reopen、Thread switch、refresh、禁用和 revision 变化均有 teardown/fallback。
- H1-06：只读 allowlist；Phase 1 不声明页面工具调用能力。
- H1-07—H1-08：版本化独立 origin sandbox proxy、CSP、Permissions-Policy、消息来源/schema、HTML 交付和销毁验证。

### 5.6 Phase 1 验收

- 当前候选上的 typecheck、Runtime tests、Backend focused tests、Next build/start/standalone 全部有退出码。
- 官方制品同时通过标准 Client smoke 和 IM Browser→Node→Manager 只读闭环。
- 无 Host、metadata 缺失、资源失败、插件禁用、版本不兼容和策略拒绝都保留同次普通工具结果。
- Browser、页面源码、日志和错误中没有上游 URL 或 credential。
- 页面 `tools/call` 全部被拒绝且上游调用计数为零。
- refresh/reconnect 不重放首次工具调用，identity mismatch 只移除 Apps 投影。
- sandbox、CSP、来源校验、权限正反向 probe 和 teardown 通过真实兼容 Chrome。
- 所有验证前后 `production_apps_effective=false`。

Phase 1 回滚先关闭 Apps effective flag，再卸载 Host/iframe/Browser Client、拒绝旧 Node session并回收无引用 connector；必要时回退已验证 Web image。普通工具结果继续显示。

## 6. Phase 2：受控双向交互

Phase 2 只有在 Phase 1 当前候选证据完整后才能验证。

| ID | 工作项 | 验收重点 |
|---|---|---|
| I2-01 | `AppBridge.oncalltool` 接管页面工具请求，并沿 Browser Client→Node→Server 标准链路调用。 | Host 与 Node 均执行权限校验；成功调用不创建 Agent turn。 |
| I2-02 | 服务端 App-callable allowlist 只开放策略允许的低风险工具。 | 高风险、未分类和需要逐次确认的工具在 Node 拒绝且不上游。 |
| I2-03 | `ui/message` 进入当前页面已有 Thread 的正常 Chat ingress。 | 一次请求产生一个普通用户消息和一个新 Agent turn。 |
| I2-04 | Host→App 只发送声明范围内的 input/result/theme/locale/display context。 | 不包含完整对话或敏感上下文。 |
| I2-05 | 版本化 `window.im` 兼容层与规范成员保持同参数、返回和失败语义。 | 只改变 namespace，不发明私有 transport。 |
| I2-06 | 文件、modal、显示模式和导航能力逐项 feature detect。 | 只有真实实现的能力才被声明。 |
| I2-07 | 恶意 tool、URI、message、origin 和重放请求的负向验证。 | App 不能绕过 Node 权限；拒绝可审计。 |

高风险写工具需要新的、服务端可验证且不可重放的授权合同。在该合同存在前，Node 始终拒绝，不使用 Apps 私有协议补洞。

## 7. Phase 3：治理、多会话与观测

| ID | 工作项 | 验收重点 |
|---|---|---|
| G3-01 | manifest 声明 Browser/Node entry、协议/SDK 版本和 feature flag。 | 声明与真实能力一致；不兼容时 fail closed。 |
| G3-02 | 安装、启用、禁用、升级、销毁与不兼容处理。 | 禁用会立即失效已有 Client/View/session；普通结果保留。 |
| G3-03 | 多用户、多 workspace、多 Server、多 Browser session 隔离。 | catalog、result、notification 和 credential 不串用。 |
| G3-04 | Browser、Chat、Node endpoint、上游 Server 分段诊断。 | 能区分投影、transport、resource、iframe、权限和上游错误。 |
| G3-05 | 协议与依赖升级合同测试。 | 升级前重跑官方 demo、inspector、Browser 和回归矩阵。 |
| G3-06 | resource 大小、超时、并发和网络访问策略。 | 超限只影响目标请求，不传播到 Agent turn。 |
| G3-07 | 仅在出现多 Host 或跨网络真实需求时评估独立 Bridge/Gateway。 | 新拓扑必须另有 ADR；默认继续使用 Next Node Runtime。 |

## 8. 当前实施顺序

1. 固定 canonical tree、单一 pnpm lock 和 Runtime package graph。
2. 完成官方 AppServer 的可复现离线供应证据。
3. 完成 C1 Python 最小投影、M1 进程级 Runtime 与 H1 server-owned result identity。
4. 完成只读 Browser Host、sandbox proxy、fallback、zero-call 和 lifecycle。
5. 在同一当前候选上运行 root standalone 与 P0-01→P0-04→P0-08。
6. 汇总 Phase 1 当前候选的 Backend、Node、Browser、Next 和供应链证据。
7. Phase 1 证据完整后实施 I2；I2 完成后实施 G3。

步骤 1—6 可以在不互相覆盖文件的前提下准备独立测试，但验收结论必须基于同一源码、lock、配置和制品指纹。

## 9. 工作树、证据和回滚

- 开始前记录 `git status --porcelain=v1 --untracked-files=all`；保留用户和并发任务的现有改动。
- 目标文件发生并发变化时暂停该文件，与并发任务协调后基于最新内容继续。
- 测试日志、截图、trace、tarball 解压、临时 HTML、端口和进程写入具名 run-owned scratch；仓库只提交源码、必要小型脱敏证据和正式报告。
- 测试只停止或删除本轮具名的进程、端口、数据库和临时目录。
- 无法运行的命令保留原命令、退出码、失败类型和受影响验收；不把替代检查包装为原命令通过。
- 回滚不得恢复旧 nested Next、legacy Runtime、自建 AppServer、第二 lock、私有协议或 production Apps。

## 10. 文档维护

每个工作项只有在当前候选证据齐全后才可标为完成。更新时同步：

- 对应 task/requirement 的技术范围与实际缺口；
- `docs/exec` 中的命令、退出码和证据路径；
- 受影响目录的 `.folder.md`；
- 行为、版本、命令或部署边界变化时同步 `README.md` 与 `README.zh.md`。

历史失败和旧版本通过记录继续保留，并明确其适用的源码、lock 和运行环境。

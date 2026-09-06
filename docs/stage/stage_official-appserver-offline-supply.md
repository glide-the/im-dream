<!-- [输入] DEC-004、官方发布身份、task_434 与独立 requirement。 -->
<!-- [输出] 官方 AppServer 离线制品的获取、验证、消费和清理顺序。 -->
<!-- [范围] 只描述供应链技术步骤；不改 Dream 生产代码、pnpm lock、运行时配置或 production Apps 状态。 -->
<!-- [同步] 2026-09-06：按 SUPPLY-01—09、安全边界与真实验收重建供应顺序。 -->

# 官方 AppServer 离线供应技术计划

本计划为 [task_434](../task/task_434_shared_official-appserver-offline-supply.md) 和对应 [requirement](../task/TASK-REQUIREMENT-task_434_shared_official-appserver-offline-supply.md) 排定技术步骤。制品只有在身份、依赖闭包、离线安装、标准 MCP smoke 和清理证据全部成立后，才可由 411-02 离线消费。

## 1. 固定范围

- 唯一目标：未修改的 `@modelcontextprotocol/server-basic-vanillajs@1.7.5`。
- npm SHA-1：`855c0acd7df70d840b9fdb1bc0868a3f68288e7f`。
- npm SRI：`sha512-q/uOxYZd7I1aMgUaQDj9ksM+5lN+4xKilwsuQTBq6q0CdeXh8pS+V+CqPq4Hv59uT/HjUyZRGQKjFV3JWMQwBQ==`。
- Git tag/commit：`v1.7.5` / `92f46a574568a3ddac7600343b7d3c4c4ed7b588`。
- 运行形态：默认 stateless Streamable HTTP `/mcp`，只绑定本轮隔离 loopback 端口。
- 业务能力：`get-time`、`ui://get-time/mcp-app.html`、`text/html;profile=mcp-app`。
- 整个过程保持 `production_apps_effective=false`。

仓库、用户 npm cache、global cache、历史临时目录、旧自建 fixture 和旧 Phase 1 证据都不能作为供应输出。外部制品根目录必须由运行环境显式配置，并位于本轮具名、可删除、无符号链接逃逸的临时空间。

## 2. 技术依赖图

~~~mermaid
flowchart TD
    I[固定 npm/Git identity] --> F[只读获取原始 tarball 与 provenance]
    F --> C[解析 production dependency closure]
    C --> K[建立只读离线 cache + manifest + lock]
    K --> V[全新 consumer 禁网离线安装]
    V --> M[直接运行 dist/index.js]
    M --> P[标准 MCP initialize/tools/list/resources/read/tools/call]
    P --> R[回读 digest、零网络与 cleanup 证据]
    R --> H[411-02 只读消费]
    F -->|identity mismatch| X[停止并清理本轮临时对象]
    C -->|closure 不完整| X
    V -->|发生出网或 lifecycle script| X
    M -->|非 loopback 或协议失败| X
~~~

## 3. SUPPLY 验收

| ID | 技术动作 | 通过条件 |
|---|---|---|
| SUPPLY-01 | 固定 package、version、tag、commit、SHA-1 与 SRI。 | 六项身份逐一匹配；不使用 `latest`、branch head 或本地重打包。 |
| SUPPLY-02 | 在白名单网络窗口只读获取 npm/GitHub 元数据与原始 tarball。 | 请求方法和 host 可审计；无凭证、写请求或额外来源。 |
| SUPPLY-03 | 验证 provenance、归档安全和根 tarball bytes。 | provenance 指向固定发布；归档无绝对路径、`..`、设备文件或符号链接逃逸。 |
| SUPPLY-04 | 解析完整 production dependency closure。 | 每个包都有 name、version、integrity、tarball digest 和父依赖关系。 |
| SUPPLY-05 | 生成只读离线 cache、manifest、lock 和逐文件 SHA-256。 | 输出可在新目录回读复算，且不引用用户/global cache。 |
| SUPPLY-06 | 在全新 consumer 执行 `npm_config_offline=true npm install --offline --ignore-scripts --no-audit --no-fund`。 | 退出 0；网络调用为零；未运行 lifecycle script。 |
| SUPPLY-07 | 从离线安装直接启动官方 `dist/index.js`。 | 只绑定具名 loopback 端口；没有源码 patch、wrapper 行为改写或生产服务连接。 |
| SUPPLY-08 | 用标准 MCP Client 验证协议与资源。 | `initialize → tools/list → resources/read → tools/call` 全部通过；descriptor、URI、MIME 与同回应时间一致。 |
| SUPPLY-09 | 保存脱敏 receipt 并清理本轮运行资源。 | manifest/digest/命令/退出码可回读；具名 PID、端口和临时副本已清理；production Apps 仍关闭。 |

## 4. 顺序与失败语义

1. 先记录目标身份、临时目录真实路径和现有工作树状态。
2. 在同一只读获取窗口取得原始发布材料；窗口关闭后，后续安装、启动和 smoke 全部禁网。
3. 依赖闭包、manifest、lock、tarball 和逐文件 digest 必须来自同一份原始发布输入。
4. 离线 consumer 必须全新创建；安装不能读取仓库 `node_modules`、用户 cache 或 global cache。
5. MCP smoke 只运行官方入口，并验证 loopback、stateless `/mcp`、标准 Client 和声明资源。
6. 任一身份、闭包、网络、归档、安装、隔离或协议条件失败时记录原命令、退出码和原因，停止消费并清理本轮临时对象。

不能用旧自建 Server、旧截图、静态类型、在线补包或修改官方 demo 将失败改写为通过。

## 5. 输出与下游消费

输出至少包含：

- 原始根 tarball；
- 完整 production dependency cache；
- manifest、lock、provenance/attestation 与逐文件 digest；
- 获取请求摘要、离线安装 receipt、标准 MCP smoke receipt、网络断言和 cleanup receipt。

411-02 必须从显式配置的制品根目录只读消费这些输出，并重新验证 identity 与 digest。供应成功只证明 S1 可复现，不证明 Browser/Node 集成、Phase 1 验收或 production Apps 发布。

## 6. 回滚

- 停止本轮具名 PID，释放具名 loopback 端口。
- 删除本轮 consumer、解压目录、cache 副本与临时日志。
- 保留已提交的小型脱敏 receipt 与用于复核的固定 digest。
- 不删除用户数据、共享 cache、历史证据或其他进程；不恢复旧自建 AppServer 路线。

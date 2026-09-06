<!-- [输入] task_434、DEC-004 固定身份、可配置 artifact root 与当前 Node/npm 工具链。 -->
<!-- [输出] 可直接执行的 SUPPLY-01—09 离线供应和验证 requirement。 -->
<!-- [定位] 官方 AppServer 供应执行合同；使用仓库外可配置 artifact。 -->
<!-- [同步] 2026-09-06：按技术依赖、仓库外 artifact、离线证据和清理边界重建。 -->

# TASK-REQUIREMENT：官方 AppServer 离线供应

## 1. 执行目标

完成 [task_434](./task_434_shared_official-appserver-offline-supply.md) 的 SUPPLY-01—09：获取并验证 `@modelcontextprotocol/server-basic-vanillajs@1.7.5` 及完整 production dependency closure，生成只读离线 artifact，在 fresh consumer 中禁网安装并运行标准 MCP smoke，最后记录命令、退出码、digest、网络证据和清理结果。

只证明官方测试制品供应；不宣告 IM 集成、Phase 1、P0 或 production Apps 通过。

## 2. 必须核对的固定值

- npm SHA-1：`855c0acd7df70d840b9fdb1bc0868a3f68288e7f`
- npm SRI：`sha512-q/uOxYZd7I1aMgUaQDj9ksM+5lN+4xKilwsuQTBq6q0CdeXh8pS+V+CqPq4Hv59uT/HjUyZRGQKjFV3JWMQwBQ==`
- Git tag/commit：`v1.7.5` / `92f46a574568a3ddac7600343b7d3c4c4ed7b588`
- MCP endpoint：默认 stateless `/mcp`
- Tool/resource/MIME：`get-time`、`ui://get-time/mcp-app.html`、`text/html;profile=mcp-app`

固定值任一不一致即停止，并在报告中记录实际值和来源。

## 3. 路径与资源

执行前填入：

| 字段 | 值 |
|---|---|
| Artifact root | `{{CONFIGURED_ARTIFACT_ROOT}}` |
| Acquisition cache | `{{CONFIGURED_ARTIFACT_ROOT}}/acquisition-cache` |
| Offline cache | `{{CONFIGURED_ARTIFACT_ROOT}}/offline-cache` |
| Fresh consumer | `{{CONFIGURED_ARTIFACT_ROOT}}/offline-consumer` |
| Evidence | `{{CONFIGURED_ARTIFACT_ROOT}}/evidence` |
| Loopback port | `{{RUN_OWNED_LOOPBACK_PORT}}` |
| 正式报告 | `docs/exec/exec_task_434_official-appserver-offline-supply.md` |

artifact root 必须在仓库和用户 cache 之外、不是 symlink，并且只包含本轮资源。

## 4. 执行步骤

1. 记录 `git status --porcelain=v1 --untracked-files=all`、Node/npm 版本、artifact root realpath、网络白名单和端口。
2. 仅从 npm 官方 registry 获取根 tarball；只读核对官方 GitHub tag/commit。
3. 验证 SHA-1、SRI、tag/commit 和 package metadata。
4. 解析并下载完整 production dependency closure；逐包记录名称、版本、来源、bytes、SHA-256 和 integrity。
5. 生成 manifest、production lock、逐文件 digest 和来源说明；保留原始 tarball 字节。
6. 构造只读离线 cache/artifact，并从只读副本回读所有 digest。
7. 在 fresh consumer 中设置 `npm_config_offline=true`，执行 `npm install --offline --ignore-scripts --no-audit --no-fund`。
8. 启动官方 `dist/index.js`，用标准 MCP Client 验证 initialize、tools/list、resources/read 和 tools/call。
9. 使用可复核方法证明步骤 7—8 没有非 loopback 网络调用。
10. 停止本轮 PID/port，删除临时 consumer 和可删除副本，保留只读 artifact 与脱敏证据。
11. 写正式报告并逐项映射 SUPPLY-01—09。

## 5. 写入与禁止范围

仓库内只允许写正式报告及其最近 `.folder.md` inventory。其余输出全部写入配置提供的 artifact root。

不得修改业务源码、测试 fixture、依赖 lock、数据库、部署、用户 cache、生产配置或其他历史证据。不得登录、publish、在线安装、使用安装脚本、patch/fork/vendor 官方包、自建替代 Server 或启用 production Apps。

## 6. 验收报告

报告至少包含：

- SUPPLY-01—09 的逐项结论；
- 每条命令、cwd、退出码和关键输出；
- 根包及完整闭包的名称、版本、bytes、SHA-256、SHA-1/SRI；
- manifest 与 production lock digest；
- 离线安装和标准 MCP smoke 结果；
- 网络监测方法、非 loopback 调用计数和限制；
- PID、端口、临时路径和清理结果；
- 未运行项、真实失败和当前 artifact 是否可消费；
- `production_apps_effective=false` 的最终确认。

无法证明完整闭包、只读回读、禁网安装或零网络运行时，不得把 artifact 标为可消费。

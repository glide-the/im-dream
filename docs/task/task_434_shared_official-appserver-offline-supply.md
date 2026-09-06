<!-- [输入] DEC-004 官方制品身份、当前 Node/npm 工具链和可配置的仓库外 artifact root。 -->
<!-- [输出] 官方 AppServer 的原始 tarball、完整离线依赖闭包、manifest/digest、离线安装与标准 MCP smoke 证据。 -->
<!-- [范围] 只供应和验证官方制品；不修改 Dream 业务代码、依赖 lock、数据库、生产配置或 Apps 开关。 -->
<!-- [同步] 2026-09-06：改用可配置 artifact root、技术依赖与 SUPPLY-01—09 证据。 -->

# task_434：官方 AppServer 离线制品供应

配套 requirement：[TASK-REQUIREMENT-task_434_shared_official-appserver-offline-supply.md](./TASK-REQUIREMENT-task_434_shared_official-appserver-offline-supply.md)

## 1. 目标

为 `@modelcontextprotocol/server-basic-vanillajs@1.7.5` 生成一个可复现、只读、仓库外的离线供应包，并证明：

- 原始 npm tarball 与官方身份一致；
- production dependency closure 完整；
- fresh consumer 可在禁网模式安装；
- 官方 `dist/index.js` 可在隔离 loopback 端口完成标准 MCP smoke；
- 运行期没有隐式网络取包；
- 清理只影响本轮资源。

该结果只证明官方测试制品可离线消费，不代表 IM 集成、Phase 1、P0 或 production Apps 通过。

## 2. 固定身份

| 字段 | 值 |
|---|---|
| Package | `@modelcontextprotocol/server-basic-vanillajs@1.7.5` |
| npm SHA-1 | `855c0acd7df70d840b9fdb1bc0868a3f68288e7f` |
| npm SRI | `sha512-q/uOxYZd7I1aMgUaQDj9ksM+5lN+4xKilwsuQTBq6q0CdeXh8pS+V+CqPq4Hv59uT/HjUyZRGQKjFV3JWMQwBQ==` |
| Git tag | `v1.7.5` |
| Git commit | `92f46a574568a3ddac7600343b7d3c4c4ed7b588` |
| Transport | default stateless Streamable HTTP `/mcp` |
| Tool/resource | `get-time` / `ui://get-time/mcp-app.html` |
| MIME | `text/html;profile=mcp-app` |

## 3. 技术依赖

- 获取阶段允许对 npm 官方 registry 做一次性 HTTPS GET/HEAD，并只读核对官方 GitHub tag/commit。
- artifact root 必须由调用方显式提供，位于仓库和用户 npm cache 之外，不使用符号链接。
- 获取阶段与离线消费阶段使用不同的具名目录和 npm cache。
- 离线阶段必须在 fresh consumer 中设置 `npm_config_offline=true`，并使用 `--offline --ignore-scripts --no-audit --no-fund`。
- 标准 MCP probe 只访问本轮隔离 loopback 端口。
- 缺少网络、artifact root、Node/npm、端口或监测工具时记录受影响验收，不用仓库 `node_modules`、用户 cache 或在线安装替代。

## 4. 工作项与验收

| ID | 工作项 | 通过标准 |
|---|---|---|
| SUPPLY-01 | 记录 Node/npm 版本、artifact root、网络白名单和工作树基线。 | 路径位于仓库外且非 symlink；仓库目标文件未被业务写入。 |
| SUPPLY-02 | 从 npm 获取原始根 tarball，核对 SHA-1/SRI 与 Git tag/commit。 | 所有固定身份一致；原始字节保留。 |
| SUPPLY-03 | 解析 production dependency closure 并逐包保存 tarball。 | 闭包完整，无 dev-only 或遗漏的 runtime 包；每包有名称、版本、来源、bytes 和 digest。 |
| SUPPLY-04 | 生成 machine-readable manifest、production lock、逐文件 digest 和来源说明。 | manifest 能独立枚举根包、闭包、文件和校验值。 |
| SUPPLY-05 | 将供应目录设为只读，并从只读副本做回读校验。 | 回读 digest 与生成时一致。 |
| SUPPLY-06 | 在 fresh consumer 中执行禁网安装。 | npm 离线安装退出 0，无 registry 请求、安装脚本或用户 cache 命中。 |
| SUPPLY-07 | 运行官方 `dist/index.js` 和标准 MCP Client smoke。 | initialize、tools/list、resources/read、tools/call 成功；tool/resource/MIME 正确。 |
| SUPPLY-08 | 证明离线安装和运行阶段网络零调用，并清理 PID/port/temp。 | 监测证据无非 loopback 请求；具名资源全部清理。 |
| SUPPLY-09 | 写正式报告，列出命令、退出码、digest、未运行项和限制。 | 报告可从空环境定位并复核 artifact；不含 credential 或用户正文。 |

任一身份、闭包、digest、离线或 smoke 条件失败时记录 No-Go，保留原始证据并停止使用该 artifact；不得 patch、fork、vendor 或自建替代 Server。

## 5. 写入边界

允许：

- `<configured-artifact-root>/server-basic-vanillajs-1.7.5/**`：本轮 tarball、cache、consumer、manifest、lock、digest、日志和回执。
- `docs/exec/exec_task_434_official-appserver-offline-supply.md`：唯一仓库内正式报告。
- 必要的 `docs/exec/.folder.md` 最小 inventory 更新。

禁止：

- Dream/Frontend/Backend 业务源码、依赖 lock、测试 fixture、数据库、部署和 production config。
- 用户 npm cache、全局 `node_modules`、旧 artifact、其他任务的 scratch、共享服务和他人进程。
- 在线安装、登录、publish、patch、fork、vendor、自建 Server、`main/latest` 或 production Apps 启用。

## 6. 证据与安全

- 日志不得包含 registry token、GitHub credential、完整环境变量、用户路径之外的私有数据或页面正文。
- 每个命令记录 cwd、退出码和关键输出；hash 工具与算法写入 manifest。
- 网络证据必须区分获取阶段和离线消费阶段。
- smoke 只记录协议方法、状态、tool/resource identity、计数和 MIME，不保存 HTML 正文。
- 只停止本轮记录的 PID/端口，只删除本轮 artifact root 下的临时 consumer/cache 副本。

## 7. 回滚

删除或隔离失败的本轮 artifact 目录，并停止本轮 loopback 进程。仓库业务代码、普通 MCP/Chat、数据库、用户 cache、历史证据和 `production_apps_effective=false` 保持不变。

<!-- [Input] User-authorized AutoDL deployment, merged Admin/Dream commits, existing direct-host scripts, and task 01a05775-b5b2-7362-b388-fa23be380eab. -->
<!-- [Output] Deployment plan and append-only evidence for the 2026-09-17 unified auth/data release. -->
<!-- [Pos] Cross-project AutoDL release receipt; secrets and business payloads are excluded. -->
<!-- [Sync] 2026-09-17: define candidate smoke, forward migration, atomic activation, no retained old release, and public acceptance gates. -->

# AutoDL 统一认证与数据接口发布回执

## Optimized Prompt

以合并后的 Admin `main` 与 Dream `develop` 精确 commit 发布统一认证和 DTO/ORM 数据接口版本。先核对远端主机、数据目录、当前链接、端口和公网映射；Admin 先发布，唯一执行 Drizzle 前向 migration，并验证 Better Auth、Admin 页面、数据库 capability 与 Dream 数据接口。Dream 后发布，只消费 Admin API，保留 Agent Runtime、SSE、线程工作区和共享文件系统。两个项目都先构建不可变 candidate，在隔离端口验证候选，再原子切换。切换或验证失败时仅在本轮内恢复仍存在的旧应用；所有本机和公网验收通过后删除旧 release 和临时链接，不保留长期回滚版本。不得打印或提交 SSH、OAuth、数据库及服务密钥。

保持不变：Admin/Dream 用户域不合并；Dream 无 PostgreSQL 凭据、SQL、ORM 或 migration；共享根目录、`.claude-tmp`、权限、符号链接边界、turn/resume/cancel 与资源策略语义不变。失败时停止下游发布，记录命令、退出码、候选与 current 指向，不删除数据库或共享业务数据。

验收：PR 已合并，两个本地默认分支 fast-forward 到远端；Admin migration/capability、本机 `6008` 与公网登录通过；Dream 候选 `16006/18765`、正式 `6006/8765`、公网 health、crawler、内置 Skills、默认 Plugin 与 Admin 依赖通过；远端只保留最终 current release。

## 初始证据

- 远端主机：`autodl-container-ylgygfuaq4-2c9ee25f`。
- 设备重启后 screen 与 `6006/6008/8765` 均未运行；release 链接与持久数据盘仍存在。
- 发布顺序：Admin → migration/capability → Dream → 跨服务公开入口。
- 发布结果在实际执行后追加；本段不声明部署成功。

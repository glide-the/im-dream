# Dream Claude Plugin 数据消费迁移阶段

## Optimized Prompt

在 Dream 工作分支中，将共享 Claude Plugin 的 Marketplace 目录、安装操作、安装记录、卸载和生命周期持久化全部迁移到 Admin Registry175-182。严格复用 Admin 已发布的业务 DTO、Service 和 typed Drizzle Repository 契约；Dream 只能保留公开 HTTP 路由、CLI/Git 执行、manifest 与 digest 校验、不可变 artifact 导入和共享文件系统操作。删除 Dream 的目录/安装 SQL 服务和任何数据库 fallback，保持公开响应、后台安装、Remote Marketplace ref/commit/manifest/full-content digest 校验、Deck refs、Runtime/SSE 与 workspace freeze/repair 语义不变。

已有证据：Admin 工作分支提交 `69cfbca` 已提供八项操作、严格 DTO、行锁、原子 ready 持久化和 soft uninstall；Dream 现有 `claude_plugins.py`、`install_service.py` 与 `marketplace_service.py` 仍包含 SQL 或数据库连接。责任仓库为 Dream；依赖 Admin Registry175-182 和 `dream.claude-plugin.remote-marketplace.v1` capability。

修改范围：新增 `services/admin_data/claude_plugin_data.py`；注册操作；将路由改为 current OAuth actor + Admin client；将安装服务改为 reporter port；删除 `marketplace_service.py`；更新安全错误、目录契约和 provider-free 测试。接口只接受 package spec、Marketplace entry ID、operation/installation ID 和严格生命周期证据，不接受 actor/user、SQL、表列或事务选择器。未知写入只查询原 request receipt，不自动重试。

正常流程为 Admin prepare queued operation → Dream begin/progress → CLI/Git/文件校验与 artifact 导入 → Admin complete 原子提交；失败流程写本地 bounded evidence 并向 Admin 报告 terminal error。Admin/capability 不可用时明确失败，不回退 Dream PostgreSQL。保持 Runner、ThreadFactory、EventBus、SSE、turn/resume/cancel、资源策略、共享根目录和 `CLAUDE_CODE_TMPDIR` 协议不变。

验收：运行 DTO/路由/安装执行器/Deck refs 聚焦测试、全部 Claude Plugin 相关测试、Ruff、Python 编译、Markdown 路径检查和源码 SQL 清单；确认公开路由没有 `database/get_db/execute`，Remote digest drift 仍 fail closed。主要风险是后台执行与 Admin terminal report 的未知结果、旧真实 CLI SQLite fixture 以及启动内置插件回填；后两项必须作为后续显式关闭项，不能冒充本阶段已完成。

## 评审结论

- Admin 负责身份、权限、目录查询、操作/安装记录、锁、事务和卸载引用处理；Dream 负责本地执行与文件证据，职责符合目标。
- 八项 DTO 均为业务操作；没有任意 SQL/表列接口，也没有外部用户 ID selector。
- 安装完成保持一个 Admin 事务；Dream 不把原事务拆成无一致性的多次数据写入。
- Remote Marketplace 的 URL/ref/commit/manifest/digest 校验和本地 artifact 算法保持不变。
- 本阶段关闭公开目录与安装生命周期 SQL；`server.py` 内置插件启动回填及 `workspace_packer.py` 测试兼容 SQL 将在后续阶段单独关闭。

## 验收记录

| 检查 | 结果 |
|---|---|
| Registry175-182 DTO、receipt、路由、安装执行器、Deck refs | `68 passed` |
| Claude Plugin 扩展回归 | `58 passed, 1 skipped, 14 subtests passed`；skip 为需显式真实 CLI 条件的技术测试 |
| Dream PostgreSQL fallback | 公开插件路由与安装服务已删除 `database/get_db/SQL`；启动与测试兼容入口列为下一阶段 |

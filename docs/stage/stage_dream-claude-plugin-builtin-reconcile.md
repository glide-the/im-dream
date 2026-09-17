# Dream 内置 Claude Plugin 启动协调切换

## 背景与问题

Dream 的公开 Claude Plugin 路由已消费 Admin Registry175-182，但 `server.py` 启动任务仍直接查询
`claude_plugin_installations`，并调用 `database.py` 中硬编码 Deck Plugin ID 的 SQL 回填。该路径违反
Admin 统一数据库访问边界，也无法按 release manifest 的真实声明决定哪些 Deck 需要引用。

## 目标与边界

Dream 注册并消费 Admin Registry183-184。Admin 用严格 DTO、Service 与 typed Drizzle Repository
负责 ready installation 查询、active binding/release join、manifest 判断、ref 写入、事务和回执。
Dream 只保留服务器声明的 builtin source、真实 Claude CLI 校验、摘要、immutable artifact import、
共享文件系统证据和启动编排。

本阶段不改变 Agent Runtime、EventBus、SSE、turn/resume/cancel、资源策略、线程工作区、
`CLAUDE_CODE_TMPDIR`、`0700` 权限或 sandbox 范围，也不新增 migration。

## 概念与规则

- `claude-plugin.builtin.ensure` 只接受 `package_spec`，不接受用户、Deck、SQL、表、列或事务选择器。
- ready installation 存在时，Admin 从 active binding 的 exact release manifest 中匹配
  `runtime.claude_code_plugins[].claude_code_plugin_id` 并补齐 refs。
- 缺失时 Admin 返回 installation plan；Dream 才执行现有 `PluginInstallService`。
- lifecycle 通过 `claude-plugin.builtin.report` 上报；complete 的 installation、operation、refs、receipt
  与 audit 在同一 Admin UOW。
- 两个操作只允许配置了 `plugins:catalog` 的 Dream 服务调用，禁止携带 browser OAuth bearer。
- 写响应未知时只读取相同 operation/request_id 的原 receipt，不重发；Admin 不可用或 capability
  缺失时记录具体失败并继续启动，不连接 PostgreSQL。

## 正常流程与状态

1. 启动任务从 `PLATFORM_BUILTIN_SOURCES` 读取服务端声明。
2. `ensure` 返回 `ready` 时结束该包处理，并记录新建 ref 数量。
3. `ensure` 返回 `install` 时，Dream 使用 plan 的 operation ID 和 source type 运行既有 CLI/制品管线。
4. reporter 发送 begin/progress/complete；Admin 完成 queued → running → ready 和引用写入。
5. fail 事件保持 error；单包失败不阻止 FastAPI 启动。

## 影响与验收

- 删除 `server.py` 的 installation SELECT 与 ref backfill 调用。
- 删除 `database.py::backfill_builtin_deck_plugin_refs`。
- Registry183-184 Pydantic contract、response binding、unknown-write receipt 和 startup coordinator 均有
  provider-free 测试。
- 静态清单同时检查生产启动调用链无 database import/SQL，Admin 失败无回退。
- 真实 CLI 与正常本机业务验收在全项目 acceptance 阶段执行，本阶段测试不得冒充真实验收。

本阶段确定性验证：

| 命令 | 工作目录 | 结果 |
| --- | --- | --- |
| `PYTHONPATH=. .venv/bin/pytest -q tests/test_admin_claude_plugin_data.py tests/test_claude_plugin_builtin_reconcile.py tests/test_install_service_reinstall.py tests/test_claude_plugin_pipeline.py tests/test_claude_plugins_router.py tests/test_admin_workspace_plugin_pack.py tests/test_workspace_init_surfaces.py` | Dream `backend` | exit 0；99 passed，25 subtests passed |
| `python3 -m compileall -q ...` | Dream worktree | exit 0 |
| `rg` production Claude Plugin table/constructor inventory | Dream worktree | exit 0；启动 installation/ref SQL 已关闭；剩余生产命中仅 `workspace_packer.py` legacy compatibility wrapper，进入后续独立阶段 |

## 发布与回滚

先部署包含 Registry183-184 的 Admin，再部署 Dream 消费者。回滚 Dream 只能回到仍受 Admin 支持的
Registry175-182 版本；不得恢复数据库凭据或启动 SQL。若 Admin capability 缺失，Dream 继续启动但
builtin 对账失败，日志保留 package spec 与业务错误码供修复部署配置。

<!-- [Sync] 2026-09-16: close builtin startup SQL through Admin Registry183-184. -->

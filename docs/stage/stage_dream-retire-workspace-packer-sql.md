<!-- [Input] Registry106 workspace-plugin DTO consumer, production call graph, legacy packer SQL compatibility entry. -->
<!-- [Output] Dream production SQL retirement plan, test-fixture boundary and verification commands. -->
<!-- [Pos] Workspace plugin metadata authority closure after Admin DTO/ORM adoption. -->
<!-- [Sync] 2026-09-16: remove the last database-handle entry from the production workspace packer. -->

# Dream Workspace Plugin Packer SQL 退役阶段

## 本轮优化指令

**Optimized Prompt:**

确认 Dream `workspace_packer.py` 的所有生产调用者与测试调用者。生产路径只接受
Registry106 严格 DTO 经过 owner/provider 转换后的惰性 metadata loader；删除 production
模块内的 SQL、数据库连接句柄、Deck ref join 和 server adapter installation 查询。把仍用于
历史 SQLite filesystem 测试的数据装载逻辑移入 `backend/tests/**`，不得成为运行时依赖。
保持 artifact digest 校验、immutable copy、workspace init、surface materialization、frozen
manifest、repair receipt、Runtime venv 和共享文件系统边界原样。增加源码围栏和定向回归，
证明生产 packer 没有数据库入口，且 Registry106 正常/Story/frozen 流程不变。

**Optional Enhancers:** 无；本阶段不增加 API、表、migration 或配置。

## 目标与已有证据

- 目标：Dream 生产 workspace pack 仅消费 Admin Registry106 DTO；任何 SQL/ORM/连接池均不在
  `backend/services/claude_plugin/workspace_packer.py` 中出现。
- 已有证据：`backend/claude_agent/service.py` 是唯一生产调用者，调用
  `pack_workspace_plugins_with_refs_loader`；loader 从
  `AdminDeckWorkspacePluginsProvider.workspace_plugins` 取得 actor、Thread、profile、Deck 绑定后的
  DTO。
- 旧 `pack_workspace_plugins(db, ...)` 只由 SQLite 技术测试使用，没有生产调用者。

## 所属项目、责任与依赖

| 项目 | 责任 | 依赖 |
|---|---|---|
| Admin | Registry106 DTO → Service → typed Drizzle Repository，权限过滤与排序 | 已实现并发布在当前 Admin 工作分支 |
| Dream | DTO 消费、artifact 校验、共享文件复制、manifest/init/repair | 依赖 Registry106 capability 和 service-persistence grant |
| 本阶段 | 删除 Dream production SQL 兼容入口并保留测试覆盖 | 不改变 Registry106 hash、路由或数据库 schema |

## 修改范围

- `backend/services/claude_plugin/workspace_packer.py`：删除数据库参数、SQL loader 和兼容 wrapper。
- `backend/tests/claude_plugin_workspace_fixture.py`：保存历史 SQLite fixture adapter，只向生产
  loader seam 提供 Registry106 形状的数据。
- workspace/plugin 相关测试：改用测试 adapter，并增加 production source fence。
- 目录文档：同步生产 ownership 和测试 fixture 边界。

## 接口、数据库与配置

- API：无新增；继续使用 Registry106。
- DTO：无变更；Dream packer 接受已经校验和授权的 ref 字典投影。
- 数据库：无 schema/migration；生产 SQL 删除，SQLite 仅留在明确命名测试 fixture。
- 配置：无新增；artifact store、runtime root、workspace root 继续使用已有服务端配置。

## 保持不变的行为

- fresh workspace 在 metadata loader 返回 ready refs 后按顺序校验与复制 artifact。
- Story profile 的 server adapter 由 Admin DTO 决定，Dream 仅追加 ready ref 并去重。
- frozen workspace 在任何 metadata I/O 前读取 manifest，校验/修复派生副本，不切换版本。
- workspace init、`.dream` surface、managed venv、receipt、符号链接与路径限制保持不变。
- Agent Runtime、EventBus、SSE、turn/resume/cancel 和 `CLAUDE_CODE_TMPDIR` 不受影响。

## 正常流程、失败与状态转换

1. Agent service 以 actor/Thread/profile 请求 Admin Registry106。
2. Admin 完成权限过滤与 typed Drizzle 查询，返回 strict DTO。
3. Dream 校验 DTO 绑定并将 refs 交给 packer loader。
4. Packer 校验 ready 状态和 artifact digest，写 immutable workspace copy 与 manifest/receipt。
5. Admin 不可用、capability 缺失、DTO 绑定不匹配或 ref 非 ready 时 fail closed；禁止数据库回退。
6. frozen manifest 路径不调用 Admin；损坏派生副本按既有规则修复，版本不变。

## 验收标准与命令

- `workspace_packer.py` 不含 `db.execute`、plugin table 名或数据库参数 wrapper。
- Registry106 标准、Story adapter、去重和 frozen no-I/O 测试通过。
- 历史 filesystem pack 测试通过 test-only adapter，输出与错误码保持不变。
- Python compile 通过；生产源码扫描没有 Claude Plugin table SQL。

建议命令：

```bash
cd backend
PYTHONPATH=. .venv/bin/pytest -q \
  tests/test_admin_workspace_plugin_pack.py \
  tests/test_claude_plugin_pipeline.py \
  tests/test_workspace_init.py \
  tests/test_workspace_init_surfaces.py \
  tests/test_real_cli_drama_forge.py
PYTHONPATH=. .venv/bin/python -m compileall -q services/claude_plugin tests/claude_plugin_workspace_fixture.py
```

## 风险与回滚

- 风险：未跟踪测试仍导入旧 wrapper。处理方式是把已跟踪测试切到 test-only adapter；不恢复生产
  DB 入口。
- 风险：fixture adapter 与 Registry106 DTO 形状漂移。生产 Registry106/provider-free 测试是契约
  oracle；SQLite adapter 只支持历史 filesystem 测试。
- 回滚只回滚本阶段 production 删除和测试 adapter；不回滚 Registry106、Admin ORM 或数据库
  所有权。

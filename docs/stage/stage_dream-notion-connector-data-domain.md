<!-- [Input] Admin Registry148-168, Dream Notion orchestration, OAuth actor and scheduled-sync service identity. -->
<!-- [Output] Executable Dream consumer plan and verified DTO-only persistence closure. -->
<!-- [Pos] Notion connector cross-project data migration stage. -->
<!-- [Sync] 2026-09-16: implement and validate the Dream consumer. -->

# Dream Notion Connector 数据域迁移

## Optimized Prompt

You are the Dream-side engineer for the Notion connector data-domain migration.
Use the already-published Admin Registry148-168 contract as the only database
boundary. Replace Dream SQL, pools, repositories, transactions and thread-list
database reads with strict Pydantic DTO calls through `AdminDataClient`. Bind
browser operations to the current Admin OAuth actor, bind scheduled sync to the
`connectors:sync` service identity, and bind Agent workspace projection to the
current server-persistence grant. Keep Notion CLI execution, credential files,
canonical snapshot files, sync orchestration, thread workspace projection and
Agent Runtime in Dream. Preserve route payloads, sync-policy state transitions,
failed-reauth LKG behavior, SSE and filesystem permission/symlink rules. Writes
must not retry after an unknown result; recover only the original request receipt.
Produce source changes, folder documentation, provider-free contract tests and a
production-source scan proving the migrated modules contain no database path.

## 目标与已有证据

- Admin commit `a64508a` provides 16 OAuth operations and five
  `connectors:sync` operations through strict Zod DTO → service → typed Drizzle
  Repository. Resource replacement and snapshot publication each retain one
  Admin transaction.
- Dream previously owned `backend/notion/store.py` PostgreSQL SQL/UOW and
  `credentials.py` called `database.list_chat_threads` during disconnect.
- The target result is a DTO-only Dream adapter. Admin continues to own the five
  existing Drizzle tables and `dream.schema.unified.v1`; this stage needs no
  migration.

## 项目、责任与依赖

| 项目 | 责任 | 依赖 |
|---|---|---|
| Admin | 权限过滤、ORM Repository、事务、capability、原始 receipt | Registry148-168 已发布 |
| Dream | OAuth/background/turn authority composition、Notion 编排、CLI、文件投影 | Admin operation hash 与 schema capability |
| 共享文件系统 | actor 凭据、canonical snapshot、thread projection | 保持 `0700`、规范化路径和符号链接拒绝 |

## 修改范围与接口

- `services/admin_data/notion_connector_data.py` 固定 21 个操作 hash、两项
  schema capability、严格输入输出和未知写回执。
- `notion/store.py` 保留历史 Store 方法形状，但每个方法只构造 DTO 并调用
  Admin；没有 SQL、ORM、连接池、DDL 或数据库 fallback。
- `routers/notion.py` 从当前 `AdminRequestActor` 构造用户 Store；生命周期只
  构造后台 Store。
- `AdminTurnPersistence` 使用当前 Thread/Run grant 构造短生命周期 Store；
  Agent turn 不获取 PostgreSQL 凭据。
- `credentials.py` 用 actor 私有的 thread 投影索引完成注销清理，保持文件
  系统权限和越界检查。

## 保持不变的业务行为

- create → login → poll → discover → select → immediate sync → policy update。
- failed reauthorization 保留先前有效凭据；空选择清除当前 snapshot。
- 后台同步逐 connector 隔离失败，Agent turn 只投影 LKG，不执行远程同步。
- `.notion-home`、`.notion`、credential/snapshot 根目录、Runtime Bash 与
  shared filesystem 仍由 Dream 管理。

## 失败处理与状态转换

- capability 缺失、Admin 不可用、身份不匹配或输出不合法均 fail closed，
  路由返回稳定错误，不回退数据库。
- 用户写使用原 OAuth receipt；后台写使用原 request ID 与 connector ID
  receipt。两者都不重发未知 POST。
- pending/authenticated/error/expired 以及 sync policy 的
  default/desired/effective/revision/LKG 转换保持原实现。

## 验收标准与命令

1. DTO、Store、路由、后台和 Agent turn 定向测试通过。
2. Notion production modules 不再 import `database`、psycopg、pool、UOW 或
   包含 SQL。
3. provider-free 路由测试经过真实 `AdminDataClient` HTTP DTO 序列化，并
   验证 OAuth 与 background 请求身份分离。
4. Markdown 索引和相对路径校验通过。

验证命令：

```bash
PYTHONPATH=backend backend/.venv/bin/python -m pytest -q backend/tests/test_admin_notion_connector_data.py backend/tests/test_notion*.py backend/tests/test_admin_turn_persistence.py backend/tests/test_claude_agent_service.py
PYTHONPATH=backend backend/.venv/bin/python -m py_compile backend/notion/*.py backend/routers/notion.py backend/services/admin_data/notion_connector_data.py
rg -n "import database|psycopg|PostgresPool|PostgresUnitOfWork|SELECT |INSERT |UPDATE |DELETE FROM" backend/notion backend/routers/notion.py backend/services/admin_data/notion_connector_data.py
```

## 设计评审结论

方案满足认证与数据库访问归 Admin、DTO → service → ORM Repository、Dream
保留业务编排与文件系统的目标。无需新增表、队列、控制通道或第二套用户/
Session 体系。主要风险是 authority 误用与未知写重复提交，已通过构造时身份
约束、capability hash 和原始 receipt 测试覆盖。

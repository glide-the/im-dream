# Dream Deck Plugin control consumer

> 状态：实现与聚焦技术验证完成；跨项目完整业务验收仍由总协调任务跟踪。
>
> Admin provider：Registry170-174，commit `63532a5`，branch `codex/admin-auth-data-provider`。

## 背景与问题

Dream 的公开 Deck Plugin 管理路由此前通过 `backend/services/deck/admin_gateway.py` 和 `backend/services/deck_plugin/installation_service.py` 直接执行 SQL、事务和安装状态转换。这与“Admin 统一拥有数据库访问，Dream 只消费业务接口”的目标冲突，也让同一生命周期在 Dream 与 Admin 各有一套持久化实现。

## 目标与边界

- Admin 负责 Workspace/instance 权限、release/installation/materialization 查询、生命周期判断、revision 并发控制、receipt、audit 和单事务写入。
- Dream 负责现有 `/api/deck-plugins/**` 产品路由、权限反馈、共享文件系统中的服务器发布制品解析、manifest 与 sha256 校验。
- 浏览器不提交 actor、数据库、表、列、SQL、事务、缓存路径或物化状态。OAuth actor 由 Dream 的认证依赖传入 Admin 客户端。
- Admin 不可用、capability 不匹配或写结果未知时 fail closed；Dream 不回退 PostgreSQL。

## 本轮 Prompt Architect 执行指令

**目标与证据**：Admin commit `63532a5` 已发布五个 DTO → Service → Drizzle Repository operation；Dream 旧网关仍导入 `database` 和 `InstallationService`。

**项目与依赖**：Dream 消费端依赖 Admin Registry170-174 与 `identity.better-auth.v1`、`dream.schema.unified.v1`、`dream.runtime.local-placement.v1` 三项 exact capability。

**修改范围**：新增严格 Pydantic DTO consumer；将路由绑定到当前 OAuth actor；把本地网关收敛为 plan → 本地证据 → apply；删除零生产调用的安装 SQL service 及旧数据库夹具；同步目录合同与测试。

**保持行为**：公开路径、请求/响应产品形状、Workspace/instance scope、install idempotency、enable/disable/upgrade/rollback/approve/reject/reconcile/uninstall、共享制品目录规则保持；Agent Runtime、SSE、EventBus、turn/resume/cancel、资源策略和临时目录协议不变。

**失败与状态**：source/release/transition/concurrency/retention 错误映射为已有公开错误；本地目录缺失、manifest 无效或 digest 不匹配在 apply 前失败；未知 apply 只读原 request receipt，不重发。

**验收**：严格 DTO 拒绝 actor/SQL/数据库和动作外字段；operation/hash/schema capability 与 Admin 产物一致；路由传递 OAuth actor 与 Workspace scope；生产源不再引用 `InstallationService`；聚焦 pytest、静态编译、格式检查和数据库入口扫描通过。

## 概念与规则

| 层 | 输入 | 输出 | 失败处理 |
| --- | --- | --- | --- |
| Public route | 当前认证用户、产品 request | 原 Deck Plugin JSON 投影 | 权限/作用域错误返回现有公开结构 |
| Dream DTO client | OAuth bearer、闭合 command | plan、view、readiness、operation | capability/hash/DTO 错误 fail closed |
| Dream local verifier | plan 中的 immutable runtime target | digest、materialized digest、cache ref、manifest evidence | 目录越界/缺失、manifest/digest 错误时拒绝 apply |
| Admin service | OAuth principal、plan、evidence | 原子 operation receipt | Repository/事务/revision/权限失败由 Admin 返回 |

install 的公开 `idempotency_key` 先计算为固定、安全的 Admin request ID；相同 key 得到相同 request ID，原字符串不写入协议路径或日志。其他 lifecycle 写入每次生成独立 UUID。所有写入都先读取 Admin plan；需要本地证据时按 plan 顺序逐项验证，然后一次调用 apply。

## 接口与状态

| Registry | Kind | Dream DTO | 作用 |
| --- | --- | --- | --- |
| 170 `deck-plugin-control.list` | read | scope | 当前安装与 Runtime 状态 |
| 171 `deck-plugin-control.version` | read | scope + plugin/version | release/installation 视图 |
| 172 `deck-plugin-control.readiness` | read | scope + plugin | 当前 Runtime readiness |
| 173 `deck-plugin-control.plan` | read | discriminated lifecycle command | immutable revision、target 与 evidence 要求 |
| 174 `deck-plugin-control.apply` | write | plan + ordered evidence | Admin 单事务生命周期提交与 receipt |

`install`、`upgrade`、`rollback`、`approve_upgrade` 与 `reconcile` 可要求 Runtime evidence。`enable`、`disable`、`reject_upgrade`、`uninstall` 是否需要证据由 Admin plan 决定，Dream 不自行猜测。`upgrade_pending` 继续表示等待能力批准；批准完成后才切换目标版本。

## 影响与验收记录

- `backend/services/deck/admin_gateway.py` 无 `database`、SQL、ORM 或 `InstallationService` import。
- `backend/services/deck_plugin/installation_service.py` 及仅验证该旧实现的测试已删除。
- `backend/services/admin_data/deck_plugin_control_data.py` 固定五个 contract hash、三项 schema capability，并实现原 receipt 恢复。
- `backend/routers/deck_plugins.py` 继续提供原公开路由，所有 Admin 调用使用认证依赖产生的 `AdminRequestActor`。
- provider-free 聚焦测试覆盖 DTO 闭集、注册、plan identity、未知写 receipt、本地 evidence、公开路由 actor/scope 与 local source 拒绝。

实际命令与结果（cwd：Dream worktree）：

- `PYTHONPATH=backend uv run --native-tls --project backend --frozen --with pytest==9.1.1 --with pytest-asyncio python -m pytest backend/tests/test_admin_deck_plugin_control_data.py backend/tests/test_deck_plugin_admin_integration.py backend/tests/test_admin_request_auth.py backend/tests/test_admin_deck_plugin_binding_data.py backend/tests/test_deck_plugin_binding.py backend/tests/test_deck_plugin_compatibility.py backend/tests/test_deck_plugin_lock.py backend/tests/test_deck_plugin_manifest.py backend/tests/test_runtime_plugin_reconcile.py backend/tests/test_postgres_runtime_sql_boundaries.py backend/tests/test_postgres_runtime_services_integration.py -q`：exit 0，`78 passed, 1 skipped, 16 subtests passed`；skip 是未提供显式 `TEST_DATABASE_URL` 的隔离 PostgreSQL 用例。
- Deck 公开路由和默认 Workspace 兼容修正后，两个路由套件单独重跑：exit 0，`32 passed`。
- `ruff check --select E4,E7,E9,F`（本阶段 Python 文件）：exit 0；`python -m py_compile`：exit 0；`git diff --cached --check`：exit 0。
- 后端全量首次运行：`3635 passed, 31 skipped, 26 failed, 673 subtests passed`。其中 7 个旧 Deck fake 签名已修正并由上述 32 项重跑关闭。其余失败来自此前已存在的 Claude 路由数据库 mock、安装 Runtime `0.1.10` 与仓库固定 `0.1.9` 不一致、直接调用 FastAPI 依赖的旧测试、相对 cwd 测试及 worktree 缺少 `vendor/drama-forge` 资产；这些不改变本阶段聚焦通过结论，也不能据此声明总任务全量验证完成。

## 发布与回滚条件

先部署 Admin provider 与 capability catalog，再部署 Dream consumer。若 Admin 未广告任一 operation/schema capability、返回 DTO 不匹配或不可用，Dream 返回明确失败，不启用旧 SQL 路径。回滚 Dream consumer 前必须确认回滚版本仍与当时 Admin 契约兼容；不得通过恢复 Dream PostgreSQL 凭据作为运行时降级方案。

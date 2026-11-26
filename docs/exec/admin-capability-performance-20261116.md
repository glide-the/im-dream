<!-- [Input] 已授权 P0 改造、前轮请求评审与 Admin/Dream 现有公开合同。 -->
<!-- [Output] 三项实施状态、技术证据、拉取请求及分支交付。 -->
<!-- [Pos] 跨仓库执行记录；设计基线保留于 architecture 专项评审。 -->
<!-- [Sync] 2026-11-16: 实施 capability 批量查询、事务去重与目录错误归属。 -->
# Admin capability 性能改造执行记录

## 背景与问题

[11月15日专项评审](../architecture/admin-request-boundary-review-20261115.md)保留原调用计数、建议和图示。用户本轮授权三项 P0 的实现、验证、提交、拉取请求与合并；既有 TypeScript 迁移文档改动保留。

## 目标与边界

Admin 向 `main`、Dream 向 `develop` 分别提交，使用 `codex/` 分支。范围为请求内 data ledger 批量读取、原事务 requirement 去重、Dream 目录错误分类。后续 TypeScript 迁移、业务聚合、认证重构、资源准入和部署保持原边界。验证使用无模型、无真实数据库的技术合同。

## 概念与规则

- Admin 继续分别使用 auth/data 显式连接。auth ledger 响应保持；data ledger 一次批量查询，以请求内 Map 比较完整要求并保留原 operation 顺序。事务内去重要求；同名不同 version/hash 冲突拒绝，校验先于原 handler，原锁与权限保持。
- [request_auth.py](../../backend/services/admin_data/request_auth.py) 移除外层重复就绪标记，认证复用客户端 `capabilities_snapshot`。Workflow、turn persistence、Gateway、Editor 四处组合路径收到普通业务错误时保留健康目录；明确 `ADMIN_CAPABILITY_UNAVAILABLE` 进入目录恢复。
- [client.py](../../backend/services/admin_data/client.py) 对已关联的 `AUTH_SCHEMA_NOT_READY`、`DREAM_DATA_SCHEMA_NOT_READY` 和明确操作缺失 `OPERATION_UNAVAILABLE` 清空目录。目录初始化/强制刷新在取数前清空，获取、解析与认证元数据验证失败继续关闭。普通业务 403、409、503、504 按原错误返回，HTTP status 不作为目录失效依据。
- 原写操作仅派发一次；原 request ID、`outcome_unknown` 与 receipt 查询保持。目录失效后可用原 ID 查询 receipt，恢复目录不会重放业务写入。

## 验证与交付

技术回归覆盖目录一致性、缺失/version/hash、查询异常、重复/冲突 requirement、四处业务错误零额外目录请求、真实目录失败恢复及未知写入原 receipt。未运行真实模型、真实业务验收、部署或服务重启。

Admin 对应记录：[批量校验执行记录](../../../ink-admin-memory/docs/exec/capability-batch-checks-20261116.md)。

### Dream 命令回执

工作目录 `backend`，均由 `luna_test_runner` 执行：

| 命令 | 退出码 | 关键输出 |
| --- | ---: | --- |
| `PYTHONPATH=. .venv/bin/python -m pytest tests/test_admin_request_auth.py tests/test_admin_data_boundary.py tests/test_admin_workflow_data.py tests/test_admin_delegation.py tests/test_admin_editor_runtime.py tests/test_admin_turn_persistence.py -q` | 0 | 最终 311 passed in 8.00s |
| `.venv/bin/python -m compileall -q services/admin_data/client.py services/admin_data/request_auth.py` | 0 | 无错误输出 |

初次 305 项、补充目录漂移后 309 项均通过；最终加入具名操作缺失和普通实体 404 对照后为 311 项。既有后台 CI 仅执行远端构建，仓库无独立 Python lint/typecheck 配置。本机无 Docker 构建或业务服务操作。原始日志为 `/tmp/ink-capability-dream-validation-20261116/`。

### 扩展检查与基线

`PYTHONPATH=. .venv/bin/python -m pytest tests/test_admin_*.py -q` 退出 1：1586 passed、6 subtests passed、4 failed。失败节点为：

- `test_admin_deck_default_workspace.py::test_profile_failure_stops_instead_of_defaulting_role[result4-504]`
- `test_admin_deck_version_routes.py::test_capability_refresh_failure_can_recover_on_next_authenticated_request`
- `test_admin_picture_history_routes.py::test_admin_transport_failure_is_explicit_and_never_uses_database`
- `test_admin_preflight_routes.py::test_timeout_keeps_same_request_id_without_retry`

在自有 detached worktree `/tmp/ink-dream-capability-baseline-20261116`、原 `origin/develop / 37a07dab79d5312e1126116e15bb886ff9bf1a3c` 的 `backend` 下执行：

```bash
PYTHONPATH=. /Users/dmeck/project/ink-dream-memory/backend/.venv/bin/python -m pytest tests/test_admin_deck_default_workspace.py::test_profile_failure_stops_instead_of_defaulting_role tests/test_admin_deck_version_routes.py::test_capability_refresh_failure_can_recover_on_next_authenticated_request tests/test_admin_picture_history_routes.py::test_admin_transport_failure_is_explicit_and_never_uses_database tests/test_admin_preflight_routes.py::test_timeout_keeps_same_request_id_without_retry -q
```

退出 1：相同 4 failed、4 passed in 1.13s。日志 `baseline-four.log` 与 `admin-consumers.log` 对照确认：profile/picture/preflight 的只读失败保留同 request ID 后有界重试一次；目录 ConnectError 在第二次只读请求成功。上述测试原有单次断言保持本轮范围之外，未修改传输重试或业务合同。

### 文档与原改动保留

`python3 /tmp/ink-admin-request-audit-20261115/docs/inventory-links-check.py` 退出 0：5 文件、62 条引用、零失效；`node /tmp/ink-admin-request-audit-20261115/docs/mermaid-browser-check.mjs` 退出 0：3 幅 Mermaid 解析和渲染通过。使用本机 Chrome 后关闭自有浏览器。

11月15日评审原文完整保留，仅追加 Sync 和本轮实施段；两份既有 `docs/design/claude-agent/` 文档改动与交接前 patch 完全一致，继续留在工作区。两仓源码头、目录索引与执行记录路径已核对。

Dream 拉取请求：[PR #106](https://github.com/glide-the/im-dream/pull/106)。Admin 完整本地 unit 为 2660 passed、37 skipped；目录/事务定向为 22 passed；TypeScript 与 2 项既有 API-only Playwright 通过。CI 状态及合并提交以对应拉取请求为准。

Admin 拉取请求：[PR #57](https://github.com/glide-the/dream-im-platform/pull/57)，目标 `main`；Dream PR #106 目标 `develop`。Admin 先合并，Dream 随后合并；两者保持协议兼容。合并与本地默认分支同步由本次授权执行，提交与实时检查见拉取请求。

最终 `python3 /tmp/ink-capability-docs-final-20261116.py` 退出 0：原评审 62 条引用及两份执行记录 11 条引用均有效，目录索引与原分析全文保留检查通过；Mermaid 原文保持。

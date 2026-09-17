<!-- [Input] Registry183-184 builtin reconciliation, current builtin artifact verifier and zero-caller SQL seed. -->
<!-- [Output] Dream builtin plugin filesystem-only ownership and SQL retirement evidence. -->
<!-- [Pos] Claude Plugin closure after Admin owns installation/release/ref persistence. -->
<!-- [Sync] 2026-09-16: delete legacy release/lock/ref seeding from Dream. -->

# Dream Builtin Plugin SQL 退役阶段

## 本轮优化指令

**Optimized Prompt:**

确认 `backend/services/deck/builtin_plugin.py` 的生产调用只需要受控 source ref、本地目录和内容
digest。删除没有生产调用者的 built-in Deck Plugin release/lock/ref seed 与 legacy repair SQL，
以及仅为这些函数存在的 manifest、时间、UUID 和数据库模型代码。保留 Admin Registry183–184
启动 reconcile、Registry170–174 plan/apply 和 Dream 本地 artifact evidence 行为。增加 source fence，
验证 Admin 仍接收相同 path/digest/manifest evidence。不得新增 migration、fallback 或固定数据库连接。

**Optional Enhancers:** 后续清理 Dream `database.py` 时直接删除这些旧 helper 的历史导出；本阶段不
改 Registry hash。

## 目标与证据

- `admin_gateway.py` 生产调用仅使用 `resolve_builtin_source` 与 `plugin_artifact_digest`。
- `seed_builtin_deck_plugin`、legacy repair 和 manifest builder 没有生产或测试调用者。
- Admin Registry183–184 已根据 active release manifest 确保 installation/ref；Dream 启动只执行
  Admin 返回的本地 install plan。

## 修改与边界

- `builtin_plugin.py` 仅保留四个稳定常量、目录解析、digest 和 source ref 解析。
- release、runtime lock、Deck ref、事务和并发冲突继续由 Admin DTO → Service → typed Drizzle
  Repository 处理。
- 共享文件系统位置、digest 算法、Admin evidence DTO、CLI/runtime 和启动失败隔离不变。
- 无 API、DTO、配置、schema 或 migration 变化。

## 状态与失败处理

1. Admin plan 返回 server-published builtin source 和预期 digest。
2. Dream 解析唯一受控 source ref，读取 repository plugin tree，计算相同 digest。
3. path 缺失、空目录、manifest 缺失或 digest 不匹配继续 fail closed。
4. release/ref 缺失由 Registry183–184 ensure/report 处理，禁止 Dream SQL 回退。

## 验收

- production builtin module 不含 DB 参数、SQL、release/lock/ref table 名或 seed function。
- Deck Plugin Admin provider-free integration 验证相同 cache path、digest、manifest 和 apply evidence。
- Claude Plugin builtin reconcile 回归验证启动路径仍由 Admin 计划驱动。
- compileall 和 source scan 通过。

```bash
cd backend
PYTHONPATH=. .venv/bin/pytest -q \
  tests/test_deck_plugin_admin_integration.py \
  tests/test_claude_plugin_builtin_reconcile.py \
  tests/test_claude_plugins_router.py
PYTHONPATH=. .venv/bin/python -m compileall -q services/deck services/claude_plugin
```

## 风险与回滚

- 风险仅限历史离线调用者依赖 seed；当前全仓调用图为零，现行 Admin reconcile 是唯一写入路径。
- 回滚不得恢复 Dream 生产写库；如需历史 fixture，应放在 `backend/tests/**`。

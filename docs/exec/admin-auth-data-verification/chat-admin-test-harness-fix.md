<!-- [Input] Previous stale Chat route test failure, committed test-only correction and root independent rerun. -->
<!-- [Output] Exact commit/tree and before/after deterministic pytest evidence. -->
<!-- [Pos] Dream technical regression receipt; no database, network, Google, model or normal-account action. -->
<!-- [Sync] 2026-09-15: preserve the stale-harness diagnosis and successful typed Admin fake rerun. -->

# Chat Admin 依赖测试 harness 修复

- Dream commit: `626747ffb0c4a414b69d9d33dc89570dc59065a2`
- Tree: `5117a23b60af54901d8e85ef1253e06d196d5ae6`
- Subject: `Update Chat route tests for Admin dependencies`
- Scope: `backend/tests/test_server_claude_agent.py` 与该文件的目录索引行；生产代码和既有 Plugin 修改未进入提交。

## 原失败

工作目录 `/Users/dmeck/.codex/worktrees/ef6e/ink-dream-memory`。同一五文件命令首次实际退出码为 1：244 tests passed、27 failed、9 subtests passed。27 个失败全部来自 `backend/tests/test_server_claude_agent.py` 仍 patch 已移除的 `route_module.database` Chat helper，或直接调用路由时遗漏显式 `chat` 依赖。该结果判定为测试 harness 落后于已经完成的 Chat Admin 接口迁移，不是生产业务回归。

## 修正与独立复验

```text
PYTHONPATH=backend /Users/dmeck/project/ink-dream-memory/.venv/bin/python -m pytest -q backend/tests/test_admin_turn_persistence.py backend/tests/test_claude_agent_service.py backend/tests/test_claude_agent_thread_factory.py backend/tests/test_server_claude_agent.py backend/tests/test_session_projection_broker.py
```

- cwd: `/Users/dmeck/.codex/worktrees/ef6e/ink-dream-memory`
- exit: `0`
- result: `270 passed, 13 subtests passed`
- elapsed: `12.29s`
- only warnings: existing FastAPI `on_event` deprecations

修正后的 direct Chat tests 使用 `AdminRequestActor`、typed Admin Chat DTO fake、Admin turn-persistence owner 和 SystemConfig operation fake。文件中剩余两处 `route_module.database.get_db` mock 属于仍待迁移的 Deck Chat Context，未被伪装成 Chat 数据接口已经关闭。

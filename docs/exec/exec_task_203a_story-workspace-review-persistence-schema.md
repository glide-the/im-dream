# Exec Report: task_203a - Character / Scene 审阅持久化 Schema 与 Canonical Contract

## 1. 执行上下文

- Task ID: `task_203a`
- Execute Issue: [SUO-323](/SUO/issues/SUO-323)
- 关联裁决 / Task: [SUO-316](/SUO/issues/SUO-316), [SUO-317](/SUO/issues/SUO-317)
- 关联设计稿: `docs/design/story-workspace/product-scope-and-navigation.md` §3.1 / §4.5.1–4.5.4；`docs/design/story-workspace/product-scope-and-navigation.md` §6.1
- 关联 Stage: [SUO-319](/SUO/issues/SUO-319), [SUO-322](/SUO/issues/SUO-322), `docs/stage/stage_story-workspace.md` §14
- 执行 Agent: `ExecTaskAgent` (`2a7a15fe-2ebb-4dc5-91a8-48ae2bcc5471`)
- 执行时间: `2026-08-01 22:40 CST`
- Checkout: 本 heartbeat 由 harness 为独立 [SUO-323](/SUO/issues/SUO-323) 预先 claim；未重复 checkout
- 下游: [SUO-309](/SUO/issues/SUO-309) 保持 blocked；本任务未修改或释放它

## 2. TASK-REQUIREMENT-FORMAT.md 填充摘要

- 模板路径: `docs/task/TASK-REQUIREMENT-FORMAT.md`（只读，未修改）
- 填充副本: `$PAPERCLIP_RUN_SCRATCH_DIR/TASK-REQUIREMENT-SUO-323-task_203a.md`
- 填充副本 SHA-256: `f647cbddeece74475e65f35b9c3ad117bb816b4b67835b10ef8b2ca8d2e84681`
- 占位符检查: `rg '\{\{|\}\}' <filled-copy>` 无结果
- 输入 Issue: [SUO-323](/SUO/issues/SUO-323)
- 输入 Task: `docs/task/task_203a_backend_story-workspace-review-persistence-schema.md`
- 填充后的执行目标: 仅实现 character / scene 四列 fresh DDL、幂等 legacy migration、canonical v1.1.0、focused tests 与本报告
- 关键约束: 五路径闭集；保留脏工作树；不写 router/service/server/frontend/design/issue/task/stage/runtime DB；不自行释放下游
- 验收条件: `AC-203A-01`～`AC-203A-09` 全量带入，未删减

首次写入前冻结 Gate：

```text
47d6290c29b0297fed2d5256a9854c2224ca93575764e277951940f4f17e0810  backend/database.py
729  0  backend/database.py
```

结果与 Issue 指定值精确匹配，允许进入 execute。

## 3. 模型生成的执行任务

- 任务目标: 使 fresh 与 legacy SQLite 在 character / scene 的四个审阅持久化字段上收敛，并把唯一 canonical owner 升级到 v1.1.0。
- 实现范围: 两表 DDL、受控 savepoint migration、schema/constraint 后验验证、canonical enum/字段/常量/request validation、focused tests。
- 文件范围: 仅 §4 五个文件。
- 实现步骤: fresh DDL → PRAGMA introspection / fixed-order ALTER → schema + CHECK 后验验证 → dataclass additive contract → boundary tests → formal verification。
- 验证方式: py_compile；20 个 focused unittest；diff check；SHA-256；scoped path review。

## 4. 实现变更记录

| 文件 | 操作 | 说明 |
|---|---|---|
| `backend/database.py` | update | character / scene fresh DDL 新增 `status`, `review_notes`, `confirmed_at`, `archived_at`；新增 savepoint 内的幂等 migration，按固定顺序 introspect/add/re-verify；验证 type/nullability/default 与两个 CHECK |
| `backend/story_workspace/contracts.py` | update | contract version `1.1.0`；新增 `StoryWorkspaceAssetStatus`、`STORY_WORKSPACE_REVIEW_NOTES_MAX_LENGTH`、两资源四字段；两 request dataclass 复用常量校验 2000 Unicode 字符边界；更新 `__all__` |
| `backend/tests/test_database.py` | update | 更新冻结 Schema matrix；新增 fresh defaults、完整 legacy Schema 收敛/backfill、migration idempotency、status/notes constraints、direct DB round-trip tests |
| `backend/tests/test_story_workspace_contracts.py` | update | 新增 v1.1.0 enum/字段/default/type/`__all__` 与 `None`/2000/2001 request boundary tests；保留旧构造与 Pydantic 行为测试 |
| `docs/exec/exec_task_203a_story-workspace-review-persistence-schema.md` | create | 执行上下文、模板摘要、变更、AC 证据、hash、风险、回滚与完成报告 |

工作树处理：执行前已存在大量其他 task 的 tracked/untracked 变更，其中四个 backend Allowed 文件亦承载已冻结前置工作。本任务未 reset、cleanup、overwrite 或重构这些既有内容；`backend/database.py` 相对 HEAD 的既有 `729/0` 增量被完整保留，本任务使总 numstat 变为 `820/0`，即在该共享基线上 additive 增加 `91/0`。

## 5. 测试与验证

### 已执行测试

```bash
python -m py_compile backend/database.py backend/story_workspace/contracts.py backend/tests/test_database.py backend/tests/test_story_workspace_contracts.py
python -m unittest backend.tests.test_database backend.tests.test_story_workspace_contracts -v
git diff --check -- backend/database.py backend/story_workspace/contracts.py backend/tests/test_database.py backend/tests/test_story_workspace_contracts.py docs/exec/exec_task_203a_story-workspace-review-persistence-schema.md
shasum -a 256 backend/database.py backend/story_workspace/contracts.py
```

### 测试结果

- `py_compile`: PASS（4 files，exit 0）
- focused unittest: PASS（`Ran 20 tests ... OK`）
- `git diff --check`: PASS（exit 0）
- hash recompute: PASS
- 未执行测试: HTTP / browser / frontend E2E 不执行；本 task 明确禁止 route/frontend 变更，以 direct SQLite round-trip 作为持久化验证

### Hash 冻结证据

| 对象 | 变更前 SHA-256 | 变更后 SHA-256 |
|---|---|---|
| `backend/database.py` | `47d6290c29b0297fed2d5256a9854c2224ca93575764e277951940f4f17e0810` | `22db28fa6269a963c2537a85f648a00fb50e2827e22ccb5d181b581cc0edc356` |
| `backend/story_workspace/contracts.py` | `677733b190bf0de650e65fa0ebb8f2c6a75c149f2b59ae136f0b062b97c00478` | `0a1c748b7fab1e2831d1f746f6ce12b6120ec3c66c049ad8cd6e0ff882fe55e8` |

### AC 证据

| AC | 结果 | 证据 |
|---|---|---|
| `AC-203A-01` | PASS | `test_story_workspace_review_persistence_schema_contract` + generic Schema matrix 精确检查两表四列 type/default/nullability/CHECK |
| `AC-203A-02` | PASS | `test_story_workspace_asset_status_constraint` 接受 active/archived、拒绝 published/deleted；`test_story_workspace_review_notes_length_constraint` 接受 2000 个 Unicode 字符、拒绝 2001 且原值不变 |
| `AC-203A-03` | PASS | `test_story_workspace_review_persistence_migrates_legacy_rows` 比较 fresh/legacy 完整 `PRAGMA table_info` 与 foreign keys；`test_story_workspace_review_persistence_migration_idempotent` 连续运行无 Schema/row 漂移 |
| `AC-203A-04` | PASS | legacy pending/confirmed/rejected 均保留 `review_status`，四列为 active/null/null/null；未从 notes/description/updated_at 推断事实 |
| `AC-203A-05` | PASS | `test_story_workspace_review_contract_v1_1` 与 `test_story_workspace_review_request_notes_boundary`；canonical owner 保持 `backend/story_workspace/contracts.py`，无 shim/re-export |
| `AC-203A-06` | PASS | `test_story_workspace_review_persistence_round_trip` 对 character / scene 直接 DB 写入并重读四字段；未写 route、side table 或 memory fallback |
| `AC-203A-07` | PASS | 本 Agent 的 apply-patch 写入仅五个 Allowed paths；scoped diff check 通过；所有既有 Forbidden-path worktree changes 原样保留且未归入本 task |
| `AC-203A-08` | PASS | 最小命令全绿；pre/post database hash 与 canonical hash 已写入本报告，Issue comment 将同步同值 |
| `AC-203A-09` | PASS（execute gate） | 独立 [SUO-323](/SUO/issues/SUO-323) 单一指派并由 harness checkout；本 Agent 未释放 [SUO-309](/SUO/issues/SUO-309)。最终 StagePlanner readiness recheck 属后续 release gate，未被冒充为已完成 |

## 6. 风险与阻塞

- 风险: 工作树仍包含大量其他 task 的未提交变更；后续合并/回滚必须按 task-specific hunks 处理，不能对共享文件整体还原。
- 风险: Stage §14 内嵌 task 文档 digest `58940f…` 与当前只读文件实际 digest `e49a583a7b54d1cb24a1e83956f67129a824e68eea91d86aec76ee5e5ca03dbd` 不同；当前 wake payload 与文件内容的执行合同一致，且唯一显式 fail-closed database hash/numstat 双 Gate 精确通过。该文档摘要漂移留给 StagePlanner final recheck 复核，本 Agent 未修改 Task/Stage。
- 阻塞: 无当前实现阻塞。
- 未验证 / 上游后续: StagePlanner 尚未执行完成后的九项 readiness final recheck；CEOOrchestrator 尚未解除 [SUO-309](/SUO/issues/SUO-309)，本 Agent也未请求解除。

## 7. 完成状态

- [x] 已完成实现
- [x] 已完成 focused 测试
- [x] 已记录变更与 hash
- [x] 已满足 `AC-203A-01`～`AC-203A-08`
- [x] 已满足 `AC-203A-09` 的独立 execute / checkout / 不提前释放约束
- [x] 可进入 StagePlanner final readiness recheck / audit

最终 disposition 建议：将 [SUO-323](/SUO/issues/SUO-323) 标记 `done`；保持 [SUO-309](/SUO/issues/SUO-309) blocked，由 CEOOrchestrator 请求 StagePlanner 进行最终 readiness recheck。

## 8. 回滚建议

- 回滚文件: 仅本报告 §4 的五个 Allowed paths中的 task_203a 专属 hunks。
- 代码回滚: 对共享脏工作树应用 task-specific inverse patch；禁止 `git reset --hard`、整文件 checkout 或清理既有 729 行 database 增量。
- 已迁移数据库: 不在线 `DROP COLUMN`；旧代码可忽略 additive 列。若必须物理恢复，从迁移前备份还原，或创建受审计的 SQLite table-rebuild 工作单。
- 数据注意: 回滚前导出并保全合法的 `archived`、`review_notes`、`confirmed_at`、`archived_at`；不得静默改 active、删除备注或伪造时间。
- Gate: 回滚期间与回滚后均保持 [SUO-309](/SUO/issues/SUO-309) blocked；只有代码/数据库恢复到同一已验证基线且 focused tests 通过后才重新冻结 hash。

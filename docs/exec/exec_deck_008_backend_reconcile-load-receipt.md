# Exec Report: DECK-008 - ClaudeAgent 声明式 Reconcile 与 Load Receipt

## 1. 执行上下文

- Task ID: `DECK-008` / `task_deck_008_backend_reconcile-load-receipt`
- 执行 Issue: `SUO-312`
- 关联 Issue: `SUO-217` / `DECK-002` / `DECK-006`
- 关联设计稿: `docs/design/deck-plugin-voice-ink-dream-integration.md` §7.1–7.4；`docs/design/plugin-remote-interaction.md` §4.2–4.4
- 关联 Stage: `docs/stage/stage_deck-plugin-voice-ink-dream-integration.md` v1.8，Stage 2 / Wave 3
- 直接前置: `SUO-304`（task_007，done）；readiness 证据 `SUO-306`
- 执行 Agent: `ExecTaskAgent`
- 执行时间: 2026-08-01（Asia/Shanghai）
- Checkout: Paperclip harness 已为本 run 获取 single-assignee execution lock；未重复 checkout

## 2. TASK-REQUIREMENT-FORMAT.md 填充摘要

- 模板路径: `docs/task/TASK-REQUIREMENT-FORMAT.md`
- 受控填充副本: `$PAPERCLIP_RUN_SCRATCH_DIR/TASK-REQUIREMENT-task_deck_008.filled.md`
- 输入 Issue: `SUO-312` wake payload；fallback fetch 不需要
- 输入 Task: `docs/task/task_deck_008_backend_reconcile-load-receipt.md`
- 填充后的执行目标: settings/headless reconcile 主路径、受控 CLI 备选、单节点本地持久物化、不可变 Load Receipt、精确五字段 Workflow Run readiness projection
- 关键约束: 仅 `pool == environment`、`local_persistent`、`development|test`；production、多节点与临时 runtime fail closed；不创建 Session、不发送 query、不转 `running`
- 验收条件: Task §9 与 Issue handoff 验收项已逐项带入；源模板未修改

## 3. 模型生成的执行任务

- 定义严格 placement、三维状态、materialization、Receipt/entry 与 canonical digest/hash 合同。
- 注入受信 source policy、settings writer 与 headless runner，先写受控意图，再以同步环境变量完成 reconcile，严格验证 `init.plugins`。
- 注入 CLI policy/runner/audit，固定 argv、`shell=False`、1..300 秒超时、严格 JSON、限长脱敏与失败审计。
- 使用同 key 单 owner 的异步协调，消费 staged artifact 和权威 retention evidence，重算 digest 后原子发布。
- 从服务端 Workflow Run/lock、placement、materialization 与 headless evidence 生成不可变 Receipt，并提供精确五字段 reader。
- 在既有 Workflow Run 初始化后仅增量追加 task_008 四表、索引、append-only guard 与 run/receipt binding trigger。
- 以 task_008 定向测试和既有 Workflow Run/Preflight 回归验证边界。

## 4. 实现变更记录

| 文件 | 操作 | 说明 |
|---|---|---|
| `backend/models/runtime_plugin.py` | create | 严格 placement、三维状态、materialization、headless/CLI result、Receipt/entry 模型及 canonical hash/digest helpers |
| `backend/services/runtime_plugin/reconcile_service.py` | create | 受控 settings + headless reconcile、CLI allowlist/runner/audit、Receipt 生成/持久化/读取与五字段 projection |
| `backend/services/runtime_plugin/materialization_manager.py` | create | 同 key 单 owner 幂等协调、staged bytes digest 重算、权威 retention evidence、节点本地原子发布 |
| `backend/database.py` | update | 仅新增 `create_runtime_plugin_tables()`，追加 materialization/reconcile-attempt/receipt/entry 表、索引和 guard；未改写既有 Workflow Run 表或 trigger |
| `backend/tests/test_runtime_plugin_reconcile.py` | create | 9 项定向测试，覆盖 Gate、reconcile、CLI、幂等/并发物化、fail closed、Receipt 与真实 Workflow Run reader 联调 |
| `docs/exec/exec_deck_008_backend_reconcile-load-receipt.md` | create | 本 task 唯一正式执行报告 |

未修改确认：未修改 `docs/design/`、`docs/issue/`、`docs/task/`、`docs/stage/`、其他 `docs/exec/`、`frontend/`、Workflow Run/Preflight 模型/服务/测试、依赖锁与部署配置。共享树中这些路径的既有差异均未清理、覆盖或归因于本 task。

## 5. 验收结果

| 验收项 | 结果 | 证据 |
|---|---|---|
| settings 受控意图 | PASS | 精确断言 `enabledPlugins` 与受信 `extraKnownMarketplaces`；plugin/source/alias/repo 均来自 lock + policy |
| 第一条 query 前同步 headless reconcile | PASS | runner 仅暴露 reconcile 端口，固定 `CLAUDE_CODE_SYNC_PLUGIN_INSTALL=true`；结果模型固定 `completed_before_first_query=True` |
| CLI 备选控制面 | PASS | allowlisted plugin/version/marketplace source/scope；固定 argv；`shell=False`；17 秒注入超时；严格 JSON；输出限长、脱敏及成功/拒绝/错误/timeout 审计 |
| 三维状态独立 | PASS | declaration/materialization/activation 使用独立 Enum、列和状态一致性验证；失败保留 `declared/failed/inactive` |
| 物化幂等和实际 digest | PASS | canonical key 含 environment/node/plugin/version/digest/policy；并发重复共享 operation；实际 bytes 重算；证据缺失 fail closed；`os.replace` 原子发布 |
| deployment/runtime Gate | PASS | Pydantic 与服务双层限制 `pool == environment`、`local_persistent`、development/test；production/temporary/pool mismatch 拒绝 |
| 不可变 Load Receipt | PASS | Receipt/entry frozen strict 模型；数据库 update/delete trigger；保留 run/lock/digest/node/artifact/policy 与逐项 digest/evidence |
| 五字段 Workflow Run projection | PASS | reader 返回精确五 key；完整 Receipt 被 strict projection 拒绝；错 run/lock/digest/not-ready 均被现有守卫拒绝，正确 projection 可消费 |
| task_009 Session 边界 | PASS | Receipt 创建后 run 仍为 `queued`，`agent_session_id` 与 `runtime_load_receipt_id` 均为空；task_008 服务不创建 Session、不发 query、不调用状态转换 |
| 数据库增量边界 | PASS | 仅新增 task_008 函数/四表/索引/guard；既有 Workflow Run 25 项回归通过 |

## 6. 测试与验证

| 命令 | Exit code | 结果 |
|---|---:|---|
| `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m unittest backend.tests.test_runtime_plugin_reconcile -v` | 0 | 9/9 PASS |
| `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m unittest backend.tests.test_workflow_run backend.tests.test_workflow_preflight -v` | 0 | 25/25 PASS |
| Task 指定 `py_compile` 五文件命令 | 0 | PASS；`.pyc` 定向 `$PAPERCLIP_RUN_SCRATCH_DIR/pycache-task-008` |
| Task 指定 `git diff --check` 闭集命令 | 0 | PASS |
| Task 指定尾随空白 `rg` 命令 | 0 | PASS；无匹配 |
| 实现前后 `git status --short` 路径闭集 | 0 | PASS；task 新增/修改路径均在闭集内 |

测试中的 `Memory workspace config backfill skipped: No module named 'memory_workspace_defaults'` 是现有 `create_tables()` 的非阻塞提示；所有 unittest 均返回 exit code 0。

### 手动/结构证据

- CLI fake 捕获的调用为 argv 列表 `claude plugin install <controlled-id> --scope project --json`，`shell=False`，timeout=17。
- 并发相同 materialization key 仅调用 ArtifactProvider 一次，两个调用返回相同 `runtime_materialization_id`。
- Receipt 持久化后尝试 update receipt 与 delete entry 均由 SQLite append-only trigger 拒绝。
- Receipt 生成服务不触碰 Workflow Run 状态；测试仅在后续联调步骤显式调用既有 `WorkflowRunService.transition_run()` 证明 reader 兼容。

## 7. 共享工作树与路径闭集

- 实现前基线保存于 `$PAPERCLIP_RUN_SCRATCH_DIR/task_deck_008.status.before`，共 78 行。
- 基线已包含大量其他任务差异；其中 `backend/database.py` 已修改，`backend/models/` 与 `backend/services/` 已以未跟踪目录形式出现。
- 对 `backend/database.py` 仅在既有 `create_workflow_run_tables()` 之后追加独立函数，未清理、格式化或重写前序区段。
- 因 Git 会把未跟踪目录折叠为 `?? backend/models/` / `?? backend/services/`，最终同时使用全局 before/after diff 与六个授权路径的 scoped status 核验实际任务文件。
- 全局 before/after 预期新增本 task 的定向测试与正式报告；`backend/models/`、`backend/services/` 在基线中已被 Git 折叠为未跟踪目录，scoped status 明确显示三个 task_008 新文件。
- 执行期间共享树还新增了闭集外 `docs/exec/exec_task_205b_story-workspace-contract-migration.md`；该并发差异不是本 task 产出，本 Agent 未读取、修改或归因该文件。
- 最终 scoped status 仅列出六个授权路径：`backend/database.py`、三个 task_008 新实现文件、定向测试和本报告。

## 8. 风险与阻塞

- 阻塞: 无。
- 已知限域: 本次通过注入 fake 验证 Claude headless/CLI 端口合同，未调用真实 Claude Code 二进制或 marketplace；这是 Task 明确的测试隔离边界，不构成 production-ready 证据。
- 供应链: `legacy_unverified` 仅在 development/test Receipt 中原样保留；服务不会升级为 production-ready。
- rollout: 多节点、临时 runtime、共享 CAS、冷存储、restore/purge 和真实留存未实现且继续 fail closed。
- 下游 owner/action: task_009 仅消费本 task Receipt/readiness 接口，在同 node/artifact set/policy 上创建 Session 后调用既有 `queued → running` 守卫。

## 9. 完成状态

- [x] 已完成实现
- [x] 已完成定向测试
- [x] 已完成 Workflow Run/Preflight 前置回归
- [x] 已记录实现变更
- [x] 已完成最终静态/格式/路径闭集验证
- [x] 已满足全部验收条件并可进入 review / audit

最终 Paperclip disposition：`SUO-312 = done`。实现、验证、工作产品登记和完成评论均已提交，无本 Issue 内剩余工作。

## 10. 回滚建议

- 回滚文件: 删除三个 task_008 新实现文件与定向测试/报告；从 `backend/database.py` 移除独立 `create_runtime_plugin_tables()` 增量区段。
- 数据回滚: 若环境已调用 task_008 schema 初始化，应先确认没有 Workflow Run 引用 Receipt，再按 `runtime_load_receipt_entries` → `runtime_load_receipts` → `runtime_plugin_reconcile_attempts` → `runtime_plugin_materializations` 顺序执行受控迁移；不得删除或重建既有 Workflow Run/Preflight 表。
- 注意事项: Receipt 和 entry 设计为 append-only；不要以普通 update/delete 作为业务回滚。保留历史证据或在专用迁移窗口处理。

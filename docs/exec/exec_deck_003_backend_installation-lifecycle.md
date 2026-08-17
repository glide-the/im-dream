# Exec Report: SUO-271 / DECK-003 - Deck Plugin Installation 生命周期管理

## 1. 执行上下文

- Task ID: `task_deck_003_backend_installation-lifecycle`
- Paperclip Issue: [SUO-271](/SUO/issues/SUO-271)
- 控制父项: [SUO-217](/SUO/issues/SUO-217)
- 上游执行: [SUO-263](/SUO/issues/SUO-263)（Manifest）、[SUO-268](/SUO/issues/SUO-268)（Runtime Lock），均已完成
- 来源条目: `docs/issue/ISSUES_deck-plugin-voice-ink-dream-integration.md` §3 `DECK-003`
- 关联设计稿: `docs/design/deck-plugin-voice-ink-dream-integration.md` §6.1、§6.2、§14.1
- 关联 Task: `docs/task/task_deck_003_backend_installation-lifecycle.md`
- 关联 Stage: `docs/stage/stage_deck-plugin-voice-ink-dream-integration.md`，Stage 1 / Wave 3
- 执行 Agent: `ExecTaskAgent`
- 执行时间: `2026-08-01 17:07:30 CST`
- Execution lock: Paperclip harness 在本 heartbeat 启动前已成功 checkout；未重复 checkout
- 最终定位: 非生产基础能力；未宣称 `production_ready`

## 2. TASK-REQUIREMENT-FORMAT.md 填充摘要

- 模板路径: `docs/task/TASK-REQUIREMENT-FORMAT.md`
- 执行目标: 实现单一 DECK-003 Installation 数据模型、状态机、升级双版本切换、显式回滚、卸载和并发冲突语义
- 交付类型: backend model/service/schema/tests + 单一 exec 报告
- Domain / Priority: `backend` / `P0`（Paperclip priority `high`）
- 状态 / Work mode: `in_progress` / `standard`
- Assignee: `ExecTaskAgent`
- Blockers: 无；上游 Manifest 与 Runtime Lock 已完成并在当前工作树可读
- Stage 准入: Stage 1 / Wave 3 的 task_001、task_002 已完成；本 task 串行执行
- 回滚顺序: Stage 级为 `task_004 → task_003 → task_002 → task_001`；本 task 仅回滚下述五个授权路径中的自身增量
- 禁止范围: 除五个精确授权路径外全部禁止，尤其是设计、Issue、Task、Stage、其他 exec 报告、前端、API、Workflow Run、Paperclip Plugin/ClaudeAgent runtime、依赖锁及部署配置
- 验收条件: Issue 中 7 项验收与 Task §9 全量带入；未删除或放宽任何项目
- 测试要求: task 专属单测、Manifest/Runtime Lock/Database 回归、`py_compile`、差异与 whitespace 检查

### 工作树基线与冲突处理

开始执行时工作树已有多项未提交改动。授权共享路径中：

- `backend/models/deck_plugin.py` 已含上游 Manifest 与 Runtime Lock 模型且为未跟踪文件；本 task 只在文件末尾追加 Installation 枚举/模型。
- `backend/database.py` 已含上游 Deck Plugin release/lock 表以及其他既有改动；本 task 只紧随 runtime lock 表追加 Installation 表与索引。
- 其他既有修改和未跟踪文件均未触碰、未清理、未重置。

以上重叠可以按独立连续区段安全合并，因此未进入 blocked。

## 3. 模型生成的执行任务

- 任务目标: 在既有 Manifest/Runtime Lock 基线上实现 Installation 控制面生命周期，不提前实现下游能力。
- 实现范围: Installation 模型与独立状态枚举、SQLite 生命周期服务、安装表、单元/集成式生命周期测试。
- 文件范围: 严格限制为 Issue 授权的五个精确路径。
- 实现步骤:
  1. 追加严格 Pydantic Installation 模型和 Deck 域状态枚举。
  2. 新增异步生命周期服务、结构化结果/错误、状态转换约束。
  3. 以 pending target + 物化/load-smoke gate 实现双版本原子切换。
  4. 实现显式回滚、digest gate、软卸载和受留存证明保护的 purge。
  5. 追加 SQLite 约束、索引、revision 乐观并发字段和幂等初始化。
  6. 覆盖安装、升级、回滚、卸载、错误恢复及并发冲突测试。
- 范围校验结论: 生成任务未涉及 API/UI、兼容性算法、Workflow Run、生产供应链或 runtime 实现，可进入实施。

## 4. 实现变更记录

| 文件 | 操作 | 最小变更说明 |
|---|---|---|
| `backend/models/deck_plugin.py` | update | 追加 `InstallationStatus` 和 `DeckPluginInstallation`；校验 id、scope、SemVer、能力唯一性及默认版本一致性 |
| `backend/services/deck_plugin/installation_service.py` | create | 新增异步 Installation 生命周期服务、结果合同、结构化错误、状态机、双版本切换、回滚、卸载及并发保护 |
| `backend/database.py` | update | 追加 `deck_plugin_installations` 表、scope/status CHECK、scope 唯一约束、pending/revision 协调字段及三个索引 |
| `backend/tests/test_deck_plugin_installation.py` | create | 新增 11 项生命周期、错误恢复、双版本、回滚、卸载、并发与数据库测试 |
| `docs/exec/exec_deck_003_backend_installation-lifecycle.md` | create | 本 Issue 唯一正式执行报告 |

### 关键实现语义

- `uninstalled` 无出边，是终态；非法转换统一返回 `DECK_PLUGIN_INVALID_TRANSITION`。
- 安装先落为 `installing`，只有 runtime adapter 同时证明 lock 已物化且 load smoke 通过才进入 `ready` 并设置 `default_version`。
- 默认 runtime adapter 为 fail-closed 的 `runtime_adapter_required`，不会仅凭 runtime lock 猜测 runtime 已就绪。
- 能力扩张升级先进入 `upgrade_pending`；管理员显式批准后才准备目标 runtime 并切换默认版本。
- 目标版本失败时恢复/保持旧默认版本的 `ready`，不把失败目标加入 `installed_versions`。
- 回滚要求显式目标版本、已安装事实、兼容 gate、完整 digest 与 runtime readiness；缺失时返回 `DECK_PLUGIN_ROLLBACK_BLOCKED`，不猜测“最近可用”。
- 服务未读写 Workflow Run 表；默认版本变化只影响后续选择，历史/进行中 run 不被改写。
- 默认卸载为软删除并保留版本历史；force purge 必须由注入的 retention checker 明确证明可删除。
- 同 scope + plugin 安装由数据库唯一约束确定一个 winner；重叠升级由 in-flight guard 返回可重试的 `DECK_PLUGIN_CONCURRENT_MODIFICATION`；数据库更新另带 revision compare-and-swap。
- 成功结果包含 `operation_id`、`capability_diff`、`runtime_readiness`；失败通过 `InstallationServiceError.to_dict()` 返回结构化 error code、summary、retryable、installation/operation id 和 details。

## 5. 测试与验证

### 已执行测试

1. Task 专属测试：

   `PYTHONDONTWRITEBYTECODE=1 backend/.venv/bin/python -m unittest backend.tests.test_deck_plugin_installation -v`

   结果：`Ran 11 tests ... OK`。

2. 上游与数据库回归：

   `PYTHONDONTWRITEBYTECODE=1 backend/.venv/bin/python -m unittest backend.tests.test_deck_plugin_lock backend.tests.test_deck_plugin_manifest backend.tests.test_database -v`

   结果：`Ran 31 tests ... OK`。

3. 静态编译：

   `PYTHONDONTWRITEBYTECODE=1 backend/.venv/bin/python -m py_compile backend/models/deck_plugin.py backend/services/deck_plugin/installation_service.py backend/tests/test_deck_plugin_installation.py`

   结果：exit code `0`，无输出。

4. 差异/whitespace：

   `git diff --check -- backend/models/deck_plugin.py backend/database.py backend/services/deck_plugin/installation_service.py backend/tests/test_deck_plugin_installation.py`

   结果：exit code `0`，无 whitespace error。对三个未跟踪实现/测试文件执行 `git diff --no-index --check /dev/null <file>` 亦无 whitespace 诊断；其 exit code `1` 仅表示文件存在内容差异。

### 验收条件映射

| 验收 | 结果 | 证据 |
|---|---|---|
| Installation 字段完整 | PASS | `test_install_model_response_and_persisted_fields` + Pydantic validators |
| 合法/非法流转、错误恢复、终态 | PASS | `test_legal_transitions_invalid_transition_and_terminal_state`、`test_install_error_and_retry_recovery` |
| 双版本、审批后切换、失败保旧 | PASS | `test_capability_expansion_requires_approval_before_switch`、`test_failed_upgrade_preserves_old_ready_version` |
| 显式回滚、不改历史、无版本猜测 | PASS | `test_rollback_is_explicit_and_does_not_rewrite_historical_runs`、`test_rollback_requires_verified_digest` |
| 软删除与受控 purge | PASS | `test_soft_uninstall_retains_history_and_force_purge_requires_proof` |
| operation/diff/readiness/错误码 | PASS | 安装结果断言、错误恢复与并发错误结构断言 |
| 并发安装/升级 | PASS | `test_concurrent_install_has_one_winner_and_structured_conflict`、`test_overlapping_upgrades_return_deterministic_conflict` |
| 数据库约束/索引/幂等初始化 | PASS | `test_database_constraints_indexes_and_idempotent_initialization` |

### 未执行测试及原因

- 未运行全仓测试：Issue 明确只要求 task 专属与三个关联回归模块。
- 未运行真实 ClaudeAgent runtime materialization/load smoke：下游 runtime 实现不在授权范围；本服务通过注入 adapter 建立 gate，默认 fail closed。
- 未运行 API/E2E：API/UI 明确不属于本 task。

## 6. 风险与阻塞

- 阻塞: 无。
- 风险: 当前只提供 runtime/compatibility/retention 注入边界，真实 adapter 与审计持久化由后续授权 task 负责。
- 风险: [SUO-255](/SUO/issues/SUO-255) 的供应链裁决仍为 request changes，[SUO-258](/SUO/issues/SUO-258) 尚无生产证据；本实现和测试只报告 `ready_non_production`，不得作为生产就绪证据。
- 风险: 安装 attempt 尚未拆成独立审计表；当前失败证据保存在 Installation `last_error_*`，未越权新增事件/审计域实现。
- 上游澄清: 无需阻塞本 task；DECK-016/017/019 的未决项继续由其既有 owner 处理。

## 7. 完成状态

- [x] 已完成实现
- [x] 已完成要求的测试与回归
- [x] 已记录全部本 task 变更
- [x] 已逐项满足本 task 验收条件
- [x] 已确认未修改禁止范围
- [x] 可进入后续 review / audit；本执行 Issue 自身无剩余动作，可标记 `done`

## 8. 回滚建议

- `backend/models/deck_plugin.py`: 仅移除末尾 `InstallationStatus` 与 `DeckPluginInstallation` 追加区段，保留上游 Manifest/Runtime Lock 模型。
- `backend/services/deck_plugin/installation_service.py`: 删除本 task 新文件。
- `backend/database.py`: 仅移除 `deck_plugin_installations` 建表与三个索引区段，保留上游 release/lock 和其他既有数据库改动。
- `backend/tests/test_deck_plugin_installation.py`: 删除本 task 新文件。
- `docs/exec/exec_deck_003_backend_installation-lifecycle.md`: 归档或删除本报告时先保留 Issue 线程中的完成证据。
- 已初始化的本地数据库如需数据层回滚，应先确认没有历史引用/留存义务，再显式 `DROP TABLE deck_plugin_installations`；不得用强制 purge 绕过审计证明。
- 禁止通过 `git reset --hard`、整文件 checkout 或清理整个未跟踪目录回滚，因为共享工作树包含其他任务的未提交成果。

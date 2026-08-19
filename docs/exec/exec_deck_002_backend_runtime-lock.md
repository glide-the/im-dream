# Exec Report: deck_002 - Deck Runtime Plugin Lock 生成与不可变合同

## 1. 执行上下文

- Task ID：`deck_002`
- 执行 Issue：[SUO-268](/SUO/issues/SUO-268)
- 控制父项：[SUO-217](/SUO/issues/SUO-217)
- 关联业务 Issue：`DECK-002`，来源为 `docs/issue/ISSUES_deck-plugin-voice-ink-dream-integration.md` §3
- 关联设计稿：`docs/design/deck-plugin-voice-ink-dream-integration.md` §3.3、§5.3
- 关联 Task：`docs/task/task_deck_002_backend_runtime-lock.md`
- 关联 Stage：`docs/stage/stage_deck-plugin-voice-ink-dream-integration.md`，Stage 1 / Wave 2
- 前序执行：[SUO-263](/SUO/issues/SUO-263)，报告为 `docs/exec/exec_deck_001_backend_manifest-model.md`
- 生产供应链 Gate：[SUO-255](/SUO/issues/SUO-255) 为 `request_changes`；[SUO-258](/SUO/issues/SUO-258) 负责补齐生产证据
- 执行 Agent：`ExecTaskAgent`
- 执行时间：2026-08-01 16:36–16:44 CST
- Checkout：当前 Issue 已处于本 Agent 名下的 `in_progress`，无 blocker

工作树基线含 `deck_001` 的未提交实现及其他用户/前序任务改动。本任务仅在授权闭集中做最小增量，未清理、重置或覆盖闭集外文件。

## 2. `TASK-REQUIREMENT-FORMAT.md` 填充摘要

### 2.1 填充 Gate

- 模板路径：`docs/task/TASK-REQUIREMENT-FORMAT.md`
- 单一映射：`SUO-268` → `deck_002` / `DECK-002` → Stage 1 / Wave 2
- 执行目标：发布时把 manifest 的 Claude Code Plugin 版本约束解析为精确版本和制品摘要，冻结并持久化不可变 runtime lock
- 交付类型：backend model/service/database/test + 本正式执行报告
- 前置条件：`deck_001` 已完成并验收，定向测试 14/14、共享数据库回归 6/6
- Blockers：无；生产供应链 Gate 不阻塞本 task 的非生产基础实现，但禁止宣称 `production_ready`
- 明确不负责：marketplace/制品存储具体实现、Installation 生命周期、runtime 加载、API/UI、ClaudeAgent runtime、Paperclip Plugin worker

### 2.2 Issue / Task / Stage 合同填充值

| 模板字段 | 填充值 |
|---|---|
| 执行 Issue | `SUO-268` — `[execute][deck-plugin][task_002] 实现 Runtime Plugin Lock` |
| 来源业务 Issue | `DECK-002` |
| Parent / Ancestor | `SUO-217` → `SUO-216` |
| Domain / Priority | `backend` / `high`（Task 原始优先级 P0） |
| 状态 / Work mode | `in_progress` / `standard`（开始执行时） |
| 标签 | `deck-plugin`, `runtime-lock`, `release` |
| Assignee | `ExecTaskAgent` |
| Task 输入 | `DeckPluginManifestV1`、抽象 `MarketplaceResolver`、来源解析结果与供应链证据 |
| Task 输出 | `DeckRuntimePluginLock`、SQLite lock 记录、结构化解析错误与显式非生产结论 |
| 直接依赖 | `deck_001` / `DECK-001`，已完成；下游为 `deck_003`、`deck_006`、`deck_008` |
| Stage Gate | 冻结 `DeckRuntimePluginLock` 不可变合同；不提前实施 Wave 3 |
| 回滚要求 | 仅删除本 task 新文件/追加区段；先备份并 drop runtime lock 表；保留 `deck_001` 与用户工作树改动 |

### 2.3 写入边界

| 路径 | 动作 | 最小变更 |
|---|---|---|
| `backend/models/deck_plugin.py` | 修改 | 仅追加 `RuntimePluginLockEntry`、`DeckRuntimePluginLock` |
| `backend/services/deck_plugin/lock_generator.py` | 新建 | SemVer 范围解析、抽象 resolver、lock 生成、结构化错误与不可变性比较 |
| `backend/services/deck_plugin/release_service.py` | 修改 | 仅追加 lock 发布/读取、原子事务与不可变性守卫 |
| `backend/database.py` | 修改 | 仅追加 `deck_runtime_plugin_locks` 表、唯一约束、组合外键和幂等索引 |
| `backend/tests/test_deck_plugin_lock.py` | 新建 | 本 task 单元与 SQLite 集成测试 |
| `docs/exec/exec_deck_002_backend_runtime-lock.md` | 新建 | 本次唯一正式执行报告 |

禁止范围包括 `docs/design/`、`docs/issue/`、`docs/task/`、`docs/stage/`、其他 `docs/exec/`、`frontend/`、marketplace 具体实现、ClaudeAgent runtime、Paperclip Plugin worker、依赖锁和部署配置。本任务未修改这些范围。

### 2.4 验收与验证填充值

| 验收 ID | 验收条件 | 预期证据 |
|---|---|---|
| AC-01 | SemVer 范围解析为精确版本与摘要 | wildcard/comparator 选最高匹配版本测试 |
| AC-02 | 生成唯一 lock id 并与相同 release 原子关联 | `draft → validating → published + lock` 集成测试 |
| AC-03 | manifest hash 或 lock 内容变化时拒绝 | 不可变性比较与既有 lock 冲突测试 |
| AC-04 | digest/供应链 Gate 缺失时不得 production-ready | 缺 digest 与当前 Gate 强制非生产测试 |
| AC-05 | deprecated/revoked 历史 lock 可读取 | 生命周期后读取同一 lock id 测试 |
| AC-06 | 表、唯一约束、外键、索引、幂等初始化可验证 | SQLite PRAGMA 与重复 `create_tables()` 测试 |
| AC-07 | 区分版本不可解析与 marketplace 不可用 | `RUNTIME_PLUGIN_UNRESOLVED` / `RUNTIME_MARKETPLACE_UNAVAILABLE` 测试 |

精确验证命令：

```bash
PYTHONDONTWRITEBYTECODE=1 backend/.venv/bin/python -m unittest backend.tests.test_deck_plugin_lock -v
PYTHONDONTWRITEBYTECODE=1 backend/.venv/bin/python -m unittest backend.tests.test_deck_plugin_manifest -v
PYTHONDONTWRITEBYTECODE=1 backend/.venv/bin/python -m unittest backend.tests.test_database -v
PYTHONDONTWRITEBYTECODE=1 backend/.venv/bin/python -m py_compile backend/models/deck_plugin.py backend/services/deck_plugin/lock_generator.py backend/services/deck_plugin/release_service.py backend/tests/test_deck_plugin_lock.py
git diff --check
git diff --no-index --check /dev/null <untracked-allowed-file>
git status --short -- <allowed-closed-set>
```

## 3. 模型生成的执行任务

- 定义严格的 Runtime Lock 模型，并显式保存 `production_ready=false` 及原因；当前供应链 Gate 未通过时不允许产生生产就绪结论。
- 以标准库实现本 task 需要的精确 SemVer、`1.4.x` 和 comparator range 解析，不新增依赖。
- 定义 `MarketplaceResolver` Protocol 与解析结果 DTO；具体 marketplace/制品存储实现保持在任务范围外。
- 在新发布入口中先校验 manifest，再解析 lock；在同一 SQLite 事务内插入 lock 并发布 release，失败时回滚到 draft。
- 对同一 `deck_plugin_id + deck_plugin_version` 的既有 lock 做 manifest hash 与解析内容比较，任何重复或差异都拒绝。
- 保留 deprecated/revoked release 及其 lock 行，不以生命周期变更删除历史来源。
- 以新测试覆盖结构化错误、不可变性、原子性、历史读取与数据库合同；回归 `deck_001` 和共享数据库测试。

范围校验：生成任务仅涉及 §2.3 六个允许路径，通过。

## 4. 实现变更记录

| 文件 | 操作 | 说明 |
|---|---|---|
| `backend/models/deck_plugin.py` | update | 追加 lock/entry 严格模型、精确 SemVer、sha256/ID 校验与显式生产就绪字段 |
| `backend/services/deck_plugin/lock_generator.py` | create | 新增 SemVer 约束判断、最高匹配版本选择、resolver 合同、错误码、manifest hash、生产 Gate 和不可变性比较 |
| `backend/services/deck_plugin/release_service.py` | update | 新增 `publish_with_lock` 原子入口、既有 lock 拒绝、历史读取和模块级包装；保留 `deck_001` 的兼容入口 |
| `backend/database.py` | update | 新增 lock 表、release 组合外键 `ON DELETE RESTRICT`、组合唯一约束和命名索引 |
| `backend/tests/test_deck_plugin_lock.py` | create | 新增 11 个单元/集成测试 |
| `docs/exec/exec_deck_002_backend_runtime-lock.md` | create | 新增本执行报告 |

实现过程中在授权模型文件内观察到短暂的同名 Runtime Lock 追加冲突；执行立即暂停相关写入并核对差异。冲突最终收敛为唯一模型定义，随后通过 `py_compile` 和全部定向/回归测试确认无重复定义或残留语法问题。闭集外文件未参与冲突处理。

## 5. 测试与验证

### 5.1 最终结果

| 命令 | 结果 | 覆盖 |
|---|---|---|
| `PYTHONDONTWRITEBYTECODE=1 backend/.venv/bin/python -m unittest backend.tests.test_deck_plugin_lock -v` | PASS，11/11 | SemVer、resolver 错误、digest/Gate、不可变性、原子发布、失败回滚、历史读取、SQLite 合同 |
| `PYTHONDONTWRITEBYTECODE=1 backend/.venv/bin/python -m unittest backend.tests.test_deck_plugin_manifest -v` | PASS，14/14 | 前序 `deck_001` manifest/release 回归 |
| `PYTHONDONTWRITEBYTECODE=1 backend/.venv/bin/python -m unittest backend.tests.test_database -v` | PASS，6/6 | 共享 Story Workspace 数据库回归 |
| `python -m py_compile ...` | PASS | 四个本 task Python 文件可编译 |
| `git diff --check` + untracked 文件逐项 `--no-index --check` | PASS | 无 whitespace/error marker；untracked 文件命令 exit 1 仅表示存在新增差异，且无错误输出 |
| 允许闭集 `git status` | PASS | 本 task 实际变更仅落在六个授权路径；共享文件保留 `deck_001` 基线 |

首次 lock 定向测试为 10/11：不可变性场景仅修改 `deck_plugin_version`，但未同步版本化 `workflow_definition_ref`，先被既有 manifest validator 正确拒绝。测试夹具同步为 `3.2.0` 的精确 workflow 引用后，最终 11/11 通过；该失败未被静默跳过。

### 5.2 验证证据映射

- AC-01：`1.4.x` 选择 `1.4.2`，`>=1.0.0 <2.0.0` 边界测试通过。
- AC-02：发布事务生成 `rpl_<uuid>`，lock 的 manifest hash 与最终 published release 一致；resolver 失败时 release 回滚为 draft 且无 lock。
- AC-03：等价 lock 比较通过，digest 改变比较失败；已有 lock 会触发 `DeckRuntimePluginLockImmutabilityError`，重复发布会被状态机拒绝。
- AC-04：缺 digest 会保留明确非生产原因；即使 resolver 声称已验证，当前供应链 Gate 未通过仍强制 `production_ready=false`。
- AC-05：release 依次 deprecated、revoked 后仍能读取同一 `runtime_plugin_lock_id`。
- AC-06：重复建表通过；唯一约束、组合外键、`ON DELETE RESTRICT` 和 `idx_runtime_locks_deck_plugin` 均经 PRAGMA 验证。
- AC-07：版本约束无效/无匹配返回 `RUNTIME_PLUGIN_UNRESOLVED`；resolver 不可用返回 `RUNTIME_MARKETPLACE_UNAVAILABLE`。

测试期间出现仓库既有 `memory_workspace_defaults` backfill warning；既有容错逻辑捕获 warning，所有断言通过，且共享数据库测试 6/6 独立通过。本 task 未修改该导入路径。

## 6. 风险与阻塞

- 阻塞：无。
- 生产限制：本实现是非生产基础能力。由于 [SUO-255](/SUO/issues/SUO-255) 和 [SUO-258](/SUO/issues/SUO-258) 尚未闭环，默认 LockGenerator 始终附加供应链 Gate 原因，不能宣称生产就绪。
- 抽象边界：具体 marketplace/制品存储、签名验证、留存和恢复源实现不在本 task；由后续生产供应链工作注入 resolver 与真实证据。
- 兼容入口：`deck_001` 的 `validate_release` 为前序测试保留；需要 runtime lock 的新发布必须调用 `publish_with_lock`。API 路由迁移不在当前授权范围。
- 未运行项：无 API/UI E2E，因为本 task 未授权 API/UI 交付面；未运行全仓测试，遵循模板最小相关验证并已覆盖两组要求的回归。
- 工作树冲突：授权文件内的短暂同名追加已收敛并验证；闭集外既有用户改动全部保留。

## 7. 完成状态

- [x] 已完成实现
- [x] 已完成测试
- [x] 已记录变更
- [x] 已满足验收条件
- [x] 可进入 review / audit

建议最终 disposition：`done`。当前 Issue 的单一 task 已实现且验证完成；生产供应链 Gate 属于既有独立 Issue，不作为本 Issue 的待办或生产就绪声明。

## 8. 回滚建议

1. 若数据库已有 lock 数据，先备份 `deck_runtime_plugin_locks.lock_json` 及组合键，再执行：

   ```sql
   DROP TABLE IF EXISTS deck_runtime_plugin_locks;
   ```

2. 删除本 task 新增的 `backend/services/deck_plugin/lock_generator.py`、`backend/tests/test_deck_plugin_lock.py` 和本报告。
3. 仅从共享文件移除本 task 的追加区段：模型文件中的两个 Runtime Lock 模型、release service 的 lock import/错误类/发布与读取入口、database 的 lock 表与索引。不得删除或回退 `deck_001` 的 manifest、release 表、validator、发布状态机与测试。
4. 恢复时重新运行 `create_tables()`；表/索引幂等初始化已验证。
5. 禁止使用 `git reset --hard`、工作树清理或整文件覆盖；必须保留前序和用户未提交改动。

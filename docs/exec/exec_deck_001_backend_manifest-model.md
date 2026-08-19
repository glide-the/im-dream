# Exec Report: deck_001 - Deck Plugin Manifest 与发布版本模型

## 1. 执行上下文

- Task ID：`deck_001`
- 执行 Issue：[SUO-263](/SUO/issues/SUO-263)
- 关联业务 Issue：`DECK-001`，来源为 `docs/issue/ISSUES_deck-plugin-voice-ink-dream-integration.md` §3
- 关联设计稿：`docs/design/deck-plugin-voice-ink-dream-integration.md` §5.1、§5.2、§5.4
- 关联 Task：`docs/task/task_deck_001_backend_manifest-model.md`
- 关联 Stage：`docs/stage/stage_deck-plugin-voice-ink-dream-integration.md`，Stage 1 / Wave 1
- 控制面准入：[SUO-262](/SUO/issues/SUO-262)、[SUO-247](/SUO/issues/SUO-247)、[SUO-248](/SUO/issues/SUO-248)、[SUO-249](/SUO/issues/SUO-249)
- 执行 Agent：`ExecTaskAgent`
- 执行时间：2026-08-01 16:15–16:24 CST
- Checkout：由本次 Paperclip harness 在启动前完成；未重复 checkout

工作树基线包含以下既有、非本任务改动，执行过程中均未覆盖或清理：

- `docs/design/deck/design_002_deck-plugin-decision-gates.md`
- `docs/stage/stage_deck-plugin-voice-ink-dream-integration.md`
- `docs/stage/stage_story-workspace.md`
- `docs/task/SUO-238-completion-report.md`

## 2. `TASK-REQUIREMENT-FORMAT.md` 执行副本

### 2.1 填充 Gate

- 模板路径：`docs/task/TASK-REQUIREMENT-FORMAT.md`
- 单一映射：`SUO-263` → `deck_001` / `DECK-001` → Stage 1 / Wave 1
- Stage 准入：满足；Stage 文档将 task_001 标记为无依赖、唯一可立即执行项
- Blockers：无
- 工作树冲突：无；允许闭集内文件在执行前均无既有改动
- 执行目标：实现 Manifest v1 schema、校验器、发布状态机、SQLite 发布表及验证
- 交付类型：backend model/service/database/test + 本正式执行报告
- 明确不负责：安装生命周期、runtime lock、API/UI、ClaudeAgent runtime、Paperclip Plugin worker、后续 Wave

### 2.2 Issue / Task / Stage 合同填充值

| 模板字段 | 填充值 |
|---|---|
| 执行 Issue | `SUO-263` — `[execute][deck-plugin][task_001] 实现 Manifest 与发布版本模型` |
| 来源业务 Issue | `DECK-001` |
| Parent / Ancestor | `SUO-262` → `SUO-217` → `SUO-216` |
| Domain / Priority | `backend` / `high`（Task 原始优先级 P0） |
| 状态 / Work mode | `in_progress` / `standard`（开始执行时） |
| 标签 | `deck-plugin`, `manifest`, `schema` |
| Assignee | `ExecTaskAgent` |
| Task 输入 | `DeckPluginManifestV1` JSON、管理员 `source_allowlist` |
| Task 输出 | `DeckPluginRelease`、结构化校验错误、SQLite 持久化记录 |
| 直接依赖 | 无；下游为 task_002、task_003、task_004 |
| Stage Gate | 本 task 冻结 `DeckPluginManifestV1`；后续 Wave 不在本次执行范围 |
| 回滚要求 | 可删除本 task 新文件；数据库先备份，再 `DROP TABLE deck_plugin_releases`；重新运行 `create_tables()` 可恢复空表与索引 |

### 2.3 必须执行的实现步骤

1. 定义 `DeckPluginManifestV1`、所有 Task §3 子模型、`DeckPluginReleaseStatus` 与 `DeckPluginRelease`。
2. 实现稳定标识、SemVer 2.0、版本化引用、能力子集、来源 allowlist、敏感内容和降级声明校验。
3. 在 `create_tables()` 中以最小增量创建 `deck_plugin_releases`、唯一约束及两个索引。
4. 实现 draft 创建、校验发布、弃用、撤销、按 id+version 查询以及显式状态迁移守卫。
5. 增加单元/内存 SQLite 集成测试，执行定向回归和闭集差异检查。

### 2.4 写入边界

| 路径 | 动作 | 最小变更 |
|---|---|---|
| `backend/models/deck_plugin.py` | 新建 | manifest/release 模型与枚举 |
| `backend/services/deck_plugin/manifest_validator.py` | 新建 | manifest 校验器与结构化错误码 |
| `backend/services/deck_plugin/release_service.py` | 新建 | 发布版本 CRUD/状态机逻辑 |
| `backend/database.py` | 修改 | 仅追加 `deck_plugin_releases` 表和索引 |
| `backend/tests/test_deck_plugin_manifest.py` | 新建 | 本 task 单元与 SQLite 集成测试 |
| `docs/exec/exec_deck_001_backend_manifest-model.md` | 新建 | 本次唯一正式执行报告 |

禁止修改：`docs/design/`、`docs/issue/`、`docs/task/`、`docs/stage/`、其他 `docs/exec/` 文件、`frontend/`、ClaudeAgent runtime、Paperclip Plugin worker、依赖锁、部署配置及任何未列出路径。执行结果未触碰这些禁止范围。

### 2.5 验收与验证填充值

| 验收 ID | 验收条件 | 预期证据 |
|---|---|---|
| AC-01 | Manifest schema 覆盖 Task §3/§9 字段 | schema 构造及合法 manifest 测试 |
| AC-02 | 稳定标识和 SemVer 校验 | 合法/非法参数化测试 |
| AC-03 | 发布状态机完整，published 不回 draft | 状态迁移和非法迁移测试 |
| AC-04 | 唯一性/schema/能力子集/allowlist/完整性校验 | validator 与 SQLite 唯一约束测试 |
| AC-05 | 禁止密钥明文和完整 runtime prompt | 敏感键与密钥特征拒绝测试 |
| AC-06 | 合法/非法 manifest、SemVer、重复标识通过 | 14 项定向测试 |
| AC-07 | DB CRUD、唯一约束、索引和幂等初始化 | 内存 SQLite 集成测试 |
| AC-08 | 回滚/恢复说明完整 | 本报告 §8 |

精确验证命令：

```bash
PYTHONDONTWRITEBYTECODE=1 backend/.venv/bin/python -m unittest backend.tests.test_deck_plugin_manifest -v
PYTHONDONTWRITEBYTECODE=1 backend/.venv/bin/python -m unittest backend.tests.test_database -v
git diff --check
git status --short -- backend/models/deck_plugin.py backend/services/deck_plugin/manifest_validator.py backend/services/deck_plugin/release_service.py backend/database.py backend/tests/test_deck_plugin_manifest.py docs/exec/exec_deck_001_backend_manifest-model.md
```

- 静态检查：仓库未配置 task 可用的 ruff/mypy 命令，采用 import 执行覆盖语法/类型构造并运行 `git diff --check`。
- E2E：N/A；本 task 不新增 API/UI 或运行入口。
- 差异通过标准：仅出现上述六个允许路径，且共享 `backend/database.py` 只有表/索引增量。

## 3. 模型生成的执行任务

- 任务目标：提供后续 Deck Plugin Wave 可依赖的不可变发布基础。
- 模型策略：Pydantic v2 严格 schema（`extra="forbid"`）；标准库正则实现 SemVer 2.0，避免越权修改依赖；SQLite connection 注入支持隔离集成测试。
- 完整性策略：递归拒绝敏感键和常见明文密钥特征；仅允许声明 config key 与 secret-ref 类型，不接收完整 prompt 字段。
- 发布策略：draft 经事务内 validating 后发布；发布时生成规范 JSON 与 `sha256:` hash；deprecated/revoked 仅改生命周期列，发布后的 manifest/hash 保持不变。
- 来源策略：production 模式拒绝本地来源，并要求 Claude Code Plugin `source_ref` 命中管理员 allowlist；允许 allowlist 来源的显式版本 pin。
- 范围校验：生成任务只涉及第 2.4 节六个允许路径，通过。

## 4. 实现变更记录

| 文件 | 操作 | 说明 |
|---|---|---|
| `backend/models/deck_plugin.py` | create | 新增 Manifest v1 全量模型、子模型、发布枚举、稳定标识/SemVer schema 校验和 release 输出模型 |
| `backend/services/deck_plugin/manifest_validator.py` | create | 新增引用、schema 版本、能力子集、allowlist、唯一性、敏感内容和降级声明校验 |
| `backend/services/deck_plugin/release_service.py` | create | 新增注入式 SQLite 发布服务、模块级入口、规范 hash 与发布不可变状态机 |
| `backend/database.py` | update | 在 `create_tables()` 中仅追加发布表、状态 CHECK、组合唯一约束和两个幂等索引 |
| `backend/tests/test_deck_plugin_manifest.py` | create | 新增 14 个单元/集成测试 |
| `docs/exec/exec_deck_001_backend_manifest-model.md` | create | 新增本执行报告 |

## 5. 测试与验证

### 5.1 最终结果

| 命令 | 结果 | 覆盖 |
|---|---|---|
| `PYTHONDONTWRITEBYTECODE=1 backend/.venv/bin/python -m unittest backend.tests.test_deck_plugin_manifest -v` | PASS，14/14 | 合法/非法 manifest、SemVer、稳定标识、版本化引用、能力子集、allowlist、本地来源、敏感键、降级、CRUD、唯一性、状态机、索引、幂等与恢复 |
| `PYTHONDONTWRITEBYTECODE=1 backend/.venv/bin/python -m unittest backend.tests.test_database -v` | PASS，6/6 | 共享 `create_tables()` 既有 Story Workspace 数据库回归 |
| `git diff --check` | PASS | 无 whitespace/error marker |
| 允许闭集 `git status` | PASS | 仅六个授权路径发生本任务变更 |

首轮 task 专属测试为 13/14：测试使用 `1.0` 时先触发 Pydantic 长度约束，导致测试期待的 SemVer 文案未命中；实现始终正确拒绝该值。测试输入修正为长度合法但违反 SemVer 的 `1.0.00` 后，最终 14/14 通过。该失败未被静默跳过。

### 5.2 验证证据映射

- AC-01：`test_valid_manifest_covers_v1_contract` 通过。
- AC-02：`test_semver_2_syntax`、`test_stable_identifier_is_required` 通过。
- AC-03：完整链路 `draft → validating → published → deprecated → revoked` 通过；`published → draft` 显式拒绝。
- AC-04：能力、来源、版本化引用、服务层重复检查和 SQLite 组合唯一约束均通过。
- AC-05：`api_key`、`password`、`system_prompt` 以及常见明文密钥特征会被拒绝；schema 额外字段也被禁止。
- AC-06：task 专属测试 14/14 通过。
- AC-07：表创建重复执行、CRUD、唯一约束、两个命名索引、drop/recreate 恢复均通过。
- AC-08：回滚与恢复步骤见 §8。

测试期间从仓库既有 `database.py` 的绝对导入路径产生 `memory_workspace_defaults` backfill warning；该 warning 被既有容错逻辑捕获，所有断言通过，且独立既有数据库测试 6/6 通过。本 task 未越权修改该既有导入逻辑。

## 6. 风险与阻塞

- 阻塞：无。
- 未运行项：无 E2E，原因是本 task 没有 API/UI 交付面；未运行全仓库测试，遵循模板“最小相关验证”要求，已额外执行共享数据库测试。
- 剩余风险：`revoke_release(reason)` 当前验证 reason 非空，但 Task 指定表没有撤销原因字段，因此本 Wave 不持久化 reason；后续审计 Wave 应按其独立合同落库，不能在本 task 擅自扩表。
- 未决设计：DECK-016/DECK-017 继续按上游默认假设管理；本实现只使用已授权的 `sha256` manifest hash，不宣称 production artifact digest 决策已冻结。
- 工作树冲突：无；基线中的既有用户改动全部保留。

## 7. 完成状态

- [x] 已完成实现
- [x] 已完成测试
- [x] 已记录变更
- [x] 已满足验收条件
- [x] 可进入 review / audit

最终 disposition：`done`。本 Issue 的单一 task 已实现且验证完成，无需在本 Issue 留待后续动作。

## 8. 回滚建议

1. 在尚未产生发布数据时，删除本 task 新增的三个实现文件、测试文件和本报告，并仅回退 `backend/database.py` 中 `deck_plugin_releases` 表/索引区段。
2. 若数据库已有数据，先备份 `deck_plugin_releases`，确认不存在下游引用后再执行：

   ```sql
   DROP TABLE IF EXISTS deck_plugin_releases;
   ```

3. 恢复空表时重新运行应用既有的 `create_tables()`；`CREATE TABLE/INDEX IF NOT EXISTS` 已由重复初始化与 drop/recreate 测试证明幂等。
4. 回滚时不得使用 `git reset --hard` 或清理工作树；必须保留 §1 所列既有用户改动。

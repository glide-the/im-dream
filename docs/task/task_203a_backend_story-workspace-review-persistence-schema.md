# task_203a_backend_story-workspace-review-persistence-schema

## 1. 任务标题

Character / Scene 审阅持久化 Schema 与 Canonical Contract

## 2. 关联 Issue

- **Task ID**：`task_203a`
- **Task domain**：`backend`
- **Task 定义 Issue**：[SUO-317](/SUO/issues/SUO-317)
- **裁决 Issue**：[SUO-316](/SUO/issues/SUO-316)
- **被解除阻塞的 execute Issue**：[SUO-309](/SUO/issues/SUO-309)
- **优先级**：P0 / high
- **权威输入**：
  - `docs/task/task_203_backend_story-workspace-review-workflow.md`
  - `backend/database.py`
  - `backend/tests/test_database.py`
  - `backend/story_workspace/contracts.py`
  - [SUO-316](/SUO/issues/SUO-316) 的方案 1 裁决与变更前 hash 证据

## 3. 任务目标与唯一裁决

在 `task_203` 路由实现之前，以独立 Schema / canonical-contract execute task 补齐 character / scene 的 confirm、reject、archive 持久化能力，使 `AC-203-01` 与 batch action-resource 矩阵在合法写入闭集内可实现。

本任务只采用 [SUO-316](/SUO/issues/SUO-316) 已裁决的**方案 1**。方案 2（收窄验收、删除 character / scene 动作或缩减 batch 矩阵）已排除，禁止作为兼容分支、feature flag、临时 fallback 或测试例外保留。

边界如下：

- 本任务只定义并实现持久化 Schema、幂等迁移、canonical contracts 与 focused contract tests。
- 本任务不实现 confirm / reject / archive HTTP 路由，不改状态流转矩阵，不释放 `backend/routers/story_workspace.py` 的 execute Gate。
- `task_203` execute 对本任务形成硬依赖：本任务实现完成、hash 重冻结并通过 Stage readiness 之前，不得恢复 [SUO-309](/SUO/issues/SUO-309)。

## 4. 冻结字段合同

### 4.1 最终字段矩阵

`story_workspace_characters` 与 `story_workspace_scenes` 必须以完全相同的定义新增下列四列：

| 字段 | SQLite 声明 | NOT NULL | SQL DEFAULT | 合法值 / 长度 | Canonical Python 类型 | 语义 |
|---|---|---:|---|---|---|---|
| `status` | `TEXT` | 是 | `'active'` | 仅 `active` / `archived` | `StoryWorkspaceAssetStatus` | character / scene 资产生命周期；不复用 story 的 publish 状态 |
| `review_notes` | `TEXT` | 否 | 无（逻辑默认 `NULL`） | `NULL` 或最多 2000 个 Unicode 字符 | `Optional[str]` | reject 的用户修改意见；不得挪用 character `notes` 或 scene `description` |
| `confirmed_at` | `DATETIME` | 否 | 无（逻辑默认 `NULL`） | `NULL` 或 SQLite datetime 值 | `Optional[datetime]` | 成功 confirm 时写入的确认时间 |
| `archived_at` | `DATETIME` | 否 | 无（逻辑默认 `NULL`） | `NULL` 或 SQLite datetime 值 | `Optional[datetime]` | 成功 archive 时写入的归档时间 |

必须在 fresh-create DDL 与 existing-database migration 中保持同一列名、affinity、default、nullability 和 `CHECK` 约束。最小列 DDL 为：

```sql
status TEXT NOT NULL DEFAULT 'active'
  CHECK(status IN ('active', 'archived')),
review_notes TEXT
  CHECK(review_notes IS NULL OR length(review_notes) <= 2000),
confirmed_at DATETIME,
archived_at DATETIME
```

SQLite 的 `length(TEXT)` 与 canonical validation 都按 Unicode 字符数量执行；2000 字符合法，2001 字符必须在写入前或数据库约束层被拒绝，且不得产生部分写入。

### 4.2 Canonical contract

`backend/story_workspace/contracts.py` 是唯一后端业务合同 owner，必须进行以下 additive 变更：

1. `STORY_WORKSPACE_CONTRACT_VERSION` 从 `1.0.0` 提升为 `1.1.0`。
2. 新增并导出：

   ```python
   class StoryWorkspaceAssetStatus(str, Enum):
       ACTIVE = "active"
       ARCHIVED = "archived"
   ```

3. `StoryWorkspaceCharacter` 与 `StoryWorkspaceScene` 均新增：
   - `status: StoryWorkspaceAssetStatus = StoryWorkspaceAssetStatus.ACTIVE`
   - `review_notes: Optional[str] = None`
   - `confirmed_at: Optional[datetime] = None`
   - `archived_at: Optional[datetime] = None`
4. 新增并导出 `STORY_WORKSPACE_REVIEW_NOTES_MAX_LENGTH = 2000`，审阅请求合同必须复用该常量进行 2000 字符上限校验；禁止 router 复制另一个数值形成双轨。
5. `StoryWorkspaceReviewActionRequest` 与 `StoryWorkspaceBatchReviewRequest` 的公开名称、既有字段和构造入口保持兼容，但其 `review_notes` 必须具备可测试的 `None | len <= 2000` 校验；2001 字符构造失败。
6. `StoryWorkspaceContentStatus` 继续只表达 story 的 `draft / published / archived`。character / scene 不允许 `published`，不得把两类 enum 合并后放宽数据库合法值。

`frontend/` 不属于本任务范围。新增响应字段属于 additive JSON 字段，旧客户端忽略未知字段即可；不得借本任务修改前端类型或页面。

### 4.3 状态与时间戳语义

下列语义供后续 `task_203` 直接消费，不得在 execute 时重新裁决：

| 前态 | 动作 | 后态 | 必须写入 | 必须保留 | 结果 |
|---|---|---|---|---|---|
| `status=active`, `review_status=pending` | confirm | `status=active`, `review_status=confirmed` | `confirmed_at=CURRENT_TIMESTAMP`, `updated_at=CURRENT_TIMESTAMP` | `archived_at`, `review_notes` | 成功 |
| `status=active`, `review_status=pending` | reject | `status=active`, `review_status=rejected` | 请求中的 `review_notes`（可为 `NULL`），`updated_at=CURRENT_TIMESTAMP` | `confirmed_at`, `archived_at` | 成功 |
| `status=active`, 任一合法 `review_status` | 单条 archive | `status=archived`，`review_status` 不变 | `archived_at=CURRENT_TIMESTAMP`, `updated_at=CURRENT_TIMESTAMP` | `review_status`, `confirmed_at`, `review_notes` | 成功 |
| `status=archived`, 任一合法 `review_status` | confirm / reject / archive | 不变 | 无 | 全部字段 | HTTP 400；数据库无写入 |

补充冻结规则：

- 无 unarchive / restore 动作；恢复语义不在本任务和 `task_203` 范围内。
- confirm 不写 `review_notes`；reject 不伪造或回填 `confirmed_at`；archive 不改变 `review_status`。
- batch 继续遵循 `task_203` 的 pending-only 合同：character / scene 的 batch archive 只更新 `status=active AND review_status=pending` 的 owned rows；其他状态进入 `skipped_ids`。
- `status=archived` 是唯一归档判定；`archived_at` 是归档发生时间。路由成功写入后必须满足 `status=archived => archived_at IS NOT NULL`；`status=active => archived_at IS NULL`。该跨列不变量由受控 action 与 focused tests 保证，不通过通用 PATCH 暴露。
- 既有 character / scene 列表行为不在本 Schema task 中隐式改变：不新增默认隐藏、status filter 或排序语义。archive 后的读取/筛选变化如需扩展，必须另有 task 合同。

## 5. 实现步骤

### Step 1：记录变更前冻结基线

执行前记录工作树中 `backend/database.py` 的 SHA-256。[SUO-317](/SUO/issues/SUO-317) / [SUO-319](/SUO/issues/SUO-319) 的旧记录、当前 `HEAD` 与本次增量重冻结候选值关系如下：

| 快照 | SHA-256 | 定位 |
|---|---|---|
| 旧 Task / Stage 记录 | `2fe178c215bfdb417c2c76186a4e3e09950a665da5e8a6874b953230f99efdce` | 已被后续共享工作树演进取代，只作漂移审计，不再是 execute 输入 |
| 当前 `HEAD:backend/database.py` | `f4ebabe03cf7935cdcfe80723c01fd421ae0b0f26534da84afeb592459218825` | 当前提交快照，不包含工作树中的未提交增量 |
| 当前工作树候选基线 | `47d6290c29b0297fed2d5256a9854c2224ca93575764e277951940f4f17e0810` | `task_203a` 变更前候选输入；相对 `HEAD` 为 `729` 行新增、`0` 行删除 |

这 `729` 行既有 diff 分为两段（`186 + 543` 行），来源为 Deck Plugin release / runtime lock / installation / binding / preflight 表，以及 Workflow Run、runtime-plugin materialization / reconcile / load receipt、agent session 的表、索引、触发器和初始化 helper。它们不属于 `task_203a`，不得清理、覆盖或静默吸收为本任务实现结果。本次重冻结窗口内连续复算保持 `47d629...e0810` 与 `729/0` 不变，因此只能将其认定为**候选变更前基线**；它不是 `HEAD` 基线，也不代表这些既有改动已完成提交或验收。

execute checkout 后、首次写入前必须同时复算 `shasum -a 256 backend/database.py` 与 `git diff --numstat HEAD -- backend/database.py`，并分别精确匹配 `47d6290c29b0297fed2d5256a9854c2224ca93575764e277951940f4f17e0810` 以及 `729` 行新增 / `0` 行删除 / `backend/database.py`。任一值变化即停止写入、将 execute 标记为 blocked，并在 Issue 评论中指明当前写入 owner 及解锁动作（由该 owner 完成或移交既有改动，随后 TaskDesignAgent 与 StagePlanner 依次重新冻结 Task / Stage）；在两层记录一致前不得进入 execute，也不得把不稳定工作树称为冻结基线。

### Step 2：更新 fresh-create DDL

在 `backend/database.py:create_tables()` 的 `story_workspace_characters` 与 `story_workspace_scenes` 定义中加入 §4.1 的四列和两个单列 `CHECK` 约束。

- 不修改 story 表字段、合法值或默认值。
- 不新增 audit 表、side table、trigger 或新的持久化资源类型。
- 不为本次四列新增索引；本任务没有 status filter 查询合同，避免预先扩展读路径。

### Step 3：实现幂等 existing-database migration

在两张表 fresh-create 之后执行受控 migration helper。每张表按 `status → review_notes → confirmed_at → archived_at` 的固定顺序：

1. 使用 `PRAGMA table_info(<table>)` 获取现有列集合。
2. 仅对缺失列执行对应的 `ALTER TABLE ... ADD COLUMN`：

   ```sql
   ALTER TABLE <table> ADD COLUMN status TEXT NOT NULL DEFAULT 'active'
     CHECK(status IN ('active', 'archived'));
   ALTER TABLE <table> ADD COLUMN review_notes TEXT
     CHECK(review_notes IS NULL OR length(review_notes) <= 2000);
   ALTER TABLE <table> ADD COLUMN confirmed_at DATETIME;
   ALTER TABLE <table> ADD COLUMN archived_at DATETIME;
   ```

3. 迁移在同一事务/受控 savepoint 中完成；已存在列通过 introspection 跳过，其他 SQL 错误必须抛出，不得用裸 `except Exception: pass` 吞掉真实失败。
4. 再次读取 `PRAGMA table_info`，确认两表字段完全符合 §4.1。
5. `create_tables()` 连续执行两次不得报错、重复列或改变已迁移数据。

### Step 4：冻结 backfill 与兼容语义

迁移后的既有行必须满足：

| 既有事实 | `status` | `review_notes` | `confirmed_at` | `archived_at` | 理由 |
|---|---|---|---|---|---|
| 任意 legacy character / scene | `active` | `NULL` | `NULL` | `NULL` | 旧 Schema 没有可证明的 archive、备注或动作时间事实 |
| legacy `review_status=confirmed` | `active` | `NULL` | `NULL` | `NULL` | 保留 confirmed 状态，但不以 `updated_at` 伪造确认时间 |
| legacy `review_status=rejected` | `active` | `NULL` | `NULL` | `NULL` | 不从 character `notes` 或 scene `description` 猜测驳回意见 |

`status` 的 `NOT NULL DEFAULT 'active'` 必须完成现有行 backfill；可追加 `WHERE status IS NULL` 的防御性更新，但不得改写非空合法状态。新增 nullable 列不执行推断式 backfill。

### Step 5：更新 canonical contracts 与 contract tests

按 §4.2 修改 canonical 文件，并在既有测试文件中验证：

- enum、版本、`__all__` 与 `StoryWorkspace*` / `STORY_WORKSPACE_*` 命名规则；
- character / scene 四字段的类型与默认值；
- review notes 2000/2001 边界；
- 旧字段与公开构造入口仍可用；
- 不创建 `backend/types/` 或其他第二 owner。

### Step 6：重冻结数据库 hash 并形成交付证据

实现、migration tests 与 contract tests 全部通过后：

1. 重新计算 `backend/database.py` SHA-256；新值必须与 §5 Step 1 的变更前基线不同。
2. 在 `docs/exec/exec_task_203a_story-workspace-review-persistence-schema.md` 和对应 execute Issue 评论中同时记录：旧 hash、新 hash、`backend/story_workspace/contracts.py` hash、测试命令与结果。
3. 后续 `task_203` 将该新数据库 hash 作为只读冻结基线；其执行前后必须相同。
4. 仅“代码已改”或仅“测试通过”均不能释放共享路由；必须同时满足 §10 的释放条件。

## 6. 涉及文件路径与输入 / 输出

### 6.1 允许修改路径

| 路径 | 操作 | 输出 |
|---|---|---|
| `backend/database.py` | 修改 | fresh DDL + 幂等四列迁移 |
| `backend/story_workspace/contracts.py` | 修改 | v1.1.0 canonical enum、字段、长度常量与请求校验 |
| `backend/tests/test_database.py` | 修改 | fresh/migration/backfill/constraint tests |
| `backend/tests/test_story_workspace_contracts.py` | 修改 | canonical contract 与 2000 字边界 tests |
| `docs/exec/exec_task_203a_story-workspace-review-persistence-schema.md` | 新建 | execute 报告、hash 与验收证据 |

### 6.2 禁止修改路径与行为

- 禁止修改 `backend/routers/story_workspace.py`、`backend/services/`、`backend/server.py` 与其他业务实现；路由归 `task_203`。
- 禁止修改 `frontend/`。
- 禁止修改 `docs/design/`、`docs/issue/`、`docs/task/`、`docs/stage/`；execute 只读本任务合同。
- 禁止提交或改写 `backend/data/ink-and-memory.db` 等运行时数据库文件。
- 禁止新增 audit table、side table、trigger、通用 JSON blob 或进程内缓存来替代冻结列。
- 禁止复用 character `notes`、scene `description` 或 story 字段承载 character / scene 的审阅事实。
- 禁止实现 route、缩减 action-resource 矩阵、加入 feature flag 双轨，或将方案 2 作为 fallback。

### 6.3 输入 / 输出

输入：当前 SQLite schema、既有 character / scene 数据、canonical contract v1.0.0、[SUO-316](/SUO/issues/SUO-316) 旧 hash 与方案 1 裁决。

输出：

- 可同时支持 fresh database 与 legacy database 的四列 Schema；
- v1.1.0 canonical contract；
- 可重放的 migration/backfill/constraint 证据；
- 新冻结数据库 hash；
- 供 `task_203` 使用的单一持久化语义，无 HTTP 路由实现。

## 7. 依赖项与执行顺序

| 依赖 / 下游 | 类型 | 冻结关系 |
|---|---|---|
| `task_201` Schema 基线 | 硬前置 | 本任务只做 additive migration，不重写六表基线 |
| `task_205b` canonical owner 迁移 | 硬前置 | `backend/story_workspace/contracts.py` 已成为唯一 owner，禁止回退到 `backend/types/` |
| `task_204` 共享路由基线 | 只读前置 | 本任务不写 router，但需保留其已交付 import / endpoint 基线 |
| `task_203a` → `task_203` | **硬依赖** | `task_203a` execute 完成、hash 重冻结、Stage readiness 通过后，`task_203` 才可 checkout |
| `task_203` → 后序 E2E / Gate | 既有下游 | 本任务不直接释放 `task_202c_verify`、`task_230` 或后续执行 |

严格顺序：

```text
task_205b / task_204 已冻结基线
  → task_203a（Schema + canonical contract）
  → StagePlanner 九项 readiness 复核
  → task_203（共享路由 review workflow）
  → 后序验证 / Gate
```

## 8. 测试策略与最小命令

### 8.1 必须新增/更新的测试

| 测试 ID | 测试目标 |
|---|---|
| `test_story_workspace_review_persistence_schema_contract` | 两表四列的列集合、type、nullability、default 与 CHECK 约束 |
| `test_story_workspace_review_persistence_fresh_defaults` | 新行默认为 active/null/null/null |
| `test_story_workspace_review_persistence_migrates_legacy_rows` | legacy pending/confirmed/rejected 数据按 §5 Step 4 backfill 且原字段不变 |
| `test_story_workspace_review_persistence_migration_idempotent` | `create_tables()` 连续执行两次无重复列和数据漂移 |
| `test_story_workspace_review_notes_length_constraint` | 2000 字符成功，2001 字符被 SQLite 拒绝 |
| `test_story_workspace_asset_status_constraint` | active/archived 成功，published/deleted/其他值被拒绝 |
| `test_story_workspace_review_persistence_round_trip` | character / scene 的 confirm、reject、archive 字段可直接 DB 写入后重读；不实现 HTTP |
| `test_story_workspace_review_contract_v1_1` | enum、四字段、默认值、常量、`__all__` 与版本均冻结 |
| `test_story_workspace_review_request_notes_boundary` | canonical request 对 `None`、2000、2001 字符执行边界校验 |

### 8.2 仓库根目录最小测试命令

```bash
python -m py_compile backend/database.py backend/story_workspace/contracts.py backend/tests/test_database.py backend/tests/test_story_workspace_contracts.py
python -m unittest backend.tests.test_database backend.tests.test_story_workspace_contracts -v
git diff --check -- backend/database.py backend/story_workspace/contracts.py backend/tests/test_database.py backend/tests/test_story_workspace_contracts.py docs/exec/exec_task_203a_story-workspace-review-persistence-schema.md
shasum -a 256 backend/database.py backend/story_workspace/contracts.py
```

从仓库根目录执行，禁止为了本任务引入 pytest、修改依赖或运行无关的全仓构建。

## 9. 验收条件与完成标志

| 验收 ID | 通过条件 | 唯一证据 |
|---|---|---|
| `AC-203A-01` | character / scene 均精确新增 `status`、`review_notes`、`confirmed_at`、`archived_at`，类型/default/nullability 与 §4.1 一致 | Schema contract test + `PRAGMA table_info` |
| `AC-203A-02` | status 仅 active/archived；review_notes 最长 2000 Unicode 字符；2001 字符无写入 | constraint tests |
| `AC-203A-03` | fresh database 与 legacy database 最终 Schema 一致，migration 可重复执行 | fresh + legacy + idempotency tests |
| `AC-203A-04` | legacy 行回填 active/null/null/null，confirmed/rejected 状态保留且不伪造时间/备注 | legacy migration test |
| `AC-203A-05` | canonical contract 为 v1.1.0，唯一 owner、enum、字段、常量、请求边界完整 | canonical contract tests |
| `AC-203A-06` | 两类资源四字段均可持久化 round-trip；无 route、side table 或内存 fallback | DB round-trip + path scan |
| `AC-203A-07` | 仅允许路径有本 task diff，story Schema/语义、router、frontend 与流水线上游文件无本 task diff | scoped diff / name-only 检查 |
| `AC-203A-08` | 最小命令全绿；旧/新 database hash 与 canonical hash 已记录且可重算 | exec report + Issue 评论 |
| `AC-203A-09` | StagePlanner 九项 readiness 全部 PASS，独立 execute Issue / single assignee / checkout 就绪后才释放 task_203 | Stage 记录 + Paperclip 状态 |

完成标志：`AC-203A-01`～`AC-203A-09` 均有证据；本 task 的 execute Issue 为 `done`；新 hash 已重冻结；[SUO-309](/SUO/issues/SUO-309) 的 blocker 与共享路由锁由 CEOOrchestrator / StagePlanner 按 §10 显式处理。Task 实现者不得自行提前唤醒或执行 `task_203`。

## 10. StagePlanner 九项 Readiness 与共享路由释放条件

| # | 检查项 | `task_203a` 通过标准 |
|---:|---|---|
| 1 | task 任务内容存在 | 本文件存在且 `task_203` 已声明硬依赖 |
| 2 | 关联 execute Issue | 为 `task_203a` 创建独立、可 checkout 的单 task execute Issue；不得复用 [SUO-317](/SUO/issues/SUO-317) 的 task 定义 checkout |
| 3 | Stage 允许 execute | Stage 增量明确插入 `task_203a → task_203`，且前序 canonical / shared baseline 已释放 |
| 4 | Prompt template 存在 | execute 时由执行 Agent 复制并完整填充 `TASK-REQUIREMENT-FORMAT.md`；本 task 定义 Issue 不填充它 |
| 5 | Allowed 范围明确 | 仅 §6.1 五个路径 |
| 6 | Forbidden 范围明确 | §6.2 全量带入 execute Issue 与填充模板 |
| 7 | 验收条件明确 | `AC-203A-01`～`AC-203A-09` 不得删减或放宽 |
| 8 | 测试/验证明确 | §8 最小命令、旧/新 hash、fresh/legacy migration 证据齐全 |
| 9 | checkout 与 single assignee | `task_203a` 独立 execute Issue 有唯一 assignee 与独立 checkout；不得与 `task_203` 并发 |

`backend/routers/story_workspace.py` 只有在以下条件**全部满足**后才可重新释放给 `task_203`：

1. `task_203a` execute Issue 已 `done`，`AC-203A-01`～`AC-203A-08` 有可复核证据；
2. `backend/database.py` 新 SHA-256 与 canonical contract SHA-256 已在 execute report 和 Issue 线程双写并可重算；
3. StagePlanner 已把 `task_203a → task_203` 写成硬依赖并完成上述九项 readiness，结论为 PASS；
4. `task_204` / `task_205b` 的既有共享路由与 canonical 基线未回退，当前没有其他 task checkout 或修改该 router；
5. CEOOrchestrator 显式解除 [SUO-309](/SUO/issues/SUO-309) 的 Schema blocker，并为其建立新的单一 checkout；
6. `task_203` 执行输入使用新冻结 database hash，且将 `backend/database.py` 与 canonical contract 视为只读，禁止再次补列或改变本合同。

任一条件未满足时，共享路由保持不释放，[SUO-309](/SUO/issues/SUO-309) 保持 blocked。

## 11. 回滚与兼容策略

- 代码回滚：回退本任务对四个 backend source/test 文件的 diff，并保持 [SUO-309](/SUO/issues/SUO-309) blocked。
- 已迁移数据库：本任务不以 `DROP COLUMN` 作为在线自动回滚。新增列是 additive，旧代码可忽略；如必须恢复物理 Schema，只能从迁移前备份恢复或另建受审计的 SQLite table-rebuild 工作单。
- 不得在回滚时把 `archived` 行静默改回 active、删除 `review_notes` 或伪造时间戳。已产生的新语义数据必须先导出/保全。
- hash 回滚：只有代码与数据库恢复到同一已验证基线且 tests 通过，才能重新冻结 hash；不得仅把文档中的摘要改回旧值。

## 12. 风险提示

| 风险 | 影响 | 处置 |
|---|---|---|
| character 已有 `notes`，容易被误当 reject 备注 | 破坏用户普通备注语义 | 独立 `review_notes`，migration 禁止复制 |
| legacy confirmed 行没有真实确认时间 | 伪造审计事实 | `confirmed_at=NULL`，仅新 confirm 写时间 |
| archive status 与 story status 混用 | character / scene 被错误允许 published | 独立 `StoryWorkspaceAssetStatus`，数据库只允许 active/archived |
| fresh DDL 与 ALTER migration 漂移 | 新旧环境行为不一致 | 同一字段矩阵 + fresh/legacy 双路径 tests |
| 宽泛异常吞掉 migration 失败 | 部分列存在却误报成功 | PRAGMA introspection + 非重复列错误 fail-fast |
| task_203 提前开始 | router 产生不可持久化或双轨逻辑 | 硬 blocker、九项 readiness、hash 与 checkout Gate |

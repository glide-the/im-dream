# Exec Report: task_210a - Deck Plugin Binding 与 Selection Validation

## 1. 执行上下文

- Task ID: `task_210a_backend_deck_plugin_binding`
- 执行 Issue: [SUO-296](/SUO/issues/SUO-296)
- 来源业务项: `DECK-005`；来源清单 [SUO-223](/SUO/issues/SUO-223)
- Parent / Ancestor: [SUO-217](/SUO/issues/SUO-217) / [SUO-216](/SUO/issues/SUO-216)
- 关联设计稿: `docs/design/deck-plugin-voice-ink-dream-integration.md` §6.3、§6.4、§9.1–§9.3、§13.2、§14.2
- 关联 Task: `docs/task/task_210a_backend_deck_plugin_binding.md`
- 关联 Stage: `docs/stage/stage_deck-plugin-voice-ink-dream-integration.md`，Stage 2 / Wave 1
- 执行 Agent: `ExecTaskAgent`
- 执行时间: `2026-08-01 18:54–19:07 CST`
- 状态 / Work mode / 优先级: `in_progress` / `standard` / `high`（Task 业务优先级 P0）
- Execution lock: harness 已为本 run 独占 checkout，按 wake 指令未重复调用 checkout
- Blockers: 无

### Stage 准入证据

本次 wake 的 Readiness 裁决明确九项准入全部通过，并确认 Stage 1 前置 [SUO-263](/SUO/issues/SUO-263)、[SUO-268](/SUO/issues/SUO-268)、[SUO-271](/SUO/issues/SUO-271)、[SUO-274](/SUO/issues/SUO-274) 均为 `done`，并行 Preflight [SUO-281](/SUO/issues/SUO-281) 已完成，最终 Stage 复核为 [SUO-290](/SUO/issues/SUO-290)。没有未满足的 Stage 条件或冻结点。

### 工作树基线与冲突处理

执行开始前已记录 `git status --short`。工作树包含其他任务的大量未提交/未跟踪成果；与本 task 授权路径重叠的既有内容包括：

- `backend/models/deck_plugin.py`: 未跟踪，已含 DECK-001/002/003/004 上游模型。
- `backend/database.py`: 已修改，已含 Story Workspace 与 DECK-001/002/003/006 表。
- `backend/server.py`: 已修改，已含 Story Workspace router 的 import/include。

上述重叠均可按独立追加区段安全合并。本次没有重置、覆盖、清理或格式化既有改动；禁止范围中的既有脏文件保持原状。

## 2. TASK-REQUIREMENT-FORMAT.md 填充记录

- 模板路径: `docs/task/TASK-REQUIREMENT-FORMAT.md`
- 执行角色: `ExecTaskAgent`
- 单一执行目标: 实现 DECK-005 后端的 next-run binding 持久化、查询/options、原子 revision 保存、selection validation 与四个认证 API。
- 交付类型: backend implementation + focused tests + exec report
- 明确排除: frontend、其他 Deck task、Workflow Run/Preflight 内部实现、通用错误码注册表、ClaudeAgent/Paperclip Plugin runtime、Stage/Issue/Task/Design 改写。
- Issue 输入: [SUO-296](/SUO/issues/SUO-296)，标题为 `[execute][deck-plugin][task_210a] 实现 Deck Plugin Binding 与 Selection Validation`。
- Domain / 标签: `backend` / `deck-plugin`, `binding`, `selection`, `backend`, `api`
- Assignee: `ExecTaskAgent`，唯一执行 owner
- 最新上游意见: 九项准入通过；独立 checkout；七路径代码闭集；12 项验收；无 blocker。
- Task 输入: DECK-001 release、DECK-003 installation、DECK-004 compatibility/permission、当前 SQLite binding、认证 actor 与精确版本请求。
- Task 输出: 可审计 binding revisions、当前 binding、options、validation、冲突/不可选的脱敏响应。
- 直接依赖: task_001 + task_003 + task_004；均由 wake 裁决满足。
- Stage / Wave: Stage 2 / Wave 1；可与 task_006 并行，完成后冻结 task_212 的后端 fixture。
- 并行约束: 不与其他 Issue 共用执行锁；不触碰 task_006 或 task_212 ownership。
- 回滚要求: 先移除 router 注册，再回退本 task router/service/model；已写 binding revision 默认保留，禁止物理删除历史数据。
- 未满足条件: 无。

### 2.1 写入边界（完整闭集）

| 路径 | 动作 | 最小授权变更 |
|---|---|---|
| `backend/models/deck_plugin.py` | update | 仅 Binding、selection 与本 task DTO |
| `backend/services/deck_plugin/binding_service.py` | create | binding 查询、保存、revision 与 Deck/workspace 访问 gate |
| `backend/services/deck_plugin/selection_validation_service.py` | create | 编排 release、installation、DECK-004 compatibility/permission/readiness |
| `backend/routers/deck_plugin_binding.py` | create | 仅四个 binding/options/validate endpoint |
| `backend/database.py` | update | binding 表、约束、索引、幂等初始化 |
| `backend/server.py` | update | 仅 import/include 本 task router |
| `backend/tests/test_deck_plugin_binding.py` | create | 本 task 定向测试 |
| `docs/exec/exec_task_210a_backend_deck_plugin_binding.md` | create | 唯一非实现例外与正式报告 |

禁止修改：`frontend/`；`docs/design/`、`docs/issue/`、`docs/task/`、`docs/stage/`；其他 `docs/exec/`；`backend/routers/voice_decks.py`、`backend/routers/story_workspace.py`、`backend/services/errors/error_registry.py`；其他 Deck task、runtime、依赖锁、部署配置、生成物和未列入闭集的任何实现/测试。

### 2.2 验收与验证输入

原始 12 项验收和全部必测场景已逐项带入模型输入，未删除或放宽。验证命令为：

1. `python -m py_compile backend/models/deck_plugin.py backend/services/deck_plugin/binding_service.py backend/services/deck_plugin/selection_validation_service.py backend/routers/deck_plugin_binding.py`
2. `pytest -q backend/tests/test_deck_plugin_binding.py`
3. 七路径、正式报告、未跟踪新文件的 whitespace 与范围检查。

模板填充后无未替换占位符、N/A 模糊项或多 task 合并，满足 Model Execution Instruction 准入。

## 3. 模型生成的执行任务

- 任务目标: 提供可审计、仅作用于下一次运行的 Deck Plugin Binding 后端合同。
- 实现范围:
  1. 追加严格 Pydantic Binding/Request/Response/Validation DTO。
  2. 新增保留历史 revision、单一 active revision 的 SQLite schema。
  3. 用 `BEGIN IMMEDIATE`、revision compare 与同事务 stale+insert 实现 CAS。
  4. 编排 DECK-004 `CompatibilityService`，只接受服务端 `RuntimeContext` resolver，不接受客户端裁决。
  5. 暴露权限过滤 options、current binding、PUT save、POST validate 四个认证 endpoint。
  6. 覆盖成功、不可选、冲突、越权、并发、脱敏和历史来源不变。
- 范围校验: 生成任务仅涉及闭集八路径，未生成 frontend、Workflow Run、Preflight 或 runtime 实现，可进入实施。

## 4. 实现变更记录

| 文件 | 操作 | 最小变更说明 |
|---|---|---|
| `backend/models/deck_plugin.py` | update | 追加 Binding status/apply-to、Binding 实体、save/validate DTO、current/options/success/conflict 响应与字段一致性校验；版本仅接受精确 SemVer |
| `backend/services/deck_plugin/binding_service.py` | create | 新增 Deck/workspace owner gate、当前 revision 查询、原子 `BEGIN IMMEDIATE` compare-and-swap、历史 revision stale 保留与当前响应组装 |
| `backend/services/deck_plugin/selection_validation_service.py` | create | 编排 release、installation、existing CompatibilityService、permission/readiness；未知 server runtime context 默认 fail closed；生成安全 reason/recovery/capability summary |
| `backend/routers/deck_plugin_binding.py` | create | 新增四个 `/api/voice-decks/{deck_id}` endpoint；全部复用 `get_current_user`；稳定返回 404、409、422 与脱敏 payload |
| `backend/database.py` | update | 追加 `deck_plugin_bindings` 表、`deck_id + revision` 唯一约束、单 active partial unique index 与 workspace/release 查询索引 |
| `backend/server.py` | update | 仅新增 binding router import 与一次 `include_router` |
| `backend/tests/test_deck_plugin_binding.py` | create | 新增 12 项测试和 10 个状态子场景，覆盖模型/schema/service/concurrency/router/security |
| `docs/exec/exec_task_210a_backend_deck_plugin_binding.md` | create | 本执行报告 |

### 关键实现语义

- 每个 save 在同一 `BEGIN IMMEDIATE` 事务中重新验证 Deck/workspace owner、比较 `expected_binding_revision`、执行 selection validation、把旧 active 改为 stale 并插入新 active revision。
- 任何 conflict、validation 失败或插入失败都会 rollback；409 payload 固定为 `error_code/current_revision/message`。
- `apply_to` 由 DTO 与数据库 CHECK 双重固定为 `next_run`；Binding API 不读取或更新 Workflow Run。
- 历史 binding revision 不物理删除；`deck_id + binding_revision` 唯一且每个 Deck 最多一个 active revision。
- options 只展示 `published/deprecated/revoked` 的安全 release 元数据，不返回 manifest、runtime lock、source path、prompt、secret 或命令输出。
- selection validation 复用 DECK-004 固定八步服务；runtime/permission 输入只允许服务端 resolver 注入。resolver 缺失、异常或结构非法时返回 `RUNTIME_CONTEXT_UNAVAILABLE`，不猜测通过。
- workspace installation 优先；不存在时只允许使用 instance installation。Deck/workspace 均须属于当前认证 actor，缺失与越权使用相同 404，避免存在性泄露。

## 5. 测试与验证

### 已执行命令

1. 静态检查：

   `PYTHONPYCACHEPREFIX="$PAPERCLIP_RUN_SCRATCH_DIR/pycache-final" python -m py_compile backend/models/deck_plugin.py backend/services/deck_plugin/binding_service.py backend/services/deck_plugin/selection_validation_service.py backend/routers/deck_plugin_binding.py`

   结果：exit code `0`，无语法错误；bytecode 定向写入 run scratch，未污染工作树。

2. 定向测试：

   `PATH="$PWD/backend/.venv/bin:$PATH" PYTHONPYCACHEPREFIX="$PAPERCLIP_RUN_SCRATCH_DIR/pycache-final" pytest -q backend/tests/test_deck_plugin_binding.py`

   结果：`12 passed, 10 subtests passed in 1.00s`。

3. 已跟踪差异检查：

   `git diff --check -- backend/models/deck_plugin.py backend/services/deck_plugin/binding_service.py backend/services/deck_plugin/selection_validation_service.py backend/routers/deck_plugin_binding.py backend/database.py backend/server.py backend/tests/test_deck_plugin_binding.py`

   结果：exit code `0`，无 whitespace error。未跟踪新文件另以 `git diff --no-index --check /dev/null <file>` 检查，无 whitespace 诊断。

### 验收结果

| # | 验收条件 | 结果 | 证据 |
|---|---|---|---|
| 1 | Binding 模型、表、唯一约束、幂等初始化 | PASS | DTO/schema 测试；重复 `create_tables`；四索引与 partial unique index 断言 |
| 2 | 当前 binding 与权限过滤 options | PASS | current 空/有值状态、options fixture 与 Deck/workspace owner gate 测试 |
| 3 | 精确版本与 `apply_to=next_run` | PASS | `latest`、range、wildcard、缺失/非法版本及 `current_run` 全部被拒绝 |
| 4 | revision 原子比较并单调递增 | PASS | revision `0→1→2`；历史 stale/当前 active；并发 CAS 单一 winner |
| 5 | 409 conflict 无静默覆盖 | PASS | 固定 409 fixture；冲突后 row count/revision 不变 |
| 6 | selection validation 覆盖六类权威输入 | PASS | published/revoked、ready/disabled/upgrade_pending、host incompatible、permission denied、runtime not ready |
| 7 | 四 endpoint 使用现有 auth | PASS | router method 集合断言；未认证请求返回 401；统一 `get_current_user` dependency |
| 8 | 不反写当前/历史 Workflow Run | PASS | 冻结 source tuple 在 save 后逐字段不变；实现无 Workflow Run DML |
| 9 | 定向测试全部通过 | PASS | `12 passed, 10 subtests passed` |
| 10 | 成功/不可选/冲突响应冻结且脱敏 | PASS | 精确 key 集合、409 全量 fixture、422 validation fixture、敏感 token/path/stack/command 排除断言 |
| 11 | 实际改动严格位于闭集 | PASS | 所有 apply patch 仅命中八个授权路径；基线外部脏文件未触碰 |
| 12 | Issue 回填验收/命令/diff/回滚 | PASS | 本报告与最终 Issue comment/status 回填 |

### 未执行测试及原因

- 未运行全仓测试：Task 明确要求最小定向测试，且共享工作树包含多个并行任务的未提交成果；全仓结果不能单独归因于本 task。
- 未执行真实 ClaudeAgent/runtime materialization：runtime 内部实现明确禁止修改；本 task 只消费服务端 resolver 裁决，默认 fail closed。
- 未做 frontend E2E：`frontend/` 属于 task_212 且在禁止范围。

## 6. 风险与阻塞

- 阻塞: 无。
- 风险: 当前仓库没有本 task 可直接消费的生产 runtime-context adapter；router 的默认 validator 因此返回安全的 `RUNTIME_CONTEXT_UNAVAILABLE`，不会把缺失的 host/schema/permission/materialization 事实猜测为通过。已通过注入式权威 context 覆盖完整成功合同；真实 adapter 接入必须由其 owning task/服务授权完成。
- 风险: SQLite `BEGIN IMMEDIATE` 提供当前单节点原子性；本 task 不宣称多节点数据库语义。
- 工作树冲突: 授权共享文件的既有改动已按独立区段安全合并；无无法合并项。
- 需要上游澄清的问题: 无。

## 7. 完成状态

- [x] 已完成实现
- [x] 已完成静态检查
- [x] 已完成定向测试
- [x] 已记录全部本 task 变更
- [x] 已逐项满足验收条件
- [x] 已确认未修改禁止范围
- [x] 可进入 review / audit

建议 Issue 最终状态：`done`。本执行 Issue 无剩余实现、测试或需要等待的真实 reviewer/blocker 路径。

## 8. 回滚建议

1. 先从 `backend/server.py` 移除本 task 的 binding router import/include，停止新写入。
2. 删除 `backend/routers/deck_plugin_binding.py`、`backend/services/deck_plugin/binding_service.py`、`backend/services/deck_plugin/selection_validation_service.py`。
3. 从 `backend/models/deck_plugin.py` 精确移除本 task 末尾的 Binding/selection DTO 区段，保留 DECK-001/002/003/004 上游模型。
4. 从 `backend/database.py` 精确移除 `deck_plugin_bindings` 建表和四个索引区段，保留其他 Deck Plugin/Story Workspace schema。
5. 删除 `backend/tests/test_deck_plugin_binding.py`；本报告按治理要求归档或删除时不得触碰其他 `docs/exec/`。
6. 已产生的 binding revisions 默认保留；只有证明表为空、无历史引用且获得明确数据回滚授权后才能 drop schema。
7. 禁止使用 `git reset --hard`、目录级 checkout/clean 或整文件覆盖，因为共享工作树含其他任务成果。

## 9. 执行完成报告

`task_210a_backend_deck_plugin_binding` 的模型、持久化、原子 revision、selection validation 编排、四个认证 API 与脱敏 fixture 已在授权闭集内完成。静态检查、12 项定向测试、10 个状态子场景、whitespace 与范围检查均通过；实现不修改 frontend、设计/Issue/Task/Stage 文档、其他 router、Workflow Run 或 runtime 内部状态，可进入 review / audit。

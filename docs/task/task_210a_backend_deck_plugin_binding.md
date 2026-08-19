# Task: Deck Plugin Binding 与 Selection Validation（Backend）

> **Task ID**: `task_210a_backend_deck_plugin_binding`
> **源 Issue**: `DECK-005` (from `SUO-223` / `SUO-218`)
> **Readiness 修订 Issue**: `SUO-279`
> **类型**: `backend`
> **优先级**: `P0`
> **标签**: `deck-plugin`, `binding`, `selection`, `backend`, `api`
> **生成日期**: 2026-08-01
> **状态**: `ready_to_execute`（StagePlanner 复核通过；Stage 1 Gate 通过后启动）
> **唯一执行责任人**: `ExecTaskAgent`（`backend` 仅表示任务类型，不是 Agent 名称）
> **Stage 映射**: Stage 2 / Wave 1（替代 shared `task_210` 的后端 execute 节点）

---

## 1. 任务标题

DECK-005 Backend：Deck Plugin Binding 持久化、API 与 Selection Validation

---

## 2. 关联 Issue

| 关联 | ID / 路径 | 说明 |
|---|---|---|
| 源业务 Issue | `DECK-005` | Deck 创建/编辑的插件选择与版本绑定 |
| Readiness Issue | `SUO-279` | 将 shared binding 拆成可独立 checkout 的后端执行单元 |
| 父控制项 | `SUO-217` | Deck Plugin 设计与执行治理 |
| Design Issue | `SUO-218` | Voice Decks × Ink Dream 集成设计 |
| Issue 清单 | `SUO-223` | Deck Plugin Issue 拆解 |
| Shared 合同索引 | `docs/task/task_210_shared_deck_plugin_binding.md` | 只读消费字段、API 与跨端 Gate；不可作为执行授权 |
| 前端消费单元 | `docs/task/task_212_frontend_deck_editor_plugin_binding.md` | 唯一 Deck Editor binding UI 执行单元 |
| Stage | `docs/stage/stage_deck-plugin-voice-ink-dream-integration.md` | Stage 2 Wave 1；依赖 Stage 1 Gate |
| Design | `docs/design/deck-plugin-voice-ink-dream-integration.md` §9.1–§9.3、§13.2、§14.2 | 选择、并发、边界与 API 真相源 |

---

## 3. 任务目标

实现且仅实现 DECK-005 的后端边界：

1. 持久化同一 Deck 的下一次运行 `DeckPluginBinding`，引用精确 `deck_plugin_id` + `deck_plugin_version`。
2. 提供当前 binding、权限过滤后的 release options、保存 binding 与 selection validation API。
3. 使用 `expected_binding_revision` 做原子乐观锁；成功 revision 单调递增，冲突返回 `409 BINDING_REVISION_CONFLICT`。
4. 保存前执行精确版本、release、installation、兼容性、权限和已知 runtime readiness 校验。
5. 只改变下一次运行的 binding；不得反写当前或历史 Workflow Run 的冻结来源。
6. 为 `task_212_frontend_deck_editor_plugin_binding` 提供冻结、脱敏且可测试的响应合同。

### 3.1 唯一 ownership

- 本 task 的独立 execute Issue 仅允许单一 assignee `ExecTaskAgent` checkout；同一时刻不得由第二个 Agent 共同或重复 checkout。
- `backend` 仅是本 task 的 domain；任何 domain 标签或历史角色名都不得解释为可 checkout 的 Agent。
- 本 task 不拥有任何 frontend 文件、组件、hook、client 或交互测试。
- Shared `task_210` 只维护合同索引；不得与本 task 共同承载实现。
- `task_212` 只消费本 task 的 API；不得在客户端复制 selection validation、权限或兼容性裁决。

### 3.2 固定业务不变量

- 版本必须是精确 SemVer；拒绝 `latest`、范围和其他可变引用。
- `binding_revision` 按 Deck 单调递增；比较与写入必须处于同一原子事务。
- `apply_to` 固定为 `next_run`。
- 当前/历史 run 已冻结的 `deck_plugin_binding_id`、revision、release 与 runtime lock 不可被更新。
- selection validation 是配置阶段快速校验，不替代绑定输入 hash/runtime snapshot 的 execution preflight。
- 响应只返回安全 reason code、恢复动作和脱敏摘要；禁止堆栈、路径、prompt、secret 或完整命令输出。

---

## 4. 实现步骤

### 步骤 1：定义模型与持久化

1.1 在 Deck Plugin 领域模型中追加 `DeckPluginBinding`：

```text
deck_plugin_binding_id
deck_id
workspace_id
creator_id
deck_plugin_id
deck_plugin_version
binding_revision
status              # active | stale
applied_to           # next_run
created_at
updated_at
```

1.2 增量增加 binding 表、唯一约束与索引：

- 同一 Deck 仅有一个当前 `active` binding；历史 revision 保持可审计或按现有数据库模式保留。
- `deck_id + binding_revision` 必须唯一。
- 表初始化幂等，不改变 DECK-001/003/004 已有表语义。

### 步骤 2：实现查询与 options

2.1 当前 binding 查询返回精确 release、revision、`applied_to=next_run` 和脱敏 validation 摘要。

2.2 options 查询消费 DECK-001/003/004 的权威 release、installation、compatibility 与权限结果，返回：

- `display_name`、`deck_plugin_id`、`deck_plugin_version`；
- `release_status`、`installation_status`、`compatibility`、`runtime_readiness`；
- `selectable`、安全 `reason_code`、恢复 owner/action；
- capability 摘要，不返回 secret 或服务端内部细节。

### 步骤 3：实现保存与乐观锁

3.1 `PUT` 请求必须携带：

```jsonc
{
  "deck_plugin_id": "voice-decks.story-dramatize",
  "deck_plugin_version": "3.1.0",
  "expected_binding_revision": 8,
  "apply_to": "next_run"
}
```

3.2 服务端在同一事务中：

1. 校验 workspace/Deck 访问权限；
2. 校验精确版本格式；
3. 读取并比较当前 revision；
4. 执行 selection validation；
5. 条件写入新 binding revision；
6. 返回新 revision 与 validation 摘要。

3.3 revision 不匹配时不得写入，返回 HTTP 409：

```jsonc
{
  "error_code": "BINDING_REVISION_CONFLICT",
  "current_revision": 10,
  "message": "Binding was modified concurrently. Please refresh and confirm your selection."
}
```

### 步骤 4：实现 selection validation

4.1 校验顺序至少覆盖：

1. release 存在且为 `published`，或策略显式允许 `deprecated`；
2. installation 为 `ready`；
3. host API、story schema、Deck runtime contract 的静态兼容性通过；
4. actor 对 workspace/Deck/release 有选择权限；
5. runtime readiness 已知且达到配置阶段允许值；
6. revoked、disabled、incompatible、permission_denied、upgrade_pending 均不可保存。

4.2 校验失败不得产生新 revision；返回结构化 reason code 和安全恢复动作。

### 步骤 5：提供独立 API 模块并接入应用

| Method | Path | 行为 |
|---|---|---|
| `GET` | `/api/voice-decks/{deck_id}/plugin-options` | 返回权限过滤后的 release options |
| `GET` | `/api/voice-decks/{deck_id}/plugin-binding` | 返回当前下一次运行 binding/revision |
| `PUT` | `/api/voice-decks/{deck_id}/plugin-binding` | 保存精确 release 与新 revision |
| `POST` | `/api/voice-decks/{deck_id}/plugin-binding/validate` | 只做 selection validation，不创建 Workflow Run |

- 路由放入本 task 的独立 binding router，应用入口只做最小 `include_router` 接入。
- 不修改 `task_deck_014` 所属的通用错误码注册表或其他 Deck/Story Workspace 路由。
- 保持现有 auth middleware，不新增旁路认证。

### 步骤 6：补齐测试与前端 fixture

6.1 后端测试覆盖模型、持久化、API、并发、validation 与安全响应。

6.2 固定成功、不可选和 revision conflict 的脱敏 JSON fixture 形状，供 `task_212` 前端测试消费；fixture 作为测试内常量或现有测试机制的一部分，不新增越界文档/生成物。

---

## 5. 涉及文件路径

| 路径 | 动作 | 最小变更 |
|---|---|---|
| `backend/models/deck_plugin.py` | 修改 | 仅追加 `DeckPluginBinding` 与本 task 请求/响应模型 |
| `backend/services/deck_plugin/binding_service.py` | 新建 | binding 查询、保存、revision 原子更新 |
| `backend/services/deck_plugin/selection_validation_service.py` | 新建 | 编排既有 release/installation/compatibility/权限判定 |
| `backend/routers/deck_plugin_binding.py` | 新建 | 仅四个 binding/options/validate endpoint |
| `backend/database.py` | 修改 | 仅增量追加 binding 表、索引与幂等初始化 |
| `backend/server.py` | 修改 | 仅导入并注册本 task 的 router |
| `backend/tests/test_deck_plugin_binding.py` | 新建 | 本 task 的模型、服务、API、并发与安全测试 |

以上七个路径是未来 execute 的实现代码完整闭集；未列出的实现代码路径默认禁止。唯一非实现代码写入例外为 §11.2 指定的正式 exec report。

---

## 6. 输入 / 输出说明

### 输入

| 来源 | 内容 |
|---|---|
| DECK-001 | 精确 `DeckPluginRelease`、发布状态、manifest/capability 摘要 |
| DECK-003 | workspace/instance installation 状态与 runtime readiness |
| DECK-004 | 服务端兼容性、能力交集、权限与 reason code |
| 当前数据库 | Deck 当前 binding 与 `binding_revision` |
| HTTP 请求 | actor/workspace/Deck、精确版本、`expected_binding_revision`、`apply_to=next_run` |

### 输出

| 去向 | 内容 |
|---|---|
| 数据库 | 新的可审计 binding revision；不得改历史 run |
| `task_212` 前端 | 当前 binding、options、validation 摘要、冲突/不可选错误 |
| Preflight 下游 | 当前精确 binding id/revision，供权威 execution preflight 再校验 |
| 审计下游 | 可生成 `deck.plugin_binding.changed` 所需 old/new release、revision、actor 数据；事件落地仍由 DECK-013 负责 |

### 成功响应最低字段

```jsonc
{
  "deck_plugin_binding_id": "dpb_...",
  "deck_id": "deck_...",
  "deck_plugin_id": "voice-decks.story-dramatize",
  "deck_plugin_version": "3.1.0",
  "binding_revision": 9,
  "status": "active",
  "applied_to": "next_run",
  "selection_validation_summary": {
    "release_status": "published",
    "installation_status": "ready",
    "compatibility": "passed",
    "runtime_readiness": "materialized"
  }
}
```

---

## 7. 依赖项

| 依赖 | 类型 | 准入 / 交接要求 |
|---|---|---|
| `task_deck_001_backend_manifest-model` | 前置 | release 模型、精确版本与发布状态稳定 |
| `task_deck_003_backend_installation-lifecycle` | 前置 | installation/readiness 查询合同稳定 |
| `task_deck_004_backend_compatibility-capability` | 前置 | 服务端 compatibility/permission/reason code 合同稳定 |
| Stage 1 Gate | 已满足 | `SUO-279` 输入确认 Stage 1 已完成；execute Issue 仍须记录具体完成证据 |
| `task_deck_014_backend_api-error-codes` | 协作，不是本 task 前置 | 后续聚合通用 registry；不得重复实现本 task 的服务逻辑 |
| `task_212_frontend_deck_editor_plugin_binding` | 下游 | 后端响应合同与 fixture 冻结后独立 checkout |
| `task_deck_006_backend_workflow-preflight` | 下游 | 消费 binding id/revision；再次执行权威 preflight |

---

## 8. 测试策略

| 验证层 | 命令 / 方法 | 覆盖场景 | 通过标准 |
|---|---|---|---|
| 静态检查 | `python -m py_compile backend/models/deck_plugin.py backend/services/deck_plugin/binding_service.py backend/services/deck_plugin/selection_validation_service.py backend/routers/deck_plugin_binding.py` | 允许闭集内 Python 模块 | 无语法错误 |
| 单元/最小集成 | `pytest -q backend/tests/test_deck_plugin_binding.py` | 模型、数据库、服务、路由、并发与安全响应 | 全部通过，无越界 fixture/快照 |
| 差异检查 | `git diff --check -- docs/task/task_210a_backend_deck_plugin_binding.md`（规划）；execute 时对 §5 七个路径逐项检查 | 格式、闭集、意外写入 | 无 whitespace error；实际写入不超闭集 |

必须覆盖：

1. 首次保存与后续 revision 单调递增；
2. 两个并发请求只有匹配 revision 的请求成功；
3. 冲突返回 409 且数据库不写入；
4. 拒绝 `latest`、范围、缺失或非法版本；
5. revoked/disabled/incompatible/permission_denied/upgrade_pending 不可选；
6. validation 失败不创建 revision，validate endpoint 不创建 Workflow Run；
7. actor/workspace/Deck 越权被拒绝且不泄露存在性细节；
8. 当前与历史 run 来源在 binding 更新后保持不变；
9. API 响应不含 secret、prompt、路径、堆栈或完整命令输出；
10. router 注册后四个 endpoint 可访问，其他路由行为不变。

---

## 9. 完成标志

- [ ] `DeckPluginBinding` 模型、表、唯一约束与幂等初始化完成
- [ ] 当前 binding 与权限过滤 options 查询完成
- [ ] 保存只接受精确版本和 `apply_to=next_run`
- [ ] `expected_binding_revision` 在原子事务中比较并单调递增
- [ ] 冲突稳定返回 `409 BINDING_REVISION_CONFLICT`，无静默覆盖
- [ ] selection validation 覆盖 release、installation、compatibility、权限和 readiness
- [ ] 四个 API endpoint 按 §4.5 提供且使用现有 auth middleware
- [ ] binding 更新不反写当前/历史 Workflow Run 来源
- [ ] `backend/tests/test_deck_plugin_binding.py` 全部通过
- [ ] 前端可消费的成功、不可选、冲突响应字段冻结且脱敏
- [ ] 实际改动严格位于 §5 七个路径闭集内
- [ ] execute Issue 评论逐项回填验收、命令、结果、diff 与回滚说明

---

## 10. 风险提示

| 风险 | 等级 | 缓解 |
|---|---|---|
| revision 读取与写入非原子导致丢失更新 | 高 | 单事务条件更新；并发测试断言只有一个写入成功 |
| 与 DECK-014 路由 ownership 重叠 | 中 | 本 task 只拥有独立 binding router 与最小注册；通用 registry/其他路由留给 DECK-014 |
| 复制 DECK-003/004 判定造成漂移 | 高 | 只编排权威服务，不复制生命周期、兼容性或权限算法 |
| binding 表或历史 revision 清理破坏审计 | 高 | 保留历史引用；默认不物理删除；回滚不删生产数据 |
| `backend/server.py` 有其他未提交改动 | 中 | execute 前检查基线；不能最小安全合并时停止并在 Issue 评论标注 owner/action |
| DECK-016 物理服务边界未决 | 中 | 保持逻辑 API 与独立 router；物理拆分由 gateway/后续 task 适配 |

---

## 11. 允许修改范围与禁止修改范围

### 11.1 未来 execute 允许闭集

- `backend/models/deck_plugin.py`（仅 Binding 与本 task DTO）
- `backend/services/deck_plugin/binding_service.py`（仅 binding 查询/保存/revision）
- `backend/services/deck_plugin/selection_validation_service.py`（仅编排权威校验）
- `backend/routers/deck_plugin_binding.py`（仅 §4.5 四个 endpoint）
- `backend/database.py`（仅 binding 表、索引、幂等初始化）
- `backend/server.py`（仅 import/include 本 task router）
- `backend/tests/test_deck_plugin_binding.py`（仅本 task 测试）

### 11.2 未来 execute 禁止范围

- `frontend/` 全部路径；前端唯一 ownership 属于 `task_212`
- execute 阶段禁止改写 `docs/design/`、`docs/issue/`、`docs/task/`、`docs/stage/`
- `docs/exec/` 仅有一个精确例外：允许 `ExecTaskAgent` 写正式报告 `docs/exec/exec_task_210a_backend_deck_plugin_binding.md`；禁止修改、覆盖、移动或删除其他任何 `docs/exec/` 文件
- `backend/routers/voice_decks.py`、`backend/routers/story_workspace.py`、`backend/services/errors/error_registry.py`
- DECK-001/003/004/006/007/013/014/015 的内部实现，及 Paperclip Plugin/ClaudeAgent runtime 实现
- 依赖锁、部署配置、生成物与未列入 §11.1 的任何测试或代码
- 借机重构、全文件格式化、清理无关代码，或覆盖工作树既有改动

### 11.3 当前规划阶段约束

本 task 文档由 `SUO-279` 规划产出，并由 `SUO-284` 增量修正 readiness 边界；`StagePlanner` 已在 `SUO-285` 完成复核并通过，本文档状态据此统一为 `ready_to_execute`。后续仍须由 `CEOOrchestrator` 独立执行 execute readiness check 并创建单独的 execute Issue，方可由 `ExecTaskAgent` 按七路径代码闭集实现；本 task 文档本身不授权任何实现，正式 exec report 仍仅可按 §11.2 的精确例外写入。

---

## 12. 回滚边界

1. 先移除 `backend/server.py` 中本 task router 注册，停止新 binding 写入。
2. 回退 router/service/model 的本 task 增量，不触碰其他 Deck Plugin 服务。
3. 已产生的 binding revision 默认保留以保护审计和历史引用；禁止把回滚等同于物理删除数据。
4. 仅在证明表为空、无历史引用且由 execute Issue 明确授权时，才能回滚 binding schema。
5. 回滚不得改变当前或历史 Workflow Run 的冻结来源，也不得要求前端回退其他 Deck Editor 功能。

---

## 13. 前后端联调边界

| 合同 | 后端 `task_210a` | 前端 `task_212` |
|---|---|---|
| binding/options/validate API | 唯一提供者 | 唯一消费者 |
| 精确版本、权限、兼容性、validation | 权威裁决 | 只展示结果 |
| revision 冲突 | 原子拒绝并返回当前 revision | 刷新并要求用户重新确认 |
| `next_run` 语义 | 持久化并保护历史来源 | 固定提示并禁止暗示当前 run 改绑 |
| 前端组件/hook/client | 禁止 | 唯一 ownership |
| 后端模型/service/router | 唯一 ownership | 禁止 |

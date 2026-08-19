# task_deck_014_backend_api-error-codes

> **Task ID**: `task_deck_014_backend_api-error-codes`
> **Readiness 修订 Issue**: [SUO-324](/SUO/issues/SUO-324)
> **Domain**: `backend`（仅用于分类，不代表执行 Agent 身份）
> **状态**: `pending_stage_recheck`
> **唯一执行责任人**: `ExecTaskAgent`
> **Stage 映射**: Stage 4 / Wave 1（独立 execute Issue、独立 checkout、独立验收）

## 1. 任务标题

API 路由与错误码规范

## 2. 关联 Issue

- **Issue ID**: `DECK-014`
- **Issue 标题**: API 路由与错误码规范
- **类型**: backend
- **优先级**: P1
- **标签**: `api`, `error-codes`, `contract`
- **来源设计稿**:
  - `docs/design/deck-plugin-voice-ink-dream-integration.md` §12.1, §14.1, §14.2, §14.3
- **Issue 清单**: `docs/issue/ISSUES_deck-plugin-voice-ink-dream-integration.md` §3 DECK-014
- **Readiness 修订**: [SUO-324](/SUO/issues/SUO-324)

## 3. 任务目标

实现设计稿中定义的逻辑 API 路由和错误码规范。`DECK-GATE-DEC-016` 已冻结：以下 router 是规范逻辑 API/gateway adapter，必须保留 Deck control plane、ClaudeAgent runtime control、story-workspace 三域单写；不得新增第三业务服务、让 gateway 持有权威状态或通过共享表双写。物理拆分不是本 task 的前置条件，未来拆分也只能替换 transport/deployment adapter，请求/响应语义和错误码不得丢失。

未来实现仅由 `ExecTaskAgent` 在本 task 的独立 execute Issue 中执行；`backend` 仅是 domain。本 task 不与其他 Stage 3/4 task 合并 checkout 或共享正式报告。

## 4. 实现步骤

### Step 1: 管理端 API 路由

在 `backend/routers/deck_plugins.py`（新建）中实现：

| Method | Path | 作用 | 最小权限 |
|---|---|---|---|
| `GET` | `/api/deck-plugins/installations` | 列安装项、版本、业务状态和 runtime readiness 摘要 | plugin admin/read |
| `POST` | `/api/deck-plugins/install` | 安装精确 release/source，携带 idempotency key | plugin admin |
| `GET` | `/api/deck-plugins/{deck_plugin_id}/versions/{version}` | 读 manifest、能力、兼容和 release hash | authorized reader |
| `POST` | `/api/deck-plugins/{deck_plugin_id}/enable` | 启用新选择/新 run | plugin admin |
| `POST` | `/api/deck-plugins/{deck_plugin_id}/disable` | 禁用并给出原因/撤销等级 | plugin admin |
| `POST` | `/api/deck-plugins/{deck_plugin_id}/upgrade` | 校验目标 release；能力扩张进入 pending | plugin admin |
| `POST` | `/api/deck-plugins/{deck_plugin_id}/rollback` | 显式切默认版本到旧 release | plugin admin |
| `GET` | `/api/deck-plugins/{deck_plugin_id}/runtime-readiness` | 按环境列 declared/materialized/loadable 状态 | plugin admin |
| `POST` | `/api/deck-plugins/{deck_plugin_id}/reconcile` | 触发受控声明式物化/诊断 | plugin admin/service |

### Step 2: Deck 创建/编辑 API 路由

在 `backend/routers/voice_decks.py`（新建或扩展）中实现：

| Method | Path | 作用 |
|---|---|---|
| `GET` | `/api/voice-decks/{deck_id}/plugin-options` | 返回权限过滤后的 release 列表及结构化不可选原因 |
| `GET` | `/api/voice-decks/{deck_id}/plugin-binding` | 返回当前下一次运行 binding/revision |
| `PUT` | `/api/voice-decks/{deck_id}/plugin-binding` | 保存精确 release；必须传 `expected_binding_revision` |
| `POST` | `/api/voice-decks/{deck_id}/plugin-binding/validate` | 执行 selection validation，不创建 Workflow Run |

Binding 保存请求：
```jsonc
{
  "deck_plugin_id": "voice-decks.story-dramatize",
  "deck_plugin_version": "3.1.0",
  "expected_binding_revision": 7,
  "apply_to": "next_run"
}
```

### Step 3: Story Workspace 执行 API 路由

在 `backend/routers/story_workspace.py`（新建或扩展）中实现：

| Method | Path | 作用 |
|---|---|---|
| `POST` | `/api/story-workspace/workflow-preflights` | 按 binding revision、输入 hash 做权威 preflight |
| `GET` | `/api/story-workspace/workflow-preflights/{id}` | 查询物化/检查进度和恢复信息 |
| `POST` | `/api/story-workspace/workflow-runs` | 用 passed token + idempotency key 原子创建运行 |
| `GET` | `/api/story-workspace/workflow-runs/{workflow_run_id}` | 返回状态、来源摘要、错误和结果引用 |
| `POST` | `/api/story-workspace/workflow-runs/{workflow_run_id}/retry` | 默认按原快照/锁创建新 run |
| `POST` | `/api/story-workspace/workflow-runs/{workflow_run_id}/cancel` | 按策略取消并记录 actor/reason |

创建运行请求：
```jsonc
{
  "workflow_preflight_id": "pf_...",
  "preflight_token": "opaque-short-lived-token",
  "idempotency_key": "client-uuid",
  "source_voice_thread_id": "optional-thread-id"
}
```

**关键约束**：响应中的来源字段由服务端从 preflight 和发布锁复制，客户端不得直接提交 `deck_plugin_version` 或 `deck_runtime_snapshot_id` 覆盖它们。

### Step 4: 错误码注册表

在 `backend/services/errors/error_registry.py`（新建）中定义：

```python
ERROR_REGISTRY = {
    # 安装阶段
    "DECK_PLUGIN_MANIFEST_INVALID": {
        "phase": "install",
        "meaning": "manifest/schema 不合法",
        "recovery": "发布者修复并发布新版本"
    },
    "DECK_PLUGIN_SOURCE_DENIED": {
        "phase": "install",
        "meaning": "来源不在 allowlist",
        "recovery": "管理员审批来源或选择受信来源"
    },
    "DECK_PLUGIN_INTEGRITY_FAILED": {
        "phase": "install",
        "meaning": "manifest/artifact digest 不匹配",
        "recovery": "隔离制品，禁止重试同 digest"
    },
    "RUNTIME_MARKETPLACE_UNAVAILABLE": {
        "phase": "install",
        "meaning": "marketplace 无法解析/下载",
        "recovery": "保留声明意图，修复网络/来源后重试"
    },
    "RUNTIME_PLUGIN_MATERIALIZATION_FAILED": {
        "phase": "install",
        "meaning": "settings 已声明但物化失败",
        "recovery": "显示 declared/not materialized，按 operation 重试"
    },
    # 兼容阶段
    "DECK_HOST_INCOMPATIBLE": {
        "phase": "compatibility",
        "meaning": "Deck host/API 不支持",
        "recovery": "升级 host 或选择兼容 release"
    },
    "CLAUDE_AGENT_INCOMPATIBLE": {
        "phase": "compatibility",
        "meaning": "Agent/Claude Code contract 不支持",
        "recovery": "升级 runtime 或回滚 release"
    },
    "STORY_SCHEMA_INCOMPATIBLE": {
        "phase": "compatibility",
        "meaning": "输出无法被 story-workspace 消费",
        "recovery": "发布兼容新 release；禁止部分写入"
    },
    # 配置阶段
    "DECK_RUNTIME_CONFIG_INVALID": {
        "phase": "config",
        "meaning": "配置缺失、未激活、过期",
        "recovery": "Deck owner 修复并重新 preflight"
    },
    "DECK_RUNTIME_CONFIG_INCOMPATIBLE": {
        "phase": "config",
        "meaning": "snapshot contract 不兼容",
        "recovery": "选择兼容 Deck runtime profile/release"
    },
    "DECK_RUNTIME_CONFIG_UNAVAILABLE": {
        "phase": "config",
        "meaning": "Deck 配置或快照解析暂时不可用",
        "recovery": "保留输入，以同一幂等语义重新 preflight"
    },
    # 权限阶段
    "WORKFLOW_PERMISSION_DENIED": {
        "phase": "permission",
        "meaning": "用户或服务身份权限不足",
        "recovery": "申请授权；不泄露敏感详情"
    },
    # 状态阶段
    "DECK_PLUGIN_DISABLED": {
        "phase": "status",
        "meaning": "release/installation 已禁用",
        "recovery": "管理员启用或用户显式选其他 release"
    },
    "DECK_PLUGIN_UPGRADE_PENDING": {
        "phase": "status",
        "meaning": "新能力等待审批",
        "recovery": "管理员审批；旧 ready 版本不受影响"
    },
    # 加载阶段
    "RUNTIME_PLUGIN_NOT_READY": {
        "phase": "load",
        "meaning": "required 插件未物化/loadable",
        "recovery": "等待/触发 reconcile；不启动 session"
    },
    "RUNTIME_PLUGIN_LOAD_FAILED": {
        "phase": "load",
        "meaning": "digest 已物化但会话加载失败",
        "recovery": "新 session 重试；持续失败转 installation error"
    },
    "RUNTIME_PLUGIN_RELOAD_UNSUPPORTED": {
        "phase": "load",
        "meaning": "热刷新前置不满足",
        "recovery": "改走新 session + headless reconcile"
    },
    # 会话阶段
    "AGENT_SESSION_START_FAILED": {
        "phase": "session",
        "meaning": "ClaudeAgent 会话未启动",
        "recovery": "保留 run/receipt 诊断，新 attempt 重试"
    },
    # 运行阶段
    "WORKFLOW_STEP_FAILED": {
        "phase": "run",
        "meaning": "已知步骤执行失败",
        "recovery": "记录 failed_step，按同锁新 run 重试"
    },
    "AGENT_EXECUTION_FAILED": {
        "phase": "run",
        "meaning": "超时、工具或运行时故障",
        "recovery": "记录公开摘要，按可重试性处理"
    },
    # 结果阶段
    "OUTPUT_CONTRACT_INVALID": {
        "phase": "result",
        "meaning": "结果不符合输出 schema",
        "recovery": "不部分提交，修复工作流/能力包后新 run"
    },
    "RESULT_COMMIT_FAILED": {
        "phase": "result",
        "meaning": "业务结果持久化失败",
        "recovery": "同 run 幂等重放提交或按策略创建重试 run"
    },
    # 并发阶段
    "BINDING_REVISION_CONFLICT": {
        "phase": "concurrency",
        "meaning": "Deck selection 被并发更新",
        "recovery": "刷新并由用户确认"
    },
    "IDEMPOTENCY_CONFLICT": {
        "phase": "concurrency",
        "meaning": "同 key 携带不同请求语义",
        "recovery": "客户端生成新 key 或恢复原请求"
    },
    "CONFIG_VERSION_DRIFT": {
        "phase": "concurrency",
        "meaning": "选择后执行前引用发生变化",
        "recovery": "使用已固定版本，或由用户显式升级后创建新 binding/run"
    }
}
```

### Step 5: 错误响应格式

```jsonc
{
  "error": {
    "code": "RUNTIME_PLUGIN_NOT_READY",
    "phase": "load",
    "message": "Required plugin is not materialized or loadable",
    "recovery_action": "Wait for or trigger reconcile; do not start session",
    "operation_id": "op_...",
    "failed_check": "runtime_plugin_ready"
  }
}
```

安全规则：
- 客户端只展示 `error_code` 对应的安全文案、失败阶段、operation/run ID 和恢复动作
- 堆栈、路径、prompt、secret、完整命令输出只进入受限日志

## 5. 涉及文件路径

| 路径 | 动作 | 说明 |
|---|---|---|
| `backend/routers/deck_plugins.py` | 新建 | 管理端 API 路由 |
| `backend/routers/voice_decks.py` | 新建/修改 | Deck 创建/编辑路由 |
| `backend/routers/story_workspace.py` | 新建/修改 | Story Workspace 执行路由 |
| `backend/services/errors/error_registry.py` | 新建 | 错误码注册表 |
| `backend/tests/test_api_routes.py` | 新建 | API 路由单元测试 |

## 6. 输入 / 输出说明

**输入**：
- HTTP 请求（各路由的 path、query、body 参数）
- 身份认证信息

**输出**：
- JSON 响应（按路由定义）
- 结构化错误响应

## 7. 依赖项

- **前置依赖**: `DECK-004`（兼容性判定）, `DECK-006`（Preflight）, `DECK-007`（Workflow Run）
- **下游依赖**: 无（API 层，消费下游服务）
- 需要与现有 auth middleware 集成

## 8. 测试策略

execute Issue 必须从仓库根核对 Python 入口及依赖环境，并逐字回填实际解释器、runner 与命令。当前仓库测试采用 `unittest` 风格，可直接复制的最小目标命令为 `PYTHONDONTWRITEBYTECODE=1 backend/.venv/bin/python -m unittest backend.tests.test_api_routes -v`，同时执行 `git diff --check`；若 `.venv` 或命令不可用，必须在 execute Issue/正式报告记录通过 `backend/pyproject.toml`、现有 `backend/tests/test_*.py` 和既有 exec 报告发现 runner 的过程、失败输出及等价解释器命令，不得新增测试框架或伪报通过。

| 测试类型 | 覆盖内容 |
|---|---|
| 单元测试 | 管理端 API 路由（所有 endpoint） |
| 单元测试 | Deck 创建/编辑 API 路由 |
| 单元测试 | Story Workspace 执行 API 路由 |
| 单元测试 | 25+ 错误码响应格式 |
| 单元测试 | 安装响应包含 operation_id、capability_diff、runtime_readiness |
| 单元测试 | 创建运行响应中来源字段由服务端复制 |
| 单元测试 | 错误响应安全（不包含堆栈/prompt/secret） |
| 集成测试 | 端到端 API 调用 |

## 9. 完成标志

- [ ] 管理端 API 路由完整，覆盖设计稿 §14.1
- [ ] Deck 创建/编辑 API 路由完整，覆盖设计稿 §14.2
- [ ] Story workspace 执行 API 路由完整，覆盖设计稿 §14.3
- [ ] 25+ 规范错误码定义完整，覆盖设计稿 §12.1
- [ ] 每个错误码包含含义和恢复动作
- [ ] 客户端只展示安全文案，堆栈/路径/prompt/secret 只进入受限日志
- [ ] 安装响应包含 `operation_id`、`capability_diff`、`runtime_readiness`
- [ ] 创建运行响应中来源字段由服务端复制，客户端不得直接提交覆盖
- [ ] 单元测试覆盖所有 API 路由和错误码响应
- [ ] 三组逻辑 router 保持 DECK-016 三域单写与无状态 gateway 边界，不引入第三业务服务或共享表双写
- [ ] 实际变更只位于 §5 五个实现/测试路径及本 task 唯一正式报告路径
- [ ] execute Issue/正式报告逐项回填验证命令、结果、验收、diff 与回滚说明

## 10. 风险提示

| 风险 | 等级 | 缓解 |
|---|---|---|
| 物理服务拆分后路由变更 | 低 | DECK-016 已冻结三域单写与无状态 gateway；逻辑路由稳定，物理拆分只替换 transport/deployment adapter |
| 错误码遗漏导致客户端无法处理 | 中 | 完整注册表；测试覆盖所有已知错误场景 |
| 敏感信息泄露到错误响应 | 高 | 自动化脱敏；代码审查 |
| API 版本演进导致兼容性破坏 | 中 | 路由版本化（`/api/v1/...`） |

## 11. 允许修改范围与禁止修改范围

### 允许修改范围

- `backend/routers/deck_plugins.py`（仅新增本 task 的管理端逻辑路由）
- `backend/routers/voice_decks.py`（仅新增/修改 Deck plugin options / binding / validate 路由）
- `backend/routers/story_workspace.py`（仅新增/修改 workflow preflight / run / retry / cancel 路由）
- `backend/services/errors/error_registry.py`（仅新增规范错误码、含义与恢复动作）
- `backend/tests/test_api_routes.py`（仅新增本 task 的 API / 错误响应测试）
- `docs/exec/exec_deck_014_backend_api-error-codes.md`（仅允许 `ExecTaskAgent` 写入本 task 的唯一正式执行报告）

以上六个路径构成未来 execute 完整闭集；前五个与 §5“涉及文件路径”一致，最后一个仅为正式报告例外。未列出的文件默认不授权。

### 禁止修改范围

- `docs/exec/` 下除 `docs/exec/exec_deck_014_backend_api-error-codes.md` 之外的全部路径
- `docs/design/`、`docs/issue/`、`docs/task/`、`docs/stage/`
- `frontend/`、gateway/物理服务部署配置与底层业务服务实现
- 除上述 5 个路径以外的任何实现、测试、依赖锁或部署配置
- 三个允许 router 中与 Deck Plugin、Workflow Preflight/Run 无关的既有路由或认证行为
- 在响应中泄露堆栈、路径、prompt、secret，或借本 task 改变服务层业务合同和来源不可变规则
- 新增第三业务服务、gateway 权威状态、跨域共享表双写，或修改 transport/deployment 配置

### 当前修订阶段约束

[SUO-324](/SUO/issues/SUO-324) 只修订 task 合同，不授权执行上述闭集。未来 execute 必须由 `ExecTaskAgent` 在独立 Issue checkout 后实施；完成后由 StagePlanner 独立重跑 readiness，不得由本 task 自行宣布进入 execute 或通过 Stage 4 Gate。

## 12. 命名隔离声明

- API 路由使用 RESTful 命名
- 错误码使用 `SNAKE_CASE`，按阶段分组

## 13. 决策状态与物理边界

- `DECK-016 / DECK-GATE-DEC-016`：`frozen`。Deck control plane 权威写 release/installation/binding/lock/snapshot；ClaudeAgent runtime control 权威写 materialization/node/session/load receipt；story-workspace 权威写 preflight/run/result/review；API gateway/BFF 只聚合和路由。
- Stage 2 服务边界设计 Gate 已通过。当前可同进程/同集群部署，不要求本 task 做物理拆分；未来物理拆分只能替换 gateway/transport/deployment adapter，不得改变逻辑资源、领域前缀、单写 owner 或错误语义。
- 本 task 只实现 §5 router adapter 与错误注册表。若 execute Issue 发现需要修改 gateway、服务部署、共享数据库访问或底层业务服务，必须停止并创建具名 owner 的独立 follow-up，不得把“已冻结”误解为越界授权。

## 14. 回滚边界

- 只回退 §11 允许的三个 router 中本 task 路由区段、错误注册表和目标测试；不得改动同文件其他既有路由、认证或业务行为。
- 回滚必须保持三域单写、逻辑错误语义和来源不可变规则；不得以 gateway 持有权威状态、共享表双写或泄露内部异常作为临时回退。
- 若下游服务合同不可用，对应路由返回已注册的安全不可用错误，不伪造成功、不部分提交，也不删除既有业务/审计数据。
- 回滚前后执行 §8 的目标测试和 `git diff --check`，并在 `docs/exec/exec_deck_014_backend_api-error-codes.md` 记录触发条件、变更路径、验证结果与剩余影响；正式报告本身不得在代码回滚中删除。

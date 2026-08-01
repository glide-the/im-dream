# task_deck_013_backend_events-audit

> **Task ID**: `task_deck_013_backend_events-audit`
> **Readiness 修订 Issue**: [SUO-324](/SUO/issues/SUO-324)
> **Domain**: `backend`（仅用于分类，不代表执行 Agent 身份）
> **状态**: `pending_stage_recheck`
> **唯一执行责任人**: `ExecTaskAgent`
> **Stage 映射**: Stage 4 / Wave 1（独立 execute Issue、独立 checkout、独立验收）

## 1. 任务标题

统一事件合同与审计

## 2. 关联 Issue

- **Issue ID**: `DECK-013`
- **Issue 标题**: 统一事件合同与审计
- **类型**: backend
- **优先级**: P1
- **标签**: `events`, `audit`, `observability`
- **来源设计稿**:
  - `docs/design/deck-plugin-voice-ink-dream-integration.md` §15.1, §15.2
- **Issue 清单**: `docs/issue/ISSUES_deck-plugin-voice-ink-dream-integration.md` §3 DECK-013
- **Readiness 修订**: [SUO-324](/SUO/issues/SUO-324)

## 3. 任务目标

实现统一的事件 envelope 和规范事件类型。事件至少一次投递，消费者按 `event_id` 去重，按 `aggregate_version` 处理顺序。事件禁止携带 prompt、secret 或完整 settings。

未来实现仅由 `ExecTaskAgent` 在本 task 的独立 execute Issue 中执行；`backend` 仅是 domain。本 task 不与其他 Stage 3/4 task 合并 checkout 或共享正式报告。

## 4. 实现步骤

### Step 1: 定义事件 Envelope 模型

在 `backend/models/events.py`（新建）中定义：

```python
class EventEnvelope(BaseModel):
    event_id: str                   # evt_<uuid>
    event_type: str                 # 规范事件类型
    event_version: int              # 事件 schema 版本
    occurred_at: datetime
    workspace_id: str
    aggregate_id: str               # 关联的聚合根 ID
    aggregate_version: int          # 聚合版本（单调递增）
    correlation_id: str             # 操作或 run ID
    causation_id: Optional[str]     # 上一个事件 ID
    payload: dict                   # 事件负载（脱敏）
```

### Step 2: 定义规范事件类型

| 事件类型 | 最小 Payload | 产生时机 |
|---|---|---|
| `deck_plugin.release.published` | plugin id/version、manifest hash、runtime lock id | release 发布完成 |
| `deck_plugin.installation.status_changed` | installation id、old/new status、error code | installation 状态变化 |
| `runtime_plugin.materialization.status_changed` | materialization id、plugin id/version、declared/materialized 状态 | 物化状态变化 |
| `deck.plugin_binding.changed` | deck id、old/new exact release、binding revision、actor | Deck binding 保存 |
| `workflow.preflight.status_changed` | preflight id、status、failed check/error code、expires at | preflight 状态变化 |
| `workflow.run.created` | run id、来源字段、runtime lock/load receipt refs | run 创建 |
| `workflow.run.status_changed` | run id、old/new status、failed step/error code | run 状态变化 |
| `workflow.run.step_progressed` | run id、step id、progress、safe summary | 步骤进度更新 |
| `workflow.result.persisted` | run id、result refs/schema version | 结果持久化 |
| `workflow.run.security_cancelled` | run id、revocation policy/ref、safe reason | 安全撤销取消 |

### Step 3: 实现事件发射器

在 `backend/services/events/event_emitter.py`（新建）中实现：

```python
class EventEmitter:
    async def emit(self, envelope: EventEnvelope) -> None:
        """
        发射事件：
        1. 持久化到数据库（权威来源）
        2. 投递到消息队列（至少一次）
        3. 前端 SSE/WebSocket 推送（脱敏投影）
        """

    def build_envelope(
        self,
        event_type: str,
        aggregate_id: str,
        payload: dict,
        correlation_id: str,
        causation_id: Optional[str] = None
    ) -> EventEnvelope:
        """构建事件 envelope，自动分配 event_id 和 aggregate_version。"""
```

### Step 4: 实现事件去重与顺序保证

```python
class EventConsumer:
    async def consume(self, envelope: EventEnvelope) -> None:
        """
        消费事件：
        1. 按 event_id 去重（幂等）
        2. 按 aggregate_version 保证同 aggregate 内顺序
        3. 乱序事件暂存，等待前置版本到达
        4. 超时未到达的前置版本触发告警
        """
```

### Step 5: 脱敏规则

事件负载禁止包含：
- prompt 文本（完整或部分）
- secret 值或解密后的配置
- 完整 settings.json 内容
- 用户敏感信息（邮箱、密码等）

允许包含：
- ID 引用（`deck_runtime_snapshot_id` 而非内容）
- 状态摘要（`load_status: loaded` 而非详细日志）
- 非敏感元数据（版本号、时间戳、actor ID）

### Step 6: 数据库表设计

在 `backend/database.py` 中追加：

```sql
CREATE TABLE IF NOT EXISTS events (
    event_id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    event_version INTEGER NOT NULL,
    occurred_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    workspace_id TEXT NOT NULL,
    aggregate_id TEXT NOT NULL,
    aggregate_version INTEGER NOT NULL,
    correlation_id TEXT NOT NULL,
    causation_id TEXT,
    payload_json TEXT NOT NULL,
    UNIQUE(aggregate_id, aggregate_version)
);

CREATE INDEX IF NOT EXISTS idx_events_aggregate
    ON events(aggregate_id, aggregate_version);
CREATE INDEX IF NOT EXISTS idx_events_type
    ON events(event_type, occurred_at);
CREATE INDEX IF NOT EXISTS idx_events_correlation
    ON events(correlation_id);
```

## 5. 涉及文件路径

| 路径 | 动作 | 说明 |
|---|---|---|
| `backend/models/events.py` | 新建 | 事件模型 |
| `backend/services/events/event_emitter.py` | 新建 | 事件发射器 |
| `backend/services/events/event_consumer.py` | 新建 | 事件消费者 |
| `backend/database.py` | 修改 | 追加 `events` 表 |
| `backend/tests/test_events.py` | 新建 | 事件系统单元测试 |

## 6. 输入 / 输出说明

**输入**：
- 各服务的状态变化（release published、installation changed、run status changed 等）
- Actor 信息（谁触发了变化）

**输出**：
- 持久化的事件记录
- SSE/WebSocket 推送（脱敏）
- 审计日志

## 7. 依赖项

- **前置依赖**: `DECK-007`（Workflow Run）, `DECK-009`（Run-Scoped Session）
- **下游依赖**: 无（基础设施，被其他服务消费）
- 需要与现有事件基础设施集成（若有）

## 8. 测试策略

execute Issue 必须从仓库根核对 Python 入口及依赖环境，并逐字回填实际解释器、runner 与命令。当前仓库测试采用 `unittest` 风格，可直接复制的最小目标命令为 `PYTHONDONTWRITEBYTECODE=1 backend/.venv/bin/python -m unittest backend.tests.test_events -v`，同时执行 `git diff --check`；若 `.venv` 或命令不可用，必须在 execute Issue/正式报告记录通过 `backend/pyproject.toml`、现有 `backend/tests/test_*.py` 和既有 exec 报告发现 runner 的过程、失败输出及等价解释器命令，不得新增测试框架或伪报通过。

| 测试类型 | 覆盖内容 |
|---|---|
| 单元测试 | 事件 envelope 构建（所有字段正确填充） |
| 单元测试 | 10 类规范事件生成 |
| 单元测试 | 事件去重（同一 event_id 多次消费只处理一次） |
| 单元测试 | 顺序保证（aggregate_version 单调递增） |
| 单元测试 | 脱敏校验（payload 不包含 prompt/secret/settings） |
| 单元测试 | 乱序处理（版本 2 先于版本 1 到达时的暂存与重排） |
| 集成测试 | 端到端事件流（发射 → 持久化 → 消费） |

## 9. 完成标志

- [ ] 统一事件 envelope 结构完整
- [ ] 10 类规范事件覆盖设计稿 §15.2 所有事件类型
- [ ] 事件至少一次投递，消费者可按 `event_id` 去重
- [ ] 同 aggregate 的 `aggregate_version` 单调递增
- [ ] 事件禁止携带 prompt、secret 或完整 settings
- [ ] 前端 SSE/WebSocket 可消费脱敏投影
- [ ] 数据库审计事件是权威来源
- [ ] 单元测试覆盖事件生成、投递、去重、顺序
- [ ] 实际变更只位于 §5 五个实现/测试路径及本 task 唯一正式报告路径
- [ ] execute Issue/正式报告逐项回填验证命令、结果、验收、diff 与回滚说明

## 10. 风险提示

| 风险 | 等级 | 缓解 |
|---|---|---|
| 事件丢失导致审计不完整 | 高 | 数据库持久化为权威来源；消息队列为异步投递 |
| 事件顺序错乱导致状态不一致 | 中 | aggregate_version 唯一约束；乱序暂存机制 |
| 敏感信息泄露到事件负载 | 高 | 脱敏规则自动化检查；代码审查 |
| 事件表无限增长 | 中 | `DECK-017` 仍为 `conditional_frozen`；production 留存/恢复 owner 与证据未批准前不得自行引入 purge，开发/测试只做显式限域策略 |

## 11. 允许修改范围与禁止修改范围

### 允许修改范围

- `backend/models/events.py`（仅新增统一事件 envelope 与规范事件模型）
- `backend/services/events/event_emitter.py`（仅新增事件发射与持久化衔接）
- `backend/services/events/event_consumer.py`（仅新增去重与 aggregate 顺序处理）
- `backend/database.py`（仅增量追加 `events` 表及其幂等初始化）
- `backend/tests/test_events.py`（仅新增本 task 的单元测试）
- `docs/exec/exec_deck_013_backend_events-audit.md`（仅允许 `ExecTaskAgent` 写入本 task 的唯一正式执行报告）

以上六个路径构成未来 execute 完整闭集；前五个与 §5“涉及文件路径”一致，最后一个仅为正式报告例外。未列出的文件默认不授权。

### 禁止修改范围

- `docs/exec/` 下除 `docs/exec/exec_deck_013_backend_events-audit.md` 之外的全部路径
- `docs/design/`、`docs/issue/`、`docs/task/`、`docs/stage/`
- `frontend/`、消息中间件基础设施和其他业务域事件生产者/消费者实现
- 除上述 5 个路径以外的任何实现、测试、依赖锁或部署配置
- `backend/database.py` 中与 `events` 表无关的既有表或初始化逻辑
- 在事件 payload 写入 prompt、secret、完整 settings，或借本 task 改写 Workflow Run / Session 业务状态机

### 当前修订阶段约束

[SUO-324](/SUO/issues/SUO-324) 只修订 task 合同，不授权执行上述闭集。未来 execute 必须由 `ExecTaskAgent` 在独立 Issue checkout 后实施；完成后由 StagePlanner 独立重跑 readiness，不得由本 task 自行宣布进入 execute 或通过 Stage 4 Gate。

## 12. 命名隔离声明

- 事件类型使用点分命名空间（`deck_plugin.release.published`）
- 聚合 ID 根据聚合根类型区分（release ID、installation ID、run ID）

## 13. 决策状态与剩余边界

- `DECK-017 / DECK-GATE-DEC-017`：`conditional_frozen`。生产制品采用 SHA-256、受信签名包与引用感知留存，但安全、marketplace/制品平台、runtime owner 的具名审批与恢复证据仍未完成；本 task 不得据此宣告 production-ready。
- 事件审计记录必须 append-only 并保留稳定引用；具体 production 保留期、归档介质和 purge 调度不在本闭集内。若 execute Issue 需要新增这些路径或策略，停止并创建具名 owner 的独立 follow-up，不得越界实现。

## 14. 回滚边界

- 只回退 §11 允许的事件模型、发射/消费实现、测试，以及 `backend/database.py` 中与 `events` 表初始化直接相关的最小代码区段。
- 已持久化的事件和审计来源不得在回滚中删除、改写或降级为可变日志；数据库兼容回滚优先停止新写入/消费并保留既有表为只读审计证据。
- 回滚不得改写 Workflow Run、Session 或其他业务状态机；跨 task 生产者/消费者由各自执行合同处置。
- 回滚前后执行 §8 的目标测试和 `git diff --check`，并在 `docs/exec/exec_deck_013_backend_events-audit.md` 记录触发条件、变更路径、数据保留、验证结果与剩余影响；正式报告本身不得在代码回滚中删除。

<!--
[Input] Existing Claude Agent admission/Observer/EventBus contracts plus Admin-owned observer and Claude Code Runtime capabilities.
[Output] Record Dream-side resource observation, desired/effective synchronization, and omit-when-unset Runtime projection.
[Pos] Local implementation task record; Admin owns schema/UI and Dream owns content-free observation/publication.
[Sync] 2026-08-28: add revisioned global effort and selected-model compact/context Runtime env; failures retain both LKGs.
-->

# Claude Agent Resource Observer — Dream PostgreSQL 实现记录

## 边界

本任务只实现 Dream 本地代码与 provider-free 自动化测试：

- 不修改 ThreadPool、EventBus、路由状态机或 admission 决策算法；service/ThreadFactory/Runner 只透传和验证 immutable server-owned Runtime env，不改变 turn/resume/cancel/SSE 语义。
- 不新增 Dream diagnostics HTTP/Bearer，不修改 AutoDL/deploy 投影。
- 不创建 migration、DDL、SQLite fallback 或 runtime schema repair。
- Admin Drizzle 唯一拥有 `system_settings`、`claude_agent_resource_snapshots` 与 capability 发布。

## 运行结构

```text
existing Agent turn
  -> existing admission controller
  -> transparent admission decorator -> content-free counters
  -> existing Observer registry / normalized EventBus -> terminal counters

Linux /proc + cgroup sampler
  -> strict closed DTO
  -> 5-second publisher
  -> capacity-1 latest queue
  -> single timeout-isolated PostgreSQL worker
  -> capability check + upsert + 7-day stale-instance cleanup

periodic PostgreSQL desired-policy refresher
  -> strict observer/Runtime capability + schema/bounds/effort validation
  -> monotonic revision guard
  -> composition-owned admission + global effort replacement
  -> read-only diagnostics immutable state commit
  -> future admission acquire only (existing leases remain active)

authenticated Admin Gateway model catalog
  -> final callable GatewayModel selection
  -> nullable compact/context Runtime projection
  -> merge with global effort snapshot at service boundary
  -> exact three-key runner validation/injection
```

Observer hook 只做计数、校验和 `asyncio.create_task` handoff；订阅/读取/unsubscribe 在独立 task 中执行。异常被隔离，且内存中不保存 Thread、Session、actor、正文或 event payload。

## Desired policy

composition root 构造时通过公开 provider 首次读取，随后由独立 task 周期读取：

1. 同时精确验证 observer capability 与 `dream.claude-code-runtime-config.v1`；任一缺失或 hash 漂移均 fail closed。
2. 读取 `system_settings(category='claude_agent', key='resource_policy')`。
3. 严格接受且只接受：

```json
{
  "schemaVersion": 1,
  "revision": 1,
  "maxConcurrentRuns": 1,
  "runMemoryBudgetMib": 512,
  "memoryReserveMib": 128,
  "retryAfterSeconds": 60,
  "claudeCodeEffortLevel": "high"
}
```

`claudeCodeEffortLevel` 也可为 null；合法非空值仅为 `low/medium/high/xhigh/max`。null 不会写入默认值，而是保证 `CLAUDE_CODE_EFFORT_LEVEL` 在最终子进程环境中不存在。

边界与 Admin 一致：`maxConcurrentRuns`、`runMemoryBudgetMib`、`memoryReserveMib`、`retryAfterSeconds` 均为 `1..9_007_199_254_740_991` 的正安全整数；`runMemoryBudgetMib + memoryReserveMib <= 8_589_934_591`，保证乘以 `1_048_576` 后仍可由 JSON/TypeScript 精确表达。这些是技术边界，不是产品配额；旧 `16/128/8192/64/4096/5/3600` 不再构成 min/max。null、0、布尔、字符串、小数、负数、非安全整数、partial/unknown object 与任何无限/关闭 sentinel 均为 `invalid`。缺行或数据库/capability 不可用分别记录 `not_configured`、`unavailable`。首次启动无 valid desired 时使用通过同一合同的 env/default fallback；运行期失败保留 last-known-good effective config、revision 与 `updated_at`，只推进 status 与本次 `loaded_at`。

refresher 默认每 5 秒执行一次，`INK_AGENT_RESOURCE_POLICY_REFRESH_INTERVAL_S` 只控制本进程的 `1..300` 秒轮询间隔，不是 Admin setting。只有更高且合法的 revision 请求公开 replace 并在回调成功后推进 LKG；回滚或同 revision 异值记录 `invalid` 并保留 LKG。同 revision 同值不重复 replace，但允许刷新 diagnostics 的 `status/loaded_at` 并从失败状态恢复为 `applied`。有效降并发不取消现有 lease，只约束后续 acquire。

配置应用只发生在 composition callback：valid higher revision 通过 admission 公开 replacement（四项相同时跳过实际 controller 写入）并更新公开 Runtime store，再把同一 policy/effective pair 提交给 read-only diagnostics。effort-only revision 仍推进 Runtime LKG 与 effective revision。两步之间 diagnostics 继续报告完整旧 state，不会拼接 new config 与 old revision；后台 provider/callback 异常由 refresher task 隔离，不进入 Agent turn。

模型级 `CLAUDE_CODE_AUTO_COMPACT_WINDOW` 与 `CLAUDE_CODE_MAX_CONTEXT_TOKENS` 由 Admin `/v1/models` catalog 的最终 `GatewayModel` 提供，只接受 int4 正整数。Dream 不在 turn path 查询 PostgreSQL 模型表。service 将模型 snapshot 与全局 effort snapshot 合并到 `AgentRunOptions.server_runtime_env`；runner 在 user env 之后按精确三键白名单验证并覆盖。composition 启动时先清除父进程同名变量，因此未配置字段在 SDK 继承环境和 options overlay 中都不存在。

## Snapshot contract

数据库行保存随机进程 UUID `instance_id`、`process_started_at`、`heartbeat_at`、`sampled_at`；UUID 不含 hostname、PID 或业务 ID。JSON 不重复这些列，只包含：

- `schema_version=1`、`backend_status=ok`、process/process-lifetime scope。
- defaults/effective/global effort/effective version/load time/policy status/revision/update time。
- turn/admission content-free counters与 `can_start_new_agent: true|false|null`。
- Claude descendant count/RSS。
- host available、cgroup current/max/raw、inactive file、reclaimable slab、effective/required 和 `memory.events`。
- sample status/time/stale/closed error code。
- queue dropped、write errors、last write error time。

严禁 JSON 包含 Thread/Session/user/actor ID、消息、prompt、transcript、文件内容、Token、Cookie、Authorization、DSN、hostname、PID、完整 env 或 argv。样本 starting/timeout/error/stale 时 `can_start_new_agent=null`；fresh unavailable 保留既有 concurrency-only 语义。

## PostgreSQL sink

- publisher 使用 `put_nowait`；队列满时以新值替换旧值并增加 drop counter，不反压 Observer/turn。
- 单 worker 使用 `asyncio.to_thread`，外层 timeout 与事务内 `statement_timeout`。
- 每次事务先验证精确 capability，再 `INSERT ... ON CONFLICT(instance_id) DO UPDATE`，随后清理 heartbeat 超过 7 天的其他实例。
- 写入失败只增加安全计数并记录固定错误码，不记录异常文本、连接信息或 payload。
- server 在 `startup_database` 之后启动 sampler/refresher/sink/publisher；shutdown 时按 publisher → refresher → sink → sampler → factory → database 顺序隔离停止。

## 本地验证

Focused suites 覆盖四项越过旧上限、safe integer 与组合内存边界/+1、env/desired/replace/DTO 一致性、Observer/admission/lease、live 降配、cancel/SSE、cgroup/proc、missing/timeout/stale、strict provider、bounded interval、same revision no-replace、revision 单调/new snapshot/last-known-good、后台异常隔离、latest queue、慢 DB/timeout、upsert/TTL/privacy，以及 server startup/shutdown 顺序。没有连接真实业务数据库、没有运行 migration、没有部署或远端验证。

## 任务账本（2026-08-28）

| 字段 | 回执 |
|---|---|
| 原始需求摘要 | 在既有动态资源策略上增加全局 effort 与选中模型 compact/context Runtime 配置；未设置不注入；invalid/unavailable 保留 LKG；不改变 Agent 核心语义。 |
| 负责人 | Dream Codex task |
| 仓库 / 目录 | `/Users/dmeck/project/ink-dream-memory`；生产修改在 provider/composition、Gateway model selection、service/options env projection 与 effective diagnostics。 |
| 文件所有权 | Dream provider/composition root、Gateway catalog consumer、精确 Runtime env 边界、effective snapshot、focused tests/docs；不拥有 Admin schema/migration，且不改变 admission/Agent 状态机/SSE。 |
| 当前状态 | complete；本地 focused、composition、Runner/ThreadFactory/admission、resume/cancel/SSE 与 schema capability 回归通过；未提交、未部署、未推送。 |
| 阻断项 | 无。 |

实际验证回执：

- `PYTHONPATH=backend .venv/bin/python -m pytest -q backend/tests/test_sdk_env.py backend/tests/test_admin_gateway_models.py backend/tests/test_admin_gateway_model_selection.py backend/tests/test_claude_agent_resource_policy.py backend/tests/test_claude_agent_resource_diagnostics.py backend/tests/test_claude_agent_service.py`：exit `0`，`90 passed, 23 subtests passed`。
- `PYTHONPATH=backend .venv/bin/python -m pytest -q backend/tests/test_claude_agent_service.py backend/tests/test_server_claude_agent.py`：exit `0`，`101 passed, 7 subtests passed`。
- `PYTHONPATH=backend .venv/bin/python -m pytest -q backend/tests/test_schema_capabilities.py backend/tests/test_server_claude_agent.py backend/tests/test_claude_agent_runner.py backend/tests/test_claude_agent_thread_factory.py backend/tests/test_claude_agent_admission.py backend/tests/test_claude_agent_resource_observer.py backend/tests/test_claude_agent_resource_postgres_sink.py`：exit `0`，`303 passed, 1 skipped, 138 subtests passed`；另有 `25` 条仓库既有 FastAPI `on_event` deprecation warnings。
- `PYTHONPATH=backend .venv/bin/python -m py_compile backend/agent_factory.py backend/claude_agent/resource_policy.py backend/claude_agent/resource_diagnostics.py backend/claude_agent/service.py backend/claude_agent/thread_factory.py backend/libs/claude_agent_kit/server/agent_runner.py backend/libs/claude_agent_kit/server/sdk_env.py backend/libs/claude_agent_kit/types.py backend/routers/claude_agent.py backend/services/admin_gateway/models.py backend/services/admin_gateway/selection.py`：exit `0`。
- Dream 仓库没有配置独立 Python lint/typecheck 命令；以上 `py_compile`、focused 与 303 项 Agent 回归作为当前本地静态/语义门禁。

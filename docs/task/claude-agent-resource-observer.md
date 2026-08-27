<!--
[Input] Existing Claude Agent admission/Observer/EventBus contracts and Admin-owned PostgreSQL capability `dream.claude-agent-resource-observer.v1`.
[Output] Record the implemented Dream-side PostgreSQL-only resource observation and desired/effective synchronization boundary.
[Pos] Local implementation task record; Admin owns schema/UI and Dream owns content-free observation/publication.
[Sync] 2026-08-27: finalize DB-clock publication, bounded fallback, serialized timeout recovery, and canonical capability hash.
-->

# Claude Agent Resource Observer — Dream PostgreSQL 实现记录

## 边界

本任务只实现 Dream 本地代码与 provider-free 自动化测试：

- 不修改 `service.py`、Runner、ThreadFactory、ThreadPool、EventBus、路由状态机或 admission 决策算法。
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
```

Observer hook 只做计数、校验和 `asyncio.create_task` handoff；订阅/读取/unsubscribe 在独立 task 中执行。异常被隔离，且内存中不保存 Thread、Session、actor、正文或 event payload。

## Desired policy

composition root 构造时通过公开 provider 读取一次：

1. 精确验证 capability `dream.claude-agent-resource-observer.v1`、version `1`、contract SHA-256 `db2ba80eb61a9515ba23000f8a615fb41f6ed5824bd306e8d0ca5fb8f1cc044e`。
2. 读取 `system_settings(category='claude_agent', key='resource_policy')`。
3. 严格接受且只接受：

```json
{
  "schemaVersion": 1,
  "revision": 1,
  "maxConcurrentRuns": 1,
  "runMemoryBudgetMib": 512,
  "memoryReserveMib": 128,
  "retryAfterSeconds": 60
}
```

边界与 Admin 一致：并发 `1..16`，run memory `128..8192 MiB`，reserve `64..4096 MiB`，retry `5..3600 s`。valid 状态为 `applied`；缺行、无效或数据库/capability 不可用分别记录 `not_configured`、`invalid`、`unavailable`，并保留已由既有 `AgentAdmissionConfig.from_env()` 验证的有限 fallback。运行中不热替换 controller config。

## Snapshot contract

数据库行保存随机进程 UUID `instance_id`、`process_started_at`、`heartbeat_at`、`sampled_at`；UUID 不含 hostname、PID 或业务 ID。JSON 不重复这些列，只包含：

- `schema_version=1`、`backend_status=ok`、process/process-lifetime scope。
- defaults/effective/effective version/load time/policy status/revision/update time。
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
- server 在 `startup_database` 之后启动 sampler/sink/publisher；shutdown 时按 publisher → sink → sampler → factory → database 顺序隔离停止。

## 本地验证

Focused suites 覆盖 Observer/admission/lease、cgroup/proc、missing/timeout/stale、strict provider、latest queue、慢 DB/timeout、upsert/TTL/privacy，以及 server startup/shutdown 顺序。没有连接真实业务数据库、没有运行 migration、没有部署或远端验证。

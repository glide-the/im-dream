<!-- [Input] Verified Reflections Registry83 provider, Dream request consumer commits and remaining background database call graph. -->
<!-- [Output] Prompt-architect execution plan for moving Reflections task/result/event persistence to Admin business APIs. -->
<!-- [Pos] Cross-project background Reflections persistence stage; Dream retains Agent execution, EventBus, SSE and shared files. -->
<!-- [Sync] 2026-09-15: freeze sixteen-operation candidate including recoverable task-section child authority. -->

# Reflections 后台任务数据聚合阶段

## Optimized Prompt

You are the Admin and Dream cross-project owner for closing the remaining production PostgreSQL access in the Reflections background workflow. Existing evidence proves Admin Registry83 provides strict `reflections-section-config.get/save/delete` through Zod DTO → Service → typed Drizzle Repository, and Dream commits `1ccb80d4`/`9f00f777` moved request-bound config access to a strict Pydantic client with original-request receipt recovery. The remaining `reflections_agent.py` and Reflections task routes still read or persist Sessions, task status, events, results, reports and background section configuration through Dream database helpers.

Read the complete Dream `backend/reflections_agent.py`, `backend/routers/reflections.py`, every referenced `backend/database.py` helper and test, plus Admin Reflections/Session/receipt/delegation repositories, Drizzle schema and published operation artifacts. Produce a function-level migration inventory with exact current transaction, locking, ordering, UTC timestamp, owner and failure semantics before modifying code. Define the smallest closed Admin business operations that preserve each original atomic boundary; do not expose SQL, table/column selectors, arbitrary user IDs or generic CRUD, and do not split one original transaction into unsafe HTTP writes.

Admin owns all SQL, ORM, transactions, owner filtering, task/result/event/report persistence and any necessary original-request receipts. Every implementation must follow strict Zod DTO → Service → typed Drizzle Repository → Drizzle transaction. Dream owns section selection, prompt/default merging, Agent Runtime, background scheduling, EventBus, SSE projection, result rendering and shared filesystem writes. Prefer an immutable, server-produced launch snapshot for data needed by the worker. If later worker persistence needs authority, reuse an existing precisely bound delegation only when its entity scope matches; otherwise define one explicit task-bound mechanism with expiry and revocation rather than retaining browser credentials, PostgreSQL credentials or a generic service bypass.

Preserve create/load/continue/cancel semantics, event sequence and cursor behavior, task/result/report ordering, timestamps, error states, repeated calls and concurrent worker updates. Admin unavailability must become an explicit business failure and must never trigger Dream PostgreSQL fallback. Keep `sessions_tool.py` and unrelated MCP/background contexts outside this stage unless their exact call graph is part of the same transaction. Do not change Runner, ThreadFactory, Claude service, turn/resume/cancel, resource-policy LKG/admission/lease, shared filesystem, `CLAUDE_CODE_TMPDIR`, `0700`, symlink or sandbox behavior.

Implement Admin contracts and provider first, publish exact capability hashes without changing prior descriptors, then implement one reusable Dream Pydantic adapter and replace every verified Reflections background production callsite. Retire or fail-before-I/O each old helper only after its callers are closed. Update headers, folder contracts, architecture/API inventories and this stage record. Validate strict inputs and outputs, owner/scope denial, missing/corrupt data, status transitions, same-request replay, concurrency, rollback at each write point, final-COMMIT response loss, Admin timeout and no-PG fallback. Use a named verified disposable PostgreSQL only for migration/transaction/fault tests; deterministic tests go to Luna. Refresh the AST inventory and prove both source closure and runtime behavior. Separately report unexecuted normal Dream/Admin/PostgreSQL/Google/model acceptance.

## 本阶段已有证据、责任与依赖

| 项目/责任 | 已有证据 | 本阶段依赖与产出 |
| --- | --- | --- |
| Admin provider | Registry83 public48、atomic2568、125表保持；Session provider29/29 | 读取真实 helper 后定义 task/result/event/report 闭合 DTO、ORM Repository 与事务 |
| Dream consumer | 配置请求入口提交 `1ccb80d4`，回执恢复 `9f00f777`；35 tests | 背景 worker 和路由改用统一 Admin client，不传浏览器 token，不保留 PG fallback |
| 跨项目协调 | 当前 AST 为52 SQL模块、39数据库/driver导入模块、95旧helper调用 | 更新机器清单、阶段状态、测试回执与真实验收缺口 |

## 保持不变与验收门槛

- Dream 继续执行 Agent、调度、EventBus、SSE、section 算法及共享文件操作。
- Admin 接口只表达实际业务操作；权限从认证主体或精确委托推导，不接受外部用户 ID。
- 所有写入明确事务、幂等与未知提交恢复；非幂等写入不盲目重试。
- 代码、DTO、文档、时序和测试必须采用同一方案；旧数据库 helper 的关闭同时需要调用清单和运行证据。
- 正常账户、Google、真实模型及日常 Admin 可见性未验证前，不宣称本阶段或整体任务完成。

## 代码前评审结论

完整调用链除 `reflections_agent.py` 与 Reflections task 路由外，还确认 `routers/reports.py` 的 GET/POST 公开 report 入口。候选接口为16个闭合操作：OAuth `reflection-task.create/start/get/latest/events` 与 `analysis-report.list/save`；后台 `reflection-task.worker-load/advance`、`reflection-section.begin/authority-renew/authority-revoke/transcript/finish`、`reflection-event.append`、`reflection-report.ensure`。`start` 是显式 owner/service 绑定和历史 task adoption，不在 GET 中写入或直接执行 Agent。`analysis-report.save` 保留普通页面保存，不能设置 task link；task report 仍由 `reflection-report.ensure` exactly-once 创建。bulk import 中的 report 写入保留为独立迁移缺口。

后台调用使用配置闭集中的 `reflections:execute` service scope。OAuth create/start 把 canonical owner 和当前 Dream service 固化到 task；后台只提交 task ID 与闭合业务 DTO，Admin 从 task 行推导 owner。task ID 仅是查找键。后台 write receipt 必须以 task scope 绑定，原回执查询重复验证当前 service 与 task；不得仅使用 service-wide receipt subject。

最小 forward expand 候选为：`reflection_task` 增加 nullable historical service binding、内部 bounded launch snapshot 与非空 revision；新 `reflection_task_section` 绑定 section、child Thread、状态与 revision；`analysis_reports` 增 nullable task link 与 partial unique；历史 event sequence 按 `created_at,id` 确定回填后增加 `(task_id,sequence)` 唯一和新写非空约束。现有 migration 不修改，0061 候选只在具名隔离 PostgreSQL 验证；共享 Registry、handler、service config 与 receipt 接线要在独立候选 source parity 和 schema diff 可核验后进行。

launch snapshot 只保存 Admin 生成且有大小门禁的本次 Session 内容/统计和三个 section 自定义配置，不进入 OAuth task DTO、日志、receipt 或 audit 正文。Dream 继续合并静态默认并写共享 workspace。终态 task 的 `report.ensure` 必须可由显式 start/recovery 路径补偿；latest 增稳定 ID tie-break，event 保持 observer 失败隔离和未知 Last-Event-ID 全量回放。

候选评审补充三项实现 gate。第一，Admin 创建 child Thread 后必须给 Dream server owner 一个 task、section、child Thread 三重绑定且可到期/续期/撤销的 Runtime persistence authority；它覆盖该内部 Agent 的 user/assistant message、Claude Session 和所需配置读取，凭据不得进入 CLI、MCP、workspace 或日志。第二，`advance` 必须包含从 CREATED/ASSEMBLING/QUEUED/RUNNING 到 FAILED 的 `fatal-fail` CAS，使 worker-load、共享 workspace 准备或 Runtime 启动前失败可持久化并结束未完成 sections。第三，Dream 创建的共享 workspace locator 必须按双方配置的根与 task ID 进行规范化验证后写入原 `workspace_path` 元数据，不能接受任意绝对路径，也不能让公开 task DTO长期返回空值。Session tool 使用另一个阶段定义的私有 projection broker，Reflections provider只读 worker-load snapshot。

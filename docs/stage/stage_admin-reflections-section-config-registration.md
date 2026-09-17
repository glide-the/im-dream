<!-- [Input] Admin Registry83 DTO/ORM implementation, isolated public/atomic receipts and Dream request-consumer evidence. -->
<!-- [Output] Current Reflections section-config request migration, background-task dependency and remaining closure gates. -->
<!-- [Pos] Cross-project Reflections configuration stage; Dream retains defaults, Agent execution and shared filesystem writes. -->
<!-- [Sync] 2026-09-15: mark Admin provider technically verified and keep Dream consumer/background closure active. -->

# Reflections Section Config 数据接口阶段

## 背景与问题

Dream 的配置 GET/PUT/DELETE 与 memory-init 已通过统一 Pydantic 客户端消费 Admin `reflections-section-config.get/save/delete`。后台 Reflections Agent prompt 装配仍有 `database.py` section-config 依赖；后台执行不能持有浏览器 token 或回退 PostgreSQL，必须与 task/result/event 业务聚合一起关闭。

## 目标与边界

- Admin 只拥有 section-config 原始 JSON 的数据库读取、写入、事务、owner过滤、receipt 与 audit。
- Dream 继续拥有三个 section、五个允许文件名、静态默认、effective 合并、空白规则、Agent/SSE 编排和共享文件系统操作。
- Reflections task/result/event、notes 与 analysis report 需要后续独立业务聚合接口，不允许借本接口扩展通用 CRUD。
- 请求内调用使用当前用户委托；后台任务需消费服务器所有的不可变配置输入或后续受限 task 聚合，Agent turn 不临时查询策略或数据库。

## 概念与规则

`get` 输入只有 `section`，输出 `prompt_files_json: string | null`。`save` 接收 `section` 和 Dream 已按白名单过滤的原始 JSON 文本。`delete` 返回 `deleted: boolean`，缺失行是成功 no-op。调用方不能提交 user ID、路径、默认 prompt、表、列或 SQL。写操作、回执和审计在同一个 Admin UOW 内；未知提交结果先查询原 request ID，不能换 ID 盲目重试。

## Optimized Prompt

You are the cross-project Reflections section-config migration owner. Reuse the verified Admin Registry83 Zod DTO, Service, typed Drizzle Repository, public Route and original receipt recovery. Add one Dream Pydantic AdminReflectionsSectionData client through the shared Admin transport and current-user delegation. Replace request-bound section GET/PUT/DELETE and memory-init reads without changing response payloads, static defaults, effective merge or filesystem behavior. Keep background task persistence separate: use a bounded server-owned aggregate or immutable creation snapshot, never a browser credential or Dream PostgreSQL fallback. Close old helpers only after all callers move, refresh the AST inventory, update file headers/folder docs and run focused consumer, failure, no-PG and business-flow verification.

USER REQUIREMENT:
数据库改造成接口必须遵从 DTO/ORM 设计，并继续关闭 Dream 全部生产数据库访问。

## 项目、责任与状态

| 项目/责任人 | 当前状态 | 下一验收 |
| --- | --- | --- |
| Admin 任务 | Registry83 静态57、契约 hash、DTO/Service/Repository 已通过 | 保持接口冻结；不扩展通用入口 |
| Root | 隔离公开48、保持258、原子2568已通过 | 归档回执并审查 Dream consumer |
| Dream 任务 | 请求入口提交 `1ccb80d4`，原回执恢复提交 `9f00f777`；Luna 35 tests 与静态门禁通过 | 冻结请求 consumer，后续仅迁移后台聚合 |
| 后续 Reflections task 阶段 | 尚未实现 task/result/event 聚合 | 定义后台服务委托与单事务业务接口 |

## 已验证接口与失败处理

- get/save/delete v1 hashes：`2e1057f1cdd9248c2dbd603057310399e7ea5a51c90c601405ebb86868ccb640`、`dc2ba4ee442618b4fd39d75b8ddf9ca834b25913d85e4bee0cba76d20b4b047f`、`8b03792f711e79c1d12343a93980da91d7675d280f9713ab454e6369b2b45967`。
- OAuth `dream:read/write`、service/client、canonical subject、null entity scope 与 strict DTO 已从公开 Route 验证。
- 400/403/409/503 均提供明确失败；损坏原回执返回503，外部 user selector 返回400。
- INSERT/UPDATE/DELETE/receipt/audit 故障全部回滚；save/delete 最终 COMMIT 响应丢失可用原 request receipt 恢复。
- 详细命令和边界见 [Registry83 公开与原子恢复回执](../exec/admin-auth-data-verification/reflections-section-config-registry83-public-atomic.md)。

## 保持不变

Runner、ThreadFactory、service、EventBus、SSE、turn/resume/cancel、资源策略 LKG、线程 workspace、`CLAUDE_CODE_TMPDIR`、`0700`、符号链接限制和 sandbox 放行范围均不在本阶段改变。Admin 不执行 Agent Runtime 或共享文件写入。

## 剩余验收与风险

1. Dream 请求入口四处已不再调用旧配置 helper；单次写 POST、同 request/operation 回执恢复和无 PG fallback 已通过 35 tests 与静态门禁。真实浏览器/共享文件写入业务验收仍待正常服务。
2. 后台 task 的 section-config 依赖必须与 task/result/event 一起形成业务聚合；未完成前旧 DB 依赖不能宣称关闭。
3. fresh AST 清单和运行探针要共同证明已迁移入口不加载连接池、SQL 或 ORM。
4. 完成真实 Dream/Admin/PostgreSQL/Google/模型流程前，本阶段与整体 goal 保持 active；隔离数据库结果不作为真实验收。

## Dream 请求消费者回执

Dream 提交 `1ccb80d4` 将配置 GET/PUT/DELETE 与 memory-init 切到严格 Pydantic DTO；`9f00f777` 为 save/delete 增加原始 request receipt 恢复。响应丢失后只查询同一 operation 和 request ID，不发第二次写请求；absent、回执超时或无效响应都保持 `outcome_unknown`。Luna 按 README 的 frozen uv 命令实际执行 35 tests，另有 7 文件编译、AST 边界和 `git diff --check` 通过；最初无 pytest 环境与首次 uv 缓存沙箱失败均保留。详见 [Dream consumer 回执](../exec/admin-auth-data-verification/reflections-section-config-dream-consumer.md)。

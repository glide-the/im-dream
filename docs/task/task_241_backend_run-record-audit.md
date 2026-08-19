# Task: Story Workspace Episodes 运行记录与审计最小合同 API（Backend）

> **Task ID**: `task_241_backend_run-record-audit`  
> **关联 Issue**: `SUO-241-BE-002` — 运行记录与审计最小合同 API  
> **Paperclip task**: [SUO-246](/SUO/issues/SUO-246)  
> **父需求**: [SUO-198](/SUO/issues/SUO-198)  
> **Domain / 优先级**: `backend` / `P0`  
> **设计决策**: `DEC-021`, `DEC-022`, `DEC-023`  
> **生成依据**: `TASK-REQUIREMENT-FORMAT.md` 已填充提示词、设计稿 §3.2 / §6.3

## 1. 任务标题

实现 Story Workspace Episodes 的不可变运行、artifact 版本、用户审阅事件与执行 Gate 审计合同及只读查询 API。

## 2. 关联 Issue

| Issue | 关系 | 本任务承接内容 |
|---|---|---|
| `SUO-241-BE-002` | 直接来源 | run / artifact / review / gate 四类审计对象与查询 API |
| `SUO-241-BE-001` | 前置 | 统一投影、artifact envelope 与 content hash |
| `SUO-226-BE-004` | 稳定依赖 | Workflow Run 创建 API 与 Deck 快照语义 |
| `SUO-241-BE-003` | 下游 | Gate 聚合、确认与后续执行审计 |

标签：`api`、`run-record`、`audit`、`versioning`、`delta`。

## 3. 任务目标

建立可追踪“一句话输入/参考接入 → Agent 产出 → 页面审阅 → 再次生成 → 后续执行”的最小审计面，使每一次 run、attempt、artifact version、review action 和 execution gate decision 都能重放来源与结果，同时不泄露 Deck secret/config。

核心原则：

- run、attempt 与 artifact version 不可变；修订通过新记录和引用关系表达。
- 旧 attempt 默认折叠、只读、可比较，任何刷新或路由切换不得删除历史。
- 四类状态维度分别记录，不能由 source `draft` 或 Agent `PASS` 推导用户确认。
- 本任务提供审计事实与查询，不擅自定义 Stage 排期或 Deck 内部执行逻辑。

## 4. 实现步骤

### 4.1 定义四类审计对象

1. `StoryWorkspaceRunRecord`：保存 `storyWorkspaceRunId`、attempt、source kind、input summary、Deck workflow/release/runtime snapshot refs、canonical status、retry/supersede refs、started/finished 时间与 failed stage。
2. `StoryWorkspaceArtifactVersion`：保存 artifact ID/kind/version、source path、source-declared version、content hash、schema version、generated-from、ingested/generated at/by 与 validation status。
3. `StoryWorkspaceReviewEvent`：保存 event ID、review unit、run、artifact/version、action、reason、finding acknowledgements、actor、timestamp、request ID；action 覆盖 confirm、edit-confirm、reject、regenerate、continue。
4. `StoryWorkspaceExecutionGateRecord`：保存 required artifact versions、aggregate hash、gate result/reasons、trigger actor/time、idempotency key 与 downstream execution ID。

### 4.2 约束不可变与关系语义

1. 再次生成必须创建新 run/attempt 与新 artifact version，写入 `retryOfRunId` / `supersedesVersion`；禁止原地更新已确认版本。
2. 同一 request ID / idempotency key 的审阅或继续重试不得写入重复事件。
3. 编辑后确认只允许引用基线批准的结构化字段；保存生成新 artifact version，再对新版本确认。
4. 后续执行失败只追加执行结果，不回滚已确认 review event 或 gate aggregate。

### 4.3 提供运行记录查询 API

1. 实现 `GET /api/story-workspace/runs/:storyWorkspaceRunId`，返回 run、当前 attempt、artifact versions、review events、gate records 和非敏感 Deck 引用。
2. 实现 `GET /api/story-workspace/runs`，支持至少按 canonical status、时间范围筛选和稳定分页。
3. 历史按时间倒序；单条查询默认展开当前 attempt，旧 attempt 返回可比较摘要并允许显式展开。
4. 不新增绕过审阅状态机的公共写 API；写事件由 episode adapter、review gate 与 continue service 在同一业务事务中调用。

### 4.4 脱敏、授权与可观测性

1. 只返回 Deck workflow/release/runtime snapshot 的引用和允许展示的摘要；secret、token、原始 config value 不进入响应或日志。
2. 对 run 与 artifact 查询复用 Story Workspace 租户/项目授权，禁止通过可猜 ID 跨边界读取。
3. 记录 request ID 与结构化错误码，日志不得包含用户完整 prompt、secret 或未脱敏 artifact 内容。

### 4.5 迁移与兼容

1. 在既有 workflow run/schema 上做增量迁移，不把基线记录重写为 episodes 专属结构。
2. 老 run 缺 episodes 字段时返回显式 `null` / capability 标记，不伪造默认审阅事实。
3. 为数据迁移、索引建立、回滚与兼容读路径提供验证脚本或测试。

## 5. 涉及文件路径

### 允许新增或修改

```text
backend/src/routes/story-workspace/runs.ts
backend/src/services/story-workspace/run-record.service.ts
backend/src/db/schema/story-workspace/run-record.ts
backend/src/db/migrations/*story-workspace*run*audit*
backend/tests/story-workspace/run-record*
backend/tests/story-workspace/run-audit*
```

### 禁止修改

- `docs/design/`、`docs/issue/`、`docs/stage/`、`docs/exec/` 与其他 task 合同。
- 前端、Deck 插件内部 workflow、Agent 生成器与后续 execute 实现。
- 既有已确认 artifact/review/gate 审计事实。
- 视频、画布、模型计费或平台媒体能力。

## 6. 输入 / 输出说明

### 输入事件

| 来源 | 最小输入 |
|---|---|
| adapter | run、source kind、artifact envelope/version、validation result |
| review service | review unit、run、artifact version、action/reason/ack、actor、request ID |
| gate / continue service | required versions、aggregate hash、decision、idempotency key、execution ID/result |

### 查询输出

| API | 输出 |
|---|---|
| `GET /api/story-workspace/runs/:storyWorkspaceRunId` | 当前 run 全量审计视图，当前 attempt 展开、旧 attempt 可比较 |
| `GET /api/story-workspace/runs` | 经授权、可分页筛选的 run 摘要列表 |

响应必须显式区分 source status、Agent verdict、user review、execution status，并包含 provenance；不得返回 secret/config values。

## 7. 依赖项

| 依赖 | 要求 |
|---|---|
| `SUO-241-BE-001` | 先冻结 artifact ID/version/hash 与 projection 引用 |
| `SUO-226-BE-004` | 复用 run 创建、状态与 Deck snapshot 绑定 |
| 基线授权/审计设施 | 复用 actor、request ID、租户边界和日志脱敏规范 |

本任务完成后解锁 `SUO-241-BE-003`，并为详情的“版本与运行”Tab 提供合同。

## 8. 测试策略

1. **模型单测**：四类记录的必填字段、唯一键、关系和枚举验证。
2. **不可变测试**：再次生成产生新 attempt/version；已确认旧记录无法被更新或删除。
3. **幂等测试**：重复 request ID / idempotency key 只留一条语义事件，并返回同一结果。
4. **查询合同测试**：单条、列表、筛选、分页、倒序与旧 attempt 展开行为稳定。
5. **失败恢复测试**：后续执行失败后确认事件仍存在，可用原 gate aggregate 幂等重试。
6. **安全测试**：跨租户/项目读取被拒绝；响应和结构化日志不含 Deck secret/config。
7. **迁移测试**：旧 run 可读取且不会被伪造 episodes 字段；升级/回滚不删除审计记录。

## 9. 完成标志

- [ ] 四类审计对象及关系已落地，字段覆盖设计 §6.3。
- [ ] run 单条与列表 API 支持授权、筛选、分页和稳定排序。
- [ ] 当前 attempt 默认展开，旧 attempt 只读可比较。
- [ ] 再次生成、编辑后确认和执行重试均保留不可变历史。
- [ ] 重复请求不会生成重复 review/gate/execution 事实。
- [ ] 四状态维度在存储和响应中明确分离。
- [ ] Deck secret/config 已从响应与日志中排除。
- [ ] 单测、API 合同测试、权限测试与迁移测试通过。

## 10. 风险提示

| 风险 | 处理 / 回滚 |
|---|---|
| 审计表与基线 run 模型职责重叠 | 以增量引用/扩展表承接，不复制或改写稳定 run 主状态 |
| 事件去重与事务边界不一致 | request ID/idempotency key 建唯一约束；业务写与审计写同事务 |
| 日志泄露 prompt 或 Deck 配置 | 输出 allowlist + 结构化脱敏测试 |
| `[CLARIFICATION_NEEDED] 手工结构化编辑范围` | **Owner：产品 owner**；默认仅基线批准字段，任何保存都生成新 artifact version |
| 回滚导致审计不可读 | 数据表向后兼容保留；代码回滚不得删除历史，可启用旧读路径或只读降级 |

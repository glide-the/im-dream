# Task: Story Workspace Episodes 审阅 Gate 冲突阻断校验（Backend）

> **Task ID**: `task_241_backend_review-gate-conflict`  
> **关联 Issue**: `SUO-241-BE-003` — 审阅 Gate 服务端聚合与冲突阻断校验  
> **Paperclip task**: [SUO-246](/SUO/issues/SUO-246)  
> **父需求**: [SUO-198](/SUO/issues/SUO-198)  
> **Domain / 优先级**: `backend` / `P0`  
> **设计决策**: `DEC-018`, `DEC-022`, `DEC-023`, `DEC-024`  
> **生成依据**: `TASK-REQUIREMENT-FORMAT.md` 已填充提示词、设计稿 §3.3 / §4.3 / §6.2

## 1. 任务标题

扩展运行级 Story Workspace Review Gate，使其按明确 artifact versions 与 aggregate hash 聚合，并在冲突、缺失、过期或 Agent 阻断时由服务端拒绝确认和后续执行。

## 2. 关联 Issue

| Issue | 关系 | 本任务承接内容 |
|---|---|---|
| `SUO-241-BE-003` | 直接来源 | episodes Gate 聚合、冲突/过期校验、防绕过与幂等 |
| `SUO-241-BE-002` | 前置 | run、artifact version、review event、gate record |
| `SUO-230-BE-001` | 稳定基线 | 运行级 Review Gate，不在本任务中另建平行 Gate |
| `SUO-241-SH-002` | 下游验证 | 冲突、过期、BLOCK、防绕过与幂等 E2E |

标签：`api`、`review-gate`、`conflict`、`security`、`delta`。

## 3. 任务目标

在基线 Gate 上增加 episodes artifact bundle 的权威校验，确保“页面按钮禁用”只是体验表现，真正的确认和继续授权始终来自服务端。聚合对象必须绑定同一 `workflow_run_id` 的明确 required artifact versions 和 aggregate hash，避免列表漂移、批量误确认、旧版本确认和客户端直接绕过。

## 4. 实现步骤

### 4.1 扩展 Gate 聚合读模型

1. 给定 `workflow_run_id`，加载最新活动 attempt、required artifact kinds、明确 artifact IDs/versions、完整性、validation diagnostics、Agent review findings 与用户审阅状态。
2. required artifact kinds 优先读取 locked Deck workflow snapshot；缺省时使用 script/storyboard/prompts/review-report，并把 assumption 返回给调用方。
3. 对参与聚合的稳定序列计算 `aggregate_hash`；hash 输入至少包含 run、attempt、required artifact IDs/versions/content hashes 与规则版本。
4. 返回每个阻断/警告的来源值、规则与受影响 review unit，不能只返回一个布尔值。

### 4.2 实现阻断矩阵

1. required artifact 缺失：阻断。
2. episode/project/version/generated-from、数量或 hash 不一致：阻断，使用 `story-workspace-artifact-version-conflict` 类诊断。
3. 多源时长差异：由 workflow 规则决定 warning 或 block；未知阈值不得硬编码为产品事实。
4. Agent overall verdict 为 BLOCK：阻断；CONDITIONAL/WARN 只有用户显式 acknowledgements 后才能通过。
5. Agent 审查范围不完整：按 workflow 规则判定；结果与缺失 reviewer 等事实必须返回。
6. 审阅期间产生新 artifact version、attempt 或 aggregate：旧审阅进入 stale，阻断并要求重新审阅。
7. Agent PASS 不得代替 user confirmed；source draft 不得映射为 user pending/rejected。

### 4.3 收紧确认合同

1. 确认/编辑后确认必须接收 `workflow_run_id`、`review_version`、`aggregate_hash`，并绑定明确 review unit 和 artifact version。
2. 服务端重新加载权威聚合，逐项校验 run、attempt、版本、hash、完整性、Agent findings acknowledgement 与 actor 权限。
3. 批量确认必须提交稳定 review unit + artifact version 集合；禁止使用“当前列表所有项”等漂移目标。
4. 编辑后确认在允许字段范围内创建新 artifact version，并对新 aggregate 原子校验；不得继承旧确认。

### 4.4 收紧后续执行与幂等

1. continue/complete 请求到达时再次计算并比较确认时 aggregate hash。
2. 同一确认聚合只发出一次下游信号；使用持久化 idempotency key 与 execution gate record 去重。
3. 首次下游执行失败时保留 confirmed 事实与 gate record；重试复用同一授权聚合并记录新 attempt/result。
4. 任何直接调用 API、伪造 UI 状态或跳过确认的请求都按服务端聚合拒绝。

### 4.5 错误与审计合同

1. 使用 `story-workspace` 前缀的稳定机器错误码，至少区分 gate locked、artifact missing、artifact conflict、review stale、aggregate mismatch、Agent blocked 与 acknowledgement required。
2. 错误响应包含可安全展示的冲突摘要与刷新/重审/退回建议，不泄露源文件全文或 Deck secret。
3. 确认、拒绝、冲突拒绝和继续结果写入 `StoryWorkspaceReviewEvent` / `StoryWorkspaceExecutionGateRecord`，关联 actor、request ID 与 idempotency key。

## 5. 涉及文件路径

### 允许新增或修改

```text
backend/src/routes/story-workspace/review-gate.ts
backend/src/services/story-workspace/review-gate.service.ts
backend/src/services/story-workspace/conflict-validator.ts
backend/tests/story-workspace/review-gate*
backend/tests/story-workspace/conflict-validator*
```

### 禁止修改

- `docs/design/`、`docs/issue/`、`docs/stage/`、`docs/exec/` 与其他 task 合同。
- frontend、Deck workflow 内部逻辑、Agent 生成器或 execute 实现。
- 通过弱化 `SUO-230-BE-001` 基线 Gate 来迁就客户端。
- 复杂画布、视频或模型计费能力。

## 6. 输入 / 输出说明

### 输入

| 输入 | 必需字段 |
|---|---|
| Gate 查询 | `workflow_run_id` |
| 确认 | `workflow_run_id`、review unit、artifact version、`review_version`、`aggregate_hash`、acknowledgements、request/idempotency ID |
| 后续执行 | `workflow_run_id`、已确认 `aggregate_hash`、action、idempotency key |
| 权威事实 | active attempt、required artifacts、validation diagnostics、Agent findings、user review events |

### 输出

| 输出 | 内容 |
|---|---|
| Gate aggregate | required versions、aggregate hash、status、warnings、blockers、assumptions、available actions |
| 确认结果 | 被确认的 review unit/version、review event 与更新后的 aggregate |
| 拒绝结果 | 稳定错误码、冲突来源摘要、恢复动作 |
| continue 结果 | triggered/already-triggered/failed-retryable 与 execution gate record |

## 7. 依赖项

| 依赖 | 要求 |
|---|---|
| `SUO-241-BE-002` | 四类审计记录与 idempotency 存储先稳定 |
| `SUO-230-BE-001` | 在既有运行级 Gate 上增量扩展 |
| Deck workflow snapshot | 提供 required artifacts、时长与审查完整性规则 |

本任务完成后与 `SUO-241-FE-004` 共同解锁 `SUO-241-SH-002`。

## 8. 测试策略

1. **聚合单测**：required artifacts 完整/缺失、CONDITIONAL acknowledgement、BLOCK、审查范围不完整。
2. **冲突表驱动测试**：episode/version/generated-from、数量、hash 与多源时长逐类覆盖 warning/block。
3. **过期竞态测试**：读取 aggregate 后生成新 version，再以旧 `review_version` / hash 确认，必须拒绝。
4. **防绕过 API 测试**：无确认、部分确认、被拒绝、冲突态、伪造客户端状态均不能 continue/complete。
5. **幂等测试**：重复确认和重复 continue 只产生一条语义结果，不重复发信号。
6. **失败恢复测试**：确认后下游失败不回滚确认；合法重试可追踪且不重复执行。
7. **权限/脱敏测试**：越权 run 被拒绝；错误和日志不含 Deck secret/config 或 artifact 全文。

## 9. 完成标志

- [ ] Gate 返回明确 required artifact versions、aggregate hash、warnings、blockers 与 assumptions。
- [ ] 缺失、冲突、Agent BLOCK、未知悉 CONDITIONAL、审查不完整和 stale 均按规则处理。
- [ ] 确认合同强制 run + review version + aggregate hash + 明确 artifact version。
- [ ] 批量确认不能以漂移列表作为目标。
- [ ] continue/complete 再次校验 aggregate，客户端无法绕过。
- [ ] 确认和后续执行幂等，执行失败不回滚确认事实。
- [ ] 稳定错误码、恢复提示和审计记录完整。
- [ ] 单测、API 集成、安全与竞态测试通过。

## 10. 风险提示

| 风险 | 处理 / 回滚 |
|---|---|
| hash 输入或排序不稳定 | 冻结 canonical serialization 与规则版本，加入跨进程契约测试 |
| Gate 与页面各自推导规则 | 服务端返回权威 aggregate；前端仅投影，不复制授权逻辑 |
| `[CLARIFICATION_NEEDED] requiredArtifactKinds` | **Owner：CEOOrchestrator 路由 Deck owner**；默认四项仅作 assumption，快照优先 |
| `[CLARIFICATION_NEEDED] 时长差异阈值` | **Owner：产品 owner**；按百分比计算差异，具体 warning/block 由 workflow 规则决定 |
| 并发生成造成 TOCTOU | 确认事务内重算 active attempt/version/hash，使用乐观并发或等价约束 |
| 部署回滚弱化安全边界 | 保留基线 Gate 的默认拒绝策略；新字段缺失时 fail closed，不删除审计记录 |

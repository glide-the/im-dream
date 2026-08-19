# Task: Story Workspace Episodes Review Gate 冲突与过期联调（Shared）

> **Task ID**: `task_241_shared_review-gate-conflict-e2e`  
> **关联 Issue**: `SUO-241-SH-002` — 审阅 Gate 冲突阻断与版本过期联调  
> **Paperclip task**: [SUO-246](/SUO/issues/SUO-246)  
> **父需求**: [SUO-198](/SUO/issues/SUO-198)  
> **Domain / 优先级**: `shared` / `P0`  
> **设计决策**: `DEC-018`, `DEC-022`, `DEC-023`, `DEC-024`  
> **生成依据**: `TASK-REQUIREMENT-FORMAT.md` 已填充提示词、设计稿 §6.2 / §8.1

## 1. 任务标题

端到端验证 Episodes Review Gate 的冲突、缺失、Agent 阻断、stale review、确认三元组、防绕过和幂等继续。

## 2. 关联 Issue

| Issue | 关系 | 本任务承接内容 |
|---|---|---|
| `SUO-241-SH-002` | 直接来源 | Gate 安全矩阵与端到端收口 |
| `SUO-241-BE-003` | 前置 | 服务端聚合、冲突/过期校验、幂等和防绕过 |
| `SUO-241-FE-004` | 前置 | 右栏确认/驳回/继续与锁定表现 |
| `SUO-230-SH-001` | 稳定基线 | 运行级审阅 Gate 幂等 E2E，不在本任务中重写 |

标签：`e2e`、`review-gate`、`conflict`、`security`、`delta`。

## 3. 任务目标

证明 UI 锁定与服务端拒绝同时成立：任一 required artifact 缺失、版本/身份冲突、Agent BLOCK、未确认 CONDITIONAL、审查不完整（按规则）或 active version 过期时，用户不能确认或进入后续执行；合法确认也必须绑定 run、review version、aggregate hash 和明确 artifact versions，并保持幂等、可审计。

## 4. 实现步骤

### 4.1 冻结跨端责任边界

| 边界 | 责任 |
|---|---|
| 前端 | 传递 run/review/hash/明确版本；展示冲突/过期；锁定不允许的动作；处理服务端竞态拒绝 |
| 后端 | 权威聚合 required versions/hash；版本/冲突校验；idempotency；直接 API 防绕过 |
| 联调 | 注入冲突、缺失、BLOCK、CONDITIONAL、stale、重复继续与执行失败场景 |
| 验收 | UI 锁定与 API 拒绝同时成立；合法确认/继续只发生一次且全链路可审计 |

前端不得复制服务端授权规则，后端不得依赖前端按钮状态；shared 代码不得成为新的 Gate 实现。

### 4.2 构建 Gate 场景矩阵

1. 基线合法场景：required artifacts 完整、一致、Agent 无 BLOCK、active versions 稳定。
2. 缺失场景：分别缺 script/storyboard/prompts/review-report，或 workflow snapshot 声明的其他 required kind。
3. 冲突场景：EP01 script@v5 vs storyboard generated-from@v1，并覆盖 episode/project、shot count、hash 冲突。
4. 时长场景：script/storyboard/prompt/target 差异低于 warning、达到 warning、达到 block；等级来自测试 workflow 规则。
5. Agent 审查场景：BLOCK、CONDITIONAL 未知悉/已知悉、reviewer 范围不完整。
6. stale 场景：用户打开 review v1 后产生 v2 / 新 attempt / 新 aggregate。

### 4.3 验证 UI 与确认合同

1. 每个阻断场景均显示来源值、原因和恢复动作；确认/保存并确认/继续禁用。
2. warning/CONDITIONAL 场景要求显式 acknowledgement，提交后请求包含 acknowledgement IDs。
3. 合法确认请求断言包含 `workflow_run_id`、明确 review unit/artifact versions、`review_version`、`aggregate_hash` 与 request/idempotency ID。
4. stale/aggregate mismatch 响应后旧内容转为只读，用户必须切换最新版本重新审阅。

### 4.4 验证服务端防绕过

1. 直接调用确认 API，分别省略/伪造 run、review version、aggregate hash 或 artifact version，必须拒绝。
2. 无确认、部分确认、存在 rejected/block/conflict 时直接调用 continue/complete，必须由聚合状态拒绝。
3. 模拟前端篡改 available actions 或按钮启用，服务端结果不受影响。
4. 验证越权 run/episode 访问与跨租户请求被拒绝，错误信息不泄露敏感来源。

### 4.5 验证幂等与失败恢复

1. 重复确认、快速双击和网络重试只生成一条语义确认事件。
2. 全部必审单元确认后，首次 continue 只发出一次下游信号；重复请求返回已处理结果。
3. 模拟后续执行失败，confirmed 事实和 aggregate hash 不回滚；合法重试可继续追踪。
4. 若失败后 artifact version 改变，旧 aggregate 不可重用，必须重新审阅。

### 4.6 固化自动化与证据

1. 当前仓库无已检测到的 Playwright/Cypress/Vitest/Jest harness；Stage 先安排 harness bootstrap 或批准 agent-browser + API 的可追溯方案。
2. 证据至少包含请求/响应摘要、稳定错误码、数据库/审计断言、关键页面截图/trace 和测试规则版本。
3. 对安全关键 API 使用自动化请求断言；仅靠按钮截图不能作为防绕过验收。

## 5. 涉及文件路径

### 允许新增或修改

```text
e2e/tests/story-workspace/review-gate-conflict.spec.ts
e2e/tests/story-workspace/review-gate-stale.spec.ts
e2e/tests/story-workspace/review-gate-bypass.spec.ts
e2e/tests/story-workspace/review-gate-idempotency.spec.ts
e2e/tests/story-workspace/fixtures/review-gate/
e2e/tests/story-workspace/helpers/review-gate-api.helper.ts
e2e/tests/story-workspace/helpers/review-gate-ui.helper.ts
backend/tests/story-workspace/review-gate.security*
```

生产实现默认只读；缺陷回流 `SUO-241-BE-003` 或 `SUO-241-FE-004` 边界修复。

### 禁止修改

- `docs/design/`、`docs/issue/`、`docs/stage/`、`docs/exec/` 与其他 task 合同。
- Deck/Agent/execute 内部逻辑、源 EP01/EP90 样本。
- 为通过测试而弱化 Gate、跳过 aggregate 重算或关闭权限校验。
- Canvas、平台视频、模型计费或移动端能力。

## 6. 输入 / 输出说明

### 输入

| 输入 | 内容 |
|---|---|
| Gate fixtures | required versions、source conflicts、duration rules、Agent findings、review completeness |
| 确认请求 | run、review unit/versions、review version、aggregate hash、ack、idempotency ID |
| continue 请求 | confirmed aggregate hash、action、idempotency key |

### 输出

| 输出 | 证据 |
|---|---|
| UI 结果 | 锁定/可用状态、并列来源、stale 与恢复提示 |
| API 结果 | 成功/拒绝、稳定错误码、最新 aggregate 摘要 |
| 审计结果 | review event、gate record、execution signal/count、request ID |
| 测试报告 | 场景矩阵、规则版本、截图/trace 与责任归属 |

## 7. 依赖项

| 依赖 | 状态门槛 |
|---|---|
| `SUO-241-BE-003` | 权威 Gate、错误码、幂等与防绕过 API 可用 |
| `SUO-241-FE-004` | 右栏动作、冲突/stale 展示与请求合同可用 |
| `SUO-241-BE-002` | review/gate/execution 审计可查询 |
| E2E harness | **Stage 前置 gate**：先冻结自动化或 agent-browser + API 证据方案 |

## 8. 测试策略

| 测试类 | 必测断言 |
|---|---|
| required missing | UI 锁定；确认和 continue API 均拒绝 |
| version/identity/hash conflict | 并列来源；EP01 已知冲突不可确认 |
| duration rules | warning/block 严格按 fixture workflow 规则，不硬编码产品阈值 |
| Agent findings | BLOCK 拒绝；CONDITIONAL/WARN 未 ack 拒绝、已 ack 可继续评估 |
| incomplete review | 缺 reviewer 等事实按 workflow 规则处理并可解释 |
| stale / race | v1 打开后生成 v2，旧 review version/hash 确认被拒绝 |
| malformed/bypass | 缺字段、伪造按钮、直接 continue、越权访问全部被服务端拒绝 |
| idempotency | 重复 confirm/continue 不重复事件或下游信号 |
| execution failure | confirmed 不回滚；同 aggregate 可重试，version 改变后不可重用 |

安全测试必须断言服务端状态与审计，而不仅是前端可见结果。

## 9. 完成标志

- [ ] 场景矩阵覆盖缺失、冲突、时长、BLOCK、CONDITIONAL、审查不完整与 stale。
- [ ] 每个阻断场景同时证明 UI 锁定和 API 拒绝。
- [ ] 确认三元组及明确 artifact versions 的合同断言完整。
- [ ] 直接调用、字段伪造、部分确认和越权均无法绕过 Gate。
- [ ] 重复确认/继续只产生一次语义结果和下游信号。
- [ ] 后续失败不回滚 confirmed，版本变化后旧 aggregate 失效。
- [ ] 前端、后端、联调和验收责任边界均有证据。
- [ ] 自动化或批准的可追溯测试报告已归档。

## 10. 风险提示

| 风险 | 处理 / 回滚 |
|---|---|
| 只测 UI 导致假安全 | 必须直接调用 API 并断言审计/信号计数 |
| 并发窗口难稳定复现 | 提供测试钩子/fixture 控制 v2 生成时机，不在生产关闭校验 |
| `[CLARIFICATION_NEEDED] requiredArtifactKinds` | **Owner：CEOOrchestrator 路由 Deck owner**；用 locked test snapshot 显式声明，默认四项仅作 assumption |
| `[CLARIFICATION_NEEDED] 时长差异阈值` | **Owner：产品 owner**；fixture 注入百分比规则，测试事实差异与等级分开断言 |
| `[CLARIFICATION_NEEDED] 手工结构化编辑范围` | **Owner：产品 owner**；默认仅基线批准字段，新版本原子确认，禁止原地编辑已确认版本 |
| 无现成 E2E harness | Stage 先安排 bootstrap/批准 agent-browser；安全 API 测试不得省略 |
| 回滚弱化 Gate | 服务端保留 fail-closed；可回滚 UI 增量但不能放宽 API 校验或删除审计 |

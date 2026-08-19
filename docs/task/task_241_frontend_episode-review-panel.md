# Task: Story Workspace EpisodeReviewPanel 分集审阅区（Frontend）

> **Task ID**: `task_241_frontend_episode-review-panel`  
> **关联 Issue**: `SUO-241-FE-004` — EpisodeReviewPanel 分集审阅区  
> **Paperclip task**: [SUO-246](/SUO/issues/SUO-246)  
> **父需求**: [SUO-198](/SUO/issues/SUO-198)  
> **Domain / 优先级**: `frontend` / `P0`  
> **设计决策**: `DEC-021`, `DEC-022`, `DEC-023`, `DEC-024`  
> **生成依据**: `TASK-REQUIREMENT-FORMAT.md` 已填充提示词、设计稿 §5.5 / §6.2

## 1. 任务标题

实现固定右栏 `StoryWorkspaceEpisodeReviewPanel`，展示明确版本的审阅依据并安全发起确认、编辑后确认、驳回、再次生成和后续执行。

## 2. 关联 Issue

| Issue | 关系 | 本任务承接内容 |
|---|---|---|
| `SUO-241-FE-004` | 直接来源 | 右栏信息、用户意见、五类动作、冲突/stale 锁定 |
| `SUO-241-FE-003` | 前置 | episode/shot/run/artifact version 选择上下文 |
| `SUO-201-FE-004` | 稳定基线 | Review Panel 结构化编辑与审阅交互 |
| `SUO-241-BE-003` | 权威合同 | Gate aggregate、确认三元组与防绕过校验 |

标签：`review`、`panel`、`episode-review`、`delta`。

## 3. 任务目标

让用户在不离开当前 episode 详情的情况下，看清当前 run/attempt/artifact version、required artifact 完整性、Agent findings、冲突和审计，再对明确 review unit 采取动作。右栏关闭、路由切换或 UI 选中变化都不能改变 Gate 事实；所有授权由服务端 Gate 再校验。

## 4. 实现步骤

### 4.1 展示明确审阅目标

1. Header 显示 episode、可选 shot/review unit、run、attempt、artifact version 及“最新活动版本/历史版本/已过期”。
2. 显示 required artifact 的完整性、source path、source version 与 validation status。
3. 显示 Agent overall verdict、BLOCK/WARN/CONDITIONAL、审查范围、finding acknowledgements 和跨文件冲突。
4. 显示最近一次同类操作的 actor、time、request ID；完整历史链接到“版本与运行”Tab。

### 4.2 维护用户意见与动作前置条件

1. 驳回/退回修改必须填写原因并选择作用范围；确认意见可选。
2. `确认通过` 只确认当前未编辑的明确版本；`保存并确认` 只对基线允许的结构化字段开放。
3. 保存结构化编辑必须创建新 artifact version，并在同一受控流程中确认新版本；“保存”本身不等于确认。
4. pending-review、rejected、failed、conflict 等状态下的“再次生成”按设计提示放弃/继承语义，不允许覆盖旧版本。

### 4.3 绑定 Gate 合同

1. 确认和保存并确认请求携带 `workflow_run_id`、明确 review unit/artifact version、`review_version`、`aggregate_hash`、finding acknowledgements 与 request/idempotency ID。
2. 版本冲突、required artifact 缺失、Agent BLOCK、未确认 CONDITIONAL/WARN 或 stale review 时禁用确认，并显示服务端原因。
3. 服务端返回 aggregate mismatch / stale 时清除提交中状态，把旧内容转为只读并引导刷新最新版本。
4. 客户端禁止态只用于体验；不得缓存“已通过”绕过服务端。

### 4.4 实现驳回、再次生成与继续

1. 驳回成功后展示原因、退回范围和审计引用，Gate 保持锁定。
2. 再次生成创建新 run/attempt 后，新旧 attempt 并列；旧版本及草稿意见按设计保留或明确清理，不能误提交到新版本。
3. `进入后续执行` 仅在服务端 aggregate 为 confirmed 且当前版本仍 active 时可用；请求携带确认 aggregate hash 和 idempotency key。
4. 后续执行失败时保留确认视图，提供幂等重试，不要求重复确认；若 artifact 已改变则重新审阅。

### 4.5 交互与可访问性

1. 360px 右栏使用分节标题、键值对与简洁表单，不嵌套多层卡片。
2. 对 destructive-like 的驳回/放弃待审版本给出明确确认文案，但不把正常审阅变成多余弹窗。
3. loading、防重复、错误、焦点回归、键盘操作和 `aria-live` 完整；状态不能只靠颜色。
4. 关闭面板只改变本地可见性；重新打开从当前服务端 aggregate 恢复。

## 5. 涉及文件路径

### 允许新增或修改

```text
frontend/src/components/story-workspace/episode/StoryWorkspaceEpisodeReviewPanel.tsx
frontend/src/components/story-workspace/episode/*EpisodeReview*.test.tsx
frontend/src/components/story-workspace/review/
frontend/src/hooks/story-workspace/*episode-review*
frontend/src/services/story-workspace/*review-gate*
```

对 `frontend/src/components/story-workspace/review/` 只做 episodes 增量适配，不全量重写基线 Review Panel。

### 禁止修改

- `docs/design/`、`docs/issue/`、`docs/stage/`、`docs/exec/` 与其他 task 合同。
- 后端 Gate 权威规则、Deck workflow、Agent 生成器或 execute 实现。
- 已确认历史版本的原地编辑。
- Canvas、视频/播放器/模型选择/计费能力。

## 6. 输入 / 输出说明

### 输入

| 输入 | 内容 |
|---|---|
| selection | episode/shot/review unit、run、attempt、artifact version |
| Gate aggregate | required versions、review version、aggregate hash、warnings/blockers、allowed actions |
| projection/audit | completeness、source paths/versions、Agent findings、最近事件 |

### 输出

| 动作 | 请求要点 |
|---|---|
| confirm | 明确目标 + run + review version + aggregate hash + acknowledgements |
| edit-confirm | 允许字段 diff + 原/新版本约束 + 确认三元组 |
| reject | 明确目标 + 必填 reason + 退回范围 |
| regenerate | 原 run/attempt、补充意见、放弃确认（适用时） |
| continue | confirmed aggregate hash + idempotency key |

## 7. 依赖项

| 依赖 | 要求 |
|---|---|
| `SUO-241-FE-003` | 提供稳定选择上下文和版本展示 |
| `SUO-201-FE-004` | 复用基线 Review Panel 与结构化编辑边界 |
| `SUO-241-BE-003` | 提供权威 aggregate、稳定错误码与动作 API；可用 fixture 并行 |
| `SUO-241-BE-002` | 提供最近事件和完整历史引用 |

本任务完成后与 backend tasks 一起解锁 `SUO-241-SH-001`、`SUO-241-SH-002`。

## 8. 测试策略

1. **展示测试**：episode/shot/run/attempt/version、完整性、findings、冲突和最近审计齐全。
2. **表单测试**：驳回必填原因；确认意见可选；保存与保存并确认语义分离。
3. **合同测试**：确认请求始终携带 run + review version + aggregate hash + 明确 artifact version。
4. **阻断测试**：缺失、冲突、BLOCK、未知悉 CONDITIONAL、stale 均禁用确认并显示原因。
5. **竞态测试**：提交前后产生新 artifact，旧请求被服务端拒绝后正确切换只读 stale。
6. **幂等测试**：快速双击/网络重试不重复确认或继续；继续失败不清除 confirmed。
7. **面板生命周期测试**：关闭、重开、刷新和路由切换不改变 Gate 事实。
8. **可访问性测试**：表单 label、错误关联、focus、键盘和 live region 正确。

## 9. 完成标志

- [ ] 右栏始终显示明确 review unit 与最新/历史版本状态。
- [ ] required artifacts、Agent findings、冲突、ack 与最近审计可见。
- [ ] 确认、保存并确认、驳回、再次生成、后续执行动作齐全。
- [ ] 驳回原因必填；保存不等于确认。
- [ ] 所有确认动作传递 run / review version / aggregate hash / artifact version。
- [ ] conflict/stale/BLOCK 等状态无法从 UI 发起合法确认。
- [ ] 后续失败保留确认事实并支持幂等重试。
- [ ] 组件、竞态、合同与可访问性测试通过。

## 10. 风险提示

| 风险 | 处理 / 回滚 |
|---|---|
| 选中 shot 变化导致误确认 | 动作前再次展示并校验明确 review unit/version，切换时取消旧提交上下文 |
| 前端规则复制导致与服务端漂移 | available actions 和 blockers 以服务端 aggregate 为准 |
| `[CLARIFICATION_NEEDED] 手工结构化编辑范围` | **Owner：产品 owner**；默认仅基线批准字段，保存一律生成新 artifact version |
| 再次生成误覆盖旧审计 | 新 run/attempt 明确展示，旧版本永久只读保留 |
| 回滚造成 Gate 行为降级 | 可回滚到基线只读 Review Panel；服务端继续 fail closed，不能以旧 UI 绕过 |

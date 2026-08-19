# Task: Story Workspace Episodes 统一投影端到端联调（Shared）

> **Task ID**: `task_241_shared_episode-projection-e2e`  
> **关联 Issue**: `SUO-241-SH-001` — 统一投影端到端联调（参考产物 + 简单描述 → 渲染 → 审阅）  
> **Paperclip task**: [SUO-246](/SUO/issues/SUO-246)  
> **父需求**: [SUO-198](/SUO/issues/SUO-198)  
> **Domain / 优先级**: `shared` / `P0`  
> **设计决策**: `DEC-020`, `DEC-021`, `DEC-024`, `DEC-025`  
> **生成依据**: `TASK-REQUIREMENT-FORMAT.md` 已填充提示词、设计稿 §3.1 / §8.1

## 1. 任务标题

端到端验证参考 episodes 与简单描述触发的新产出进入同一个 `StoryWorkspaceEpisodeProjection`、页面骨架、版本模型和审阅语义。

## 2. 关联 Issue

| Issue | 关系 | 本任务承接内容 |
|---|---|---|
| `SUO-241-SH-001` | 直接来源 | 两种来源统一投影与 UI/审阅闭环 |
| `SUO-241-BE-001` | 前置 | adapter、projection、完整性和冲突 diagnostics |
| `SUO-241-FE-004` | 前置 | 页面、列表、详情与 Review Panel 已形成可审阅链 |
| `SUO-241-SH-002` | 相邻安全验证 | Gate 冲突、stale、防绕过和幂等的深入覆盖 |

标签：`e2e`、`integration`、`episode-projection`、`delta`。

## 3. 任务目标

以 EP01 / EP90 固定样本和一个固定简单描述场景，证明“参考内容接入”与“即时 Agent 生成”不存在字段、状态、版本、路由或审阅语义分叉。流程必须覆盖：接入/创建 run → artifact 到达 → projection → 列表/详情/右栏 → 用户审阅 → 运行历史，并留下可重复、可审计的证据。

本任务只验证文本与结构化元信息；复杂画布和平台视频能力明确排除。

## 4. 实现步骤

### 4.1 冻结跨端责任边界

| 边界 | 责任 |
|---|---|
| 前端 | 同一页面渲染两种来源；列表、七 Tabs、Review Panel、状态和运行历史只消费统一投影 |
| 后端 | 解析参考/Agent artifact bundle；输出统一 projection、provenance、完整性、冲突和不可变版本 |
| 联调 | 用固定数据核对请求、响应、路由选择、状态变化、审阅目标与审计关系 |
| 验收 | 两种来源无字段/状态/版本/审阅语义分叉；已知冲突和时长差异可见且不被改写 |

任何缺陷由对应 frontend/backend owner 修复；shared task 负责复现矩阵、契约断言和收口证据，不偷偷建立第三套适配逻辑。

### 4.2 准备可重复测试数据

1. 只读复制或受控加载 `output/episodes/EP01`、`output/episodes/EP90` 到隔离 fixture，记录原始 hashes。
2. 固定一个简单描述、Deck workflow/release/runtime snapshot 与确定性 Agent stub/fixture，生成同类 artifact bundle。
3. 为每个场景记录 source kind、run ID、attempt、artifact IDs/versions/content hashes 与预期 diagnostics。
4. 测试清理只能删除本测试命名空间数据，不能修改源样本或既有审计。

### 4.3 验证参考产物接入

1. 索引 EP01 / EP90，等待 adapter 完成解析和 projection。
2. 断言五类 artifact 的存在/可选性、字段 provenance、source versions 与 raw fallback。
3. 断言 EP01/EP90 已知版本、时长和审查范围差异被原样保留；script@v5 / storyboard@v1 形成冲突诊断。
4. 在列表、详情七 Tabs、Review Panel 和 Run History 中核对同一 run/artifact version。

### 4.4 验证简单描述生成

1. 从 `StoryWorkspacePromptComposer` 提交固定描述并创建 run。
2. 验证 queued/running → output-validating → pending-review 或明确阻断态的可见进度。
3. Agent fixture 产出经同一 adapter 后进入同一列表、详情、右栏和运行历史，不能走前端专用映射。
4. 对相同字段集、状态标签、版本条和审阅动作做与参考来源一致的契约断言。

### 4.5 验证审阅与历史

1. 在无阻断 fixture 上确认明确 review unit/artifact version，并核对 review event。
2. 在冲突 fixture 上确认按钮锁定；服务端拒绝逻辑的深入场景由 `SUO-241-SH-002` 承接。
3. 触发驳回/再次生成，验证新 attempt/version 与旧事实并列，旧事件不消失。
4. 验证运行历史倒序、当前 attempt 展开、旧 attempt 只读可比较。

### 4.6 固化证据与测试入口

1. 当前仓库未检测到 Playwright/Cypress/Vitest/Jest harness；Stage 必须先安排独立 harness bootstrap，或明确批准等价的 agent-browser 可追溯方案。
2. 自动化方案至少输出 API 契约断言、关键页面截图/trace、测试数据 IDs/hashes 和通过/失败摘要。
3. 不把 harness 安装、跨仓库基础设施改造或生产实现混入本 shared task 的验收。

## 5. 涉及文件路径

### 允许新增或修改

```text
e2e/tests/story-workspace/episode-projection.spec.ts
e2e/tests/story-workspace/fixtures/episodes/
e2e/tests/story-workspace/fixtures/prompt-generated/
e2e/tests/story-workspace/helpers/episode-api.helper.ts
e2e/tests/story-workspace/helpers/episode-ui.helper.ts
backend/tests/story-workspace/episode-projection.contract*
frontend/src/components/story-workspace/episode/__tests__/episode-projection.contract*
```

生产代码路径默认只读；联调发现的实现缺陷回到对应 backend/frontend task 边界修复。

### 禁止修改

- `docs/design/`、`docs/issue/`、`docs/stage/`、`docs/exec/` 与其他 task 合同。
- `output/episodes/EP01`、`output/episodes/EP90` 原始样本。
- Deck 插件内部、平台视频、复杂画布、模型计费或移动端实现。

## 6. 输入 / 输出说明

### 输入

| 场景 | 输入 |
|---|---|
| 参考接入 | EP01 / EP90 artifact bundle + locked workflow snapshot |
| 即时生成 | 固定简单描述 + Deck snapshot + deterministic Agent fixture |
| 前后端合同 | projection、run history、Gate aggregate、review actions |

### 输出

| 输出 | 证据 |
|---|---|
| projection 契约结果 | 两种 source kind 的字段/状态/版本对照 |
| UI 链路结果 | 列表、Tabs、Review Panel、状态、Run History 截图/trace |
| 审阅审计结果 | review event、attempt/version、provenance 与 request ID |
| 差异清单 | 失败断言、责任边界、复现数据 ID/hash |

## 7. 依赖项

| 依赖 | 状态门槛 |
|---|---|
| `SUO-241-BE-001` | adapter/projection 合同完成并可使用固定 fixture |
| `SUO-241-FE-004` | 页面、列表、详情和 Review Panel 可联调 |
| `SUO-241-BE-002` | 运行历史/审计查询可用 |
| E2E harness | **Stage 前置 gate**：先选定自动化 harness 或批准 agent-browser 证据规范 |

## 8. 测试策略

| 场景 | 核心断言 |
|---|---|
| EP01 接入 | 五类 artifact 可追踪；版本冲突保留；列表/详情/右栏版本一致 |
| EP90 接入 | 缺失 reviewer 等审查范围事实可见；按 workflow 规则标记 |
| 简单描述 | 创建 run，经同一 adapter/projection 渲染，无专用字段分支 |
| 多源时长 | script/storyboard/prompt/target 并列，不被单值覆盖 |
| raw fallback | 损坏/未知 schema 仍可查看原始内容，Gate 保持安全 |
| 驳回/重生成 | 新 attempt/version 产生，旧 artifact、意见和事件保留 |
| 路由/刷新 | 列表、详情、review 深链与刷新保持明确版本上下文 |

重复执行测试必须使用隔离命名空间并产生一致断言；任何手工证据需包含步骤、时间、数据 ID 与关键截图。

## 9. 完成标志

- [ ] EP01、EP90 与简单描述场景均可重复执行。
- [ ] 两种来源进入同一 `StoryWorkspaceEpisodeProjection` 和同一 UI 组件链。
- [ ] 列表、七 Tabs、Review Panel、状态和 Run History 使用同一 run/artifact version。
- [ ] 已知版本/时长/审查范围差异未被静默覆盖。
- [ ] 驳回与再次生成保留不可变历史。
- [ ] 前端、后端、联调和验收边界均有责任人/证据。
- [ ] 自动化或批准的可追溯验证通过并归档摘要。
- [ ] 无 Canvas、视频、模型计费或手工新建故事路径。

## 10. 风险提示

| 风险 | 处理 / 回滚 |
|---|---|
| 无现成 E2E harness | Stage 先安排 bootstrap/批准 agent-browser；不得在本 task 临时引入无维护基础设施 |
| Agent 输出不确定导致 flaky | 使用 deterministic fixture/stub，并另保留真实 smoke 场景 |
| 测试污染源样本或审计 | 复制到隔离命名空间，按显式前缀清理；源文件只读 |
| `[CLARIFICATION_NEEDED] requiredArtifactKinds` | **Owner：CEOOrchestrator 路由 Deck owner**；记录快照规则，默认四项仅作 assumption |
| `[CLARIFICATION_NEEDED] 时长差异阈值` | **Owner：产品 owner**；固定原始差异断言，等级断言读取 workflow 规则 |
| shared task 吞并生产修复 | 缺陷回流对应 owner task，shared 只维护契约和证据 |

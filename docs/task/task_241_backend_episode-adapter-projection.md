# Task: Story Workspace Episodes 元信息适配层与统一投影（Backend）

> **Task ID**: `task_241_backend_episode-adapter-projection`  
> **关联 Issue**: `SUO-241-BE-001` — Episodes 元信息适配层与统一投影数据模型  
> **Paperclip task**: [SUO-246](/SUO/issues/SUO-246)  
> **父需求**: [SUO-198](/SUO/issues/SUO-198)  
> **Domain / 优先级**: `backend` / `P0`  
> **设计决策**: `DEC-020`, `DEC-021`, `DEC-024`  
> **生成依据**: `TASK-REQUIREMENT-FORMAT.md` 已填充提示词、设计稿 §3.1 / §4.2～§4.4

## 1. 任务标题

实现 `story-workspace` Episodes 元信息适配层、兼容解析器与唯一的 `StoryWorkspaceEpisodeProjection` 投影合同。

## 2. 关联 Issue

| Issue | 关系 | 本任务承接内容 |
|---|---|---|
| `SUO-241-BE-001` | 直接来源 | 解析、字段映射、完整性、版本冲突与统一投影 |
| `SUO-201-BE-001` | 稳定基线 | Story Workspace schema，不在本任务中重写 |
| `SUO-226-BE-001` | 上游依赖 | workflow binding / run 与 Deck 快照引用 |
| `SUO-241-SH-001` | 下游验证 | 两种来源进入同一投影的端到端联调 |

标签：`episode`、`projection`、`adapter`、`schema`、`delta`。

## 3. 任务目标

把已有 `output/episodes/EP??` 参考产物和简单描述触发的 Agent 产物收敛到同一接入链：清单发现 → 兼容解析 → 来源事实保留 → 一致性校验 → artifact 版本封装 → `StoryWorkspaceEpisodeProjection`。列表、详情、审阅和运行记录只能消费这一个投影合同。

任务必须保证：

- 覆盖 script、storyboard、prompts、review report 与 render guide 的设计字段。
- 源文件状态、Agent 审查、用户审阅、后续执行保持四个独立维度。
- 冲突值并列保留并输出诊断，不静默选值、改值或覆盖源文件。
- 结构化解析失败仍可回退展示原始内容，未知 token 与未知 schema 不丢失。
- 本任务只定义并实现数据接入/投影；不实现页面、审阅动作、后续执行或视频能力。

## 4. 实现步骤

### 4.1 冻结 artifact envelope 与来源合同

1. 定义带 `storyWorkspace` 前缀的 manifest/envelope，至少记录 episode key、artifact ID/kind/version、source path、source-declared version、content hash、schema version、generated-from、接入/生成时间与 actor、validation status。
2. 明确 source kind：`story-workspace-episode-reference` 与 `story-workspace-prompt-generated`；两类来源只影响审计字段，不产生两套 projection 类型。
3. content hash 基于原始内容计算；接入封装字段不得回写到源文件或伪造 frontmatter。

### 4.2 实现分类型兼容解析

1. `script.md`：解析集级元信息、角色/场景引用、弧光、正文场景以及 CAM / `@EMOTION` / `@SETUP` / `@HOOK` / TRANS 标记。
2. `storyboard.yaml`：解析 episode/project、镜头统计、来源版本、shots 及摄影/画面/对白/时长/转场。
3. `prompts/*.yml`：解析工具与合同快照、生成审计、一致性、镜头 Prompt、参数和 generability。
4. `review-report.md`：解析审查范围、总裁决、维度、BLOCK/WARN、建议与签字；不得把 Agent 裁决转换成用户审阅结论。
5. `renders/render-guide.md`：只解析风险、费用估算、工具、镜头与队列文本元信息；不得引入视频预览、生成、播放器或模型选择能力。
6. 任一解析器失败时返回结构化诊断与原始文本引用，不能让单个 artifact 的失败吞掉其余已到达内容。

### 4.3 构建统一投影

1. 定义 `StoryWorkspaceEpisodeProjection`，完整覆盖 Issue 列出的集级、剧本、分镜、Prompt、Agent 审查与执行参考字段。
2. 保留多源时长：script estimate、storyboard total、prompt total、target duration，禁止归一成单个时长。
3. 分别保存 source status、agent review verdict、user review status、execution status；为 UI 提供只读聚合字段，但不改变权威事实。
4. 记录来源字段与系统补充字段的 provenance，确保页面可解释每个值来自哪个文件或接入封装。

### 4.4 完整性与冲突校验

1. 以 locked Deck workflow snapshot 的 `requiredArtifactKinds` 为权威；未提供时使用默认 `script/storyboard/prompts/review-report` 并记录 assumption。
2. 检测目录 episode、文件内 episode/project、source version、`generated_from`、shot 数量与 content hash 的不一致。
3. 版本/身份冲突输出 `story-workspace-artifact-version-conflict`，未知 schema 输出 `story-workspace-episodes-schema-unknown`。
4. 计算多源时长差异百分比；阈值由 workflow 规则注入，适配层只输出事实、差异和规则判定结果。
5. 以 EP01 / EP90 样本验证既有 script@v5 与 storyboard@v1 等冲突不会被静默修正。

### 4.5 持久化与查询边界

1. 在基线 schema 上以增量表/字段保存 artifact envelope、projection、diagnostics 与 provenance；迁移保持可回滚。
2. 写入必须幂等：同一 source path + content hash 重复接入不产生重复版本；内容变化生成新 artifact version。
3. 为 run record、Gate 聚合与页面查询提供稳定的 repository/service 接口，不在本任务开放无审计的任意文件写入 API。

## 5. 涉及文件路径

### 允许新增或修改

```text
backend/src/services/story-workspace/episode-adapter.ts
backend/src/services/story-workspace/episode-parser/
backend/src/db/schema/story-workspace/episode-projection.ts
backend/src/db/migrations/*story-workspace*episode*
backend/tests/story-workspace/episode-adapter*
backend/tests/fixtures/story-workspace/episodes/
```

若仓库实际测试或迁移目录不同，Stage 必须先确认约定，再使用同等的 `story-workspace` 前缀路径；不得另建无前缀业务包。

### 禁止修改

- `docs/design/`、`docs/issue/`、`docs/stage/`、`docs/exec/` 与其他 task 合同。
- 前端、Deck 插件内部实现、后续 execute 流程。
- `output/episodes` 参考样本原文。
- 视频预览/上传/生成/播放器、模型计费或复杂画布模块。

## 6. 输入 / 输出说明

### 输入

| 输入 | 关键内容 |
|---|---|
| artifact bundle | `script.md`、`storyboard.yaml`、`prompts/*.yml`、`review-report.md`、`renders/render-guide.md` |
| 接入上下文 | `storyWorkspaceRunId`、attempt、source kind、Deck workflow/release/runtime snapshot refs |
| workflow 规则 | required artifact kinds、时长警告/阻断规则、引用完整性规则 |

### 输出

| 输出 | 用途 |
|---|---|
| `StoryWorkspaceEpisodeProjection` | 列表、详情、审阅区与运行记录的唯一读模型 |
| artifact envelope/version | 版本、hash、来源与 generated-from 审计 |
| completeness result | 缺失 artifact/字段及默认 assumption |
| conflict diagnostics | 身份、版本、数量、hash、时长和 schema 冲突的并列事实 |
| raw fallback reference | 结构化解析失败后的原始内容展示入口 |

## 7. 依赖项

| 依赖 | 要求 |
|---|---|
| `SUO-201-BE-001` | 复用基线数据库、ID、时间戳与迁移规范 |
| `SUO-226-BE-001` | 获取 workflow binding/run 及锁定快照引用 |
| Deck workflow snapshot | 动态提供 required artifacts 与差异规则；运行中不可漂移 |

本任务完成后解锁 `SUO-241-BE-002`、`SUO-241-SH-001`，并为 frontend tasks 提供稳定投影合同。

## 8. 测试策略

1. **解析单测**：每种 artifact 各覆盖完整、缺字段、未知字段、格式损坏与原始回退。
2. **样本契约测试**：EP01 / EP90 均能形成投影；script@v5 / storyboard@v1 冲突保持两值并输出阻断诊断。
3. **完整性测试**：缺少默认必审项时明确列出缺失项；快照指定不同清单时按快照计算。
4. **时长测试**：四类时长同时保留；规则阈值变化只改变诊断等级，不改来源数值。
5. **幂等测试**：相同 hash 重复接入不增版本；内容变化生成新版本并保留旧事实。
6. **安全测试**：路径规范化、防目录穿越、大小/类型上限和错误日志脱敏。
7. **迁移测试**：升级/回滚均不破坏基线数据；回滚实现不删除既有 artifact 审计。

## 9. 完成标志

- [ ] 统一投影字段覆盖 Issue 的全部字段族，且两种来源共享同一模型。
- [ ] 五类 artifact 可解析，失败时有 raw fallback。
- [ ] required artifacts、身份/版本/generated-from、数量/hash 与时长差异均可校验。
- [ ] EP01 / EP90 已形成固定测试夹具，已知冲突不会被静默归一。
- [ ] source、Agent、user review、execution 四类状态严格分离。
- [ ] 重复接入幂等，内容变化产生不可变新版本。
- [ ] 迁移、单测、样本契约测试通过并留下结果。
- [ ] 未修改任何禁止范围，未引入画布或视频能力。

## 10. 风险提示

| 风险 | 处理 / 回滚 |
|---|---|
| episodes 无统一 manifest/schema | 使用接入 envelope；未知 schema 保留原文并标记，不猜测修复 |
| Markdown 半结构化导致误解析 | parser 分层、诊断可见；失败回退原文 |
| 样本版本天然不一致 | 并列保存来源值，交由 Gate 阻断，不覆盖数据 |
| `[CLARIFICATION_NEEDED] requiredArtifactKinds` | **Owner：CEOOrchestrator 路由 Deck owner**；默认四项只作为非阻塞 assumption，快照到位后覆盖 |
| `[CLARIFICATION_NEEDED] 时长差异阈值` | **Owner：产品 owner**；默认按百分比计算，警告/阻断阈值由 workflow 规则注入 |
| schema 回滚影响审计 | 代码回滚只停止新写入；已落库版本与审计不可删除，必要时保留兼容读路径 |

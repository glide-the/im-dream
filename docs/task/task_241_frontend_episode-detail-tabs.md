# Task: Story Workspace EpisodeDetail 分集详情 Tabs（Frontend）

> **Task ID**: `task_241_frontend_episode-detail-tabs`  
> **关联 Issue**: `SUO-241-FE-003` — EpisodeDetail 分集详情 Tabs  
> **Paperclip task**: [SUO-246](/SUO/issues/SUO-246)  
> **父需求**: [SUO-198](/SUO/issues/SUO-198)  
> **Domain / 优先级**: `frontend` / `P0`  
> **设计决策**: `DEC-020`, `DEC-021`, `DEC-024`, `DEC-025`  
> **生成依据**: `TASK-REQUIREMENT-FORMAT.md` 已填充提示词、设计稿 §5.4 / §7.2

## 1. 任务标题

实现 `StoryWorkspaceEpisodeDetail` 的七个结构化 Tabs，并让镜头选择与右侧审阅上下文安全联动。

## 2. 关联 Issue

| Issue | 关系 | 本任务承接内容 |
|---|---|---|
| `SUO-241-FE-003` | 直接来源 | 七个 Tabs、raw fallback、shot 选择与右栏联动 |
| `SUO-241-FE-002` | 前置 | 详情入口与明确 run/artifact version 选择 |
| `SUO-241-BE-001` | 数据合同 | 统一投影、raw fallback、provenance 和 diagnostics |
| `SUO-241-FE-004` | 下游 | 右栏审阅明确 episode/shot/artifact version |

标签：`tabs`、`episode-detail`、`structured-display`、`delta`。

## 3. 任务目标

把 episode artifact bundle 以概览、剧本、分镜、Prompt、Agent 审查、执行参考、版本与运行七个 Tab 呈现。所有复杂内容使用表格、键值对和结构化文本，不采用节点画布；解析失败或 schema 未知时保留原始 Markdown/YAML 文本入口。

## 4. 实现步骤

### 4.1 建立详情上下文

1. 详情加载必须绑定 `storyWorkspaceEpisodeId`、run、attempt 和 artifact version；页面标题明确显示是否为最新活动版本。
2. Tabs 切换、深链和刷新保留同一版本上下文，不能自动跳到另一个 run 后仍允许确认。
3. projection 更新产生新版本时，旧详情转为只读 stale 表现，并引导切换最新版本。

### 4.2 实现七个 Tabs

1. `StoryWorkspaceEpisodeOverview`：集元信息、角色/场景引用、人物弧光、完整性和四类时长对照。
2. `StoryWorkspaceEpisodeScriptDetail`：场景分组、动作/对白与 CAM / emotion / setup / hook / transition 标签；未知 token 原样显示。
3. `StoryWorkspaceEpisodeShotTable`：shot ID、场景、角色、摄影、画面、对白、时长和转场的结构化表格。
4. `StoryWorkspaceEpisodePromptTable`：逐镜 positive/negative prompt、参数、工具/合同快照与 generability；只读展示，不提供模型或视频生成控件。
5. `StoryWorkspaceAgentReviewFindings`：总裁决、审查范围、维度、BLOCK/WARN/建议与签字，明确标注“Agent 审查 ≠ 用户确认”。
6. `StoryWorkspaceRenderGuideReference`：风险、费用估算、工具和队列文本状态；作为执行参考，不提供视频预览/上传/播放器。
7. `StoryWorkspaceRunHistory`：artifact 关系、run/attempt、输入摘要、审阅和执行事件；当前 attempt 默认展开，历史只读。

### 4.3 结构化失败与 provenance

1. 每个区域显示数据来源文件、source version、artifact version 和 validation status。
2. 结构化解析失败时显示错误摘要和可访问的 raw fallback；不能显示空白或丢弃未识别内容。
3. 冲突字段并列展示全部来源值，禁止在 UI 内“选择一个看起来正确的值”。

### 4.4 镜头选择与右栏联动

1. 点击/键盘选择 shot 时发布带 episode、shot、run、attempt、artifact version 的选择事件。
2. 右栏切换到该镜头的结构化详情；Tab 或选中变化不自动执行确认。
3. 确认目标始终显示明确 review unit 与 artifact version，选中变化后清理未提交的错误目标或要求重新确认。

### 4.5 视觉与性能

1. 使用分节标题、键值表和行分隔，不嵌套多层面板。
2. 大型剧本/shot/prompt 内容按基线能力延迟渲染或虚拟化，保持 Tab 切换与键盘操作可用。
3. 状态、问题与选中态具文本/图标/focus 表达，不能只靠颜色。

## 5. 涉及文件路径

### 允许新增或修改

```text
frontend/src/components/story-workspace/episode/StoryWorkspaceEpisodeDetail.tsx
frontend/src/components/story-workspace/episode/tabs/
frontend/src/components/story-workspace/episode/*EpisodeDetail*.test.tsx
frontend/src/components/story-workspace/episode/tabs/*.test.tsx
```

### 禁止修改

- `docs/design/`、`docs/issue/`、`docs/stage/`、`docs/exec/` 与其他 task 合同。
- 后端 parser/projection/Gate、Dream shell、通用 Tabs/表格基线。
- Canvas/节点拖拽、视频预览/上传/生成/播放器、外部模型选择或计费。
- 将历史 artifact 变为可编辑，或把 Agent review 当用户确认。

## 6. 输入 / 输出说明

### 输入

| 输入 | 内容 |
|---|---|
| 详情上下文 | episode ID、run、attempt、artifact version、active-version 标志 |
| projection | 集级、剧本、shots、prompts、review、render guide、run history |
| diagnostics | completeness、冲突、schema unknown、raw fallback 与 provenance |

### 输出

| 输出 | 内容 |
|---|---|
| 七个 Tab | 结构化且可访问的 artifact 展示 |
| selection event | episode/shot/run/attempt/artifact version 明确目标 |
| stale/raw fallback UI | 过期只读提示或原始内容展示入口 |
| deep-link state | 可恢复当前 Tab 与稳定版本上下文 |

## 7. 依赖项

| 依赖 | 要求 |
|---|---|
| `SUO-241-FE-002` | 提供详情导航和版本化选择上下文 |
| `SUO-241-BE-001` | 提供统一 projection、provenance、diagnostics 与 raw fallback |
| `SUO-241-BE-002` | “版本与运行”Tab 的审计查询合同，可用 fixture 并行 |

本任务完成后解锁 `SUO-241-FE-004`。

## 8. 测试策略

1. **Tab 合同测试**：七个 Tabs 对完整 projection 均展示设计字段。
2. **解析回退测试**：损坏 Markdown/YAML、未知 token/schema 时原始内容仍可访问。
3. **冲突测试**：EP01 script@v5 / storyboard@v1 和多源时长并列显示，不静默归一。
4. **选择联动测试**：shot 选择携带完整版本目标；切换 Tab/episode 不发生误确认。
5. **stale 测试**：详情打开期间出现新版本，旧内容只读并要求切换最新版本。
6. **性能/可访问性测试**：大 shot/prompt 集合下 Tab 可用；键盘、focus、表头与读屏语义正确。
7. **范围回归**：执行参考 Tab 无视频预览、生成、播放器或模型选择。

## 9. 完成标志

- [ ] 七个设计 Tabs 与对应命名组件均已实现。
- [ ] 所有 Tabs 绑定同一明确 run/attempt/artifact version。
- [ ] shot 选择安全驱动右栏，不触发隐式确认。
- [ ] raw fallback、未知 token 和 provenance 可见。
- [ ] 冲突字段与多源时长并列展示。
- [ ] 历史 attempt 只读，stale 版本不可确认。
- [ ] 详情不包含 Canvas、视频能力、模型选择或计费。
- [ ] 组件、交互、性能和可访问性测试通过。

## 10. 风险提示

| 风险 | 处理 / 回滚 |
|---|---|
| 七个 Tabs 信息量过大 | 延迟渲染、虚拟化和稳定标题层级；不改成卡片/画布 |
| parser 输出随 schema 变化 | 以 capability/validation 状态渲染；未知内容走 raw fallback |
| 选择上下文漂移导致误确认 | 所有事件携带 run/attempt/version；右栏展示并复核目标 |
| render guide 被误解为视频功能 | 明确“执行参考”只读标签，禁止媒体控件 |
| 回滚丢失深链 | 保持列表/详情路由稳定；可降级到 raw/read-only 视图而不改变版本上下文 |


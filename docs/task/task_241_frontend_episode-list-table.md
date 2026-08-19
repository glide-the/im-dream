# Task: Story Workspace EpisodeListTable 分集列表（Frontend）

> **Task ID**: `task_241_frontend_episode-list-table`  
> **关联 Issue**: `SUO-241-FE-002` — EpisodeListTable 分集列表组件  
> **Paperclip task**: [SUO-246](/SUO/issues/SUO-246)  
> **父需求**: [SUO-198](/SUO/issues/SUO-198)  
> **Domain / 优先级**: `frontend` / `P0`  
> **设计决策**: `DEC-021`, `DEC-024`, `DEC-025`  
> **生成依据**: `TASK-REQUIREMENT-FORMAT.md` 已填充提示词、设计稿 §5.3 / §7.2

## 1. 任务标题

实现高密度、可扫描的 `StoryWorkspaceEpisodeListTable` 及轻量筛选 Toolbar，以表格承载分集元信息、冲突和审阅状态。

## 2. 关联 Issue

| Issue | 关系 | 本任务承接内容 |
|---|---|---|
| `SUO-241-FE-002` | 直接来源 | 列定义、筛选、冲突/时长展示与视觉规则 |
| `SUO-241-FE-001` | 前置 | 页面容器、路由与当前 run/episode 上下文 |
| `SUO-241-BE-001` | 数据合同 | `StoryWorkspaceEpisodeProjection` 摘要与 diagnostics |
| `SUO-241-FE-003` | 下游 | 列表选择进入详情 Tabs |

标签：`table`、`episode-list`、`data-display`、`delta`。

## 3. 任务目标

让用户在一个表格中快速定位 episode、产物完整性、镜头/多源时长、Agent 质量、来源版本、用户审阅和更新时间，并能按搜索、状态、问题和版本筛选。表格不得把来源状态、Agent 裁决和用户审阅混成一个状态，也不得使用复杂画布或层叠卡片。

## 4. 实现步骤

### 4.1 定义列表行视图模型

1. 从统一投影派生稳定 row key、episode/title/series、artifact completeness、shot/time metrics、Agent verdict、run/attempt/version、user review 与 updated time。
2. source status、Agent quality、user review 和 execution status 分列/分组展示，禁止互相推断。
3. 列表选择携带明确 episode ID、run、attempt 和 artifact version，避免详情/右栏来源漂移。

### 4.2 实现七组列

1. `EP / 标题`：episode、title、series；缺标题显示“未命名分集”而不补写源值。
2. `产物完整性`：script/storyboard/prompts/review/guide 五类紧凑文本+图标标签，required 与 optional 可区分。
3. `镜头 / 时长`：实际镜头数并列 script/storyboard/prompt/target；差异保留来源标签。
4. `Agent 质量`：PASS / CONDITIONAL / BLOCK / incomplete，不能表现为用户已确认。
5. `来源版本`：active run、attempt、script source version、artifact version。
6. `用户审阅`：待审阅、已确认、已驳回、过期、冲突。
7. `更新`：最新 artifact 或接入时间，并提供可理解的完整时间。

### 4.3 实现 Toolbar 与导航

1. 支持按 episode/title/series 搜索，以及 canonical 状态、问题类型、active/历史版本筛选。
2. 筛选条件可反映到 URL 或可恢复页面状态，返回列表时保持上下文。
3. 默认摘要行；点击或键盘激活进入详情，展开行为不得改变 artifact version 选择。
4. 不添加“手动新建剧本”按钮。

### 4.4 冲突与视觉表达

1. artifact version conflict 行使用既有错误语义 token、文本和图标，并可展开并列来源。
2. 时长差异使用警告语义 token，始终并列各来源值；warning/block 等级来自服务端规则结果。
3. 遵循暖纸背景、少面板、行分隔、高密度可扫描；只有 hover 可用轻阴影。
4. 状态变化用 `aria-live` 或等价可访问文本，颜色不是唯一信息载体。

### 4.5 大数据与状态边界

1. 使用项目基线的分页/虚拟化/排序能力，不在本任务另建通用数据表框架。
2. loading、empty、error 与 stale 数据须有稳定 row/region，避免筛选和刷新造成选中版本漂移。
3. 服务端返回未知状态时显示安全的“未知/需检查”，不默认放行或归类为通过。

## 5. 涉及文件路径

### 允许新增或修改

```text
frontend/src/components/story-workspace/episode/StoryWorkspaceEpisodeListTable.tsx
frontend/src/components/story-workspace/episode/StoryWorkspaceEpisodeListToolbar.tsx
frontend/src/components/story-workspace/episode/*EpisodeList*.test.tsx
frontend/src/hooks/story-workspace/*episode-list*
```

### 禁止修改

- `docs/design/`、`docs/issue/`、`docs/stage/`、`docs/exec/` 与其他 task 合同。
- 后端投影/Gate、通用表格基线、Sidebar 或 Dream shell。
- 复杂画布、节点拖拽、视频/模型选择、手工新建故事入口。

## 6. 输入 / 输出说明

### 输入

`StoryWorkspaceEpisodeProjection` 摘要列表，包括 episode identity、artifact completeness、四类时长、Agent findings、run/attempt/version、user review、diagnostics 与 timestamps。

### 输出

| 输出 | 内容 |
|---|---|
| 表格行 | 七组列和可访问状态文本 |
| 筛选状态 | query/status/problem/version 条件 |
| 选择事件 | 明确 episode ID + run + attempt + artifact version |
| 冲突展开 | 不一致来源值、诊断类型与阻断/警告级别 |

## 7. 依赖项

| 依赖 | 要求 |
|---|---|
| `SUO-241-FE-001` | 提供页面容器、路由与选择上下文 |
| `SUO-241-BE-001` | 提供统一摘要、provenance 和 diagnostics；可用 fixture 并行 |
| `SUO-202c` 表格基线 | 复用排序、分页、空态与键盘交互，不全量重写 |

本任务完成后解锁 `SUO-241-FE-003`。

## 8. 测试策略

1. **列合同测试**：七组列对完整、缺失、未知与历史版本数据均正确渲染。
2. **筛选测试**：搜索、状态、问题、版本组合筛选及 URL/返回恢复。
3. **冲突样本测试**：EP01 版本冲突红色语义且并列 source values；多源时长黄色语义且数值不被覆盖。
4. **状态分离测试**：Agent PASS + user pending、source draft + user confirmed 等组合不被错误合并。
5. **交互测试**：鼠标与键盘选择均传递完整版本上下文；刷新/排序后不误选其他行。
6. **视觉/可访问性测试**：1280px 无关键列遮挡，focus 可见，状态具文本/图标/aria 表达。

## 9. 完成标志

- [ ] 表格包含全部七组设计列与轻量 Toolbar。
- [ ] 搜索、状态、问题和版本筛选可组合且可恢复。
- [ ] artifact 冲突和时长差异均并列显示来源值。
- [ ] Agent/source/user/execution 状态不会混淆。
- [ ] 行选择绑定明确 run/attempt/artifact version。
- [ ] 无手工新建按钮、Canvas、视频或模型选择控件。
- [ ] UI v2、高密度扫描、键盘与读屏测试通过。

## 10. 风险提示

| 风险 | 处理 / 回滚 |
|---|---|
| 列过多导致中栏拥挤 | 以紧凑摘要、可控横向滚动/列优先级处理，不改变三栏宽度 |
| `[CLARIFICATION_NEEDED] 时长差异阈值` | **Owner：产品 owner**；只展示服务端规则结果，默认按百分比差异，不在 UI 硬编码阈值 |
| required artifacts 未来变化 | 根据 projection 的 required/optional 标记渲染，不写死 Gate 结论 |
| 前端自行推导授权 | 表格只展示 diagnostics；确认授权继续由服务端 Gate 决定 |
| 回滚丢失列表入口 | 保留基线数据表与 Dream 页面；增量组件可退回为只读摘要，不改变路由主入口 |

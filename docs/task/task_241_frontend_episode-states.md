# Task: Story Workspace Episodes 页面状态组件集（Frontend）

> **Task ID**: `task_241_frontend_episode-states`  
> **关联 Issue**: `SUO-241-FE-005` — Episodes 页面状态组件集  
> **Paperclip task**: [SUO-246](/SUO/issues/SUO-246)  
> **父需求**: [SUO-198](/SUO/issues/SUO-198)  
> **Domain / 优先级**: `frontend` / `P1`  
> **设计决策**: `DEC-021`, `DEC-023`, `DEC-024`  
> **生成依据**: `TASK-REQUIREMENT-FORMAT.md` 已填充提示词、设计稿 §6.1 / §7.2

## 1. 任务标题

实现 Episodes 工作空间的空态、提交态、校验态、不完整态、冲突态、过期态与再次生成态组件。

## 2. 关联 Issue

| Issue | 关系 | 本任务承接内容 |
|---|---|---|
| `SUO-241-FE-005` | 直接来源 | 七类 episodes 专属状态与恢复动作 |
| `SUO-201-FE-006` | 稳定基线 | 通用 loading/error/empty 状态组件 |
| `SUO-241-FE-001` | 前置 | 页面容器、run 状态与 Composer |
| `SUO-241-BE-001/003` | 数据合同 | completeness/conflict diagnostics 与 Gate 状态 |

标签：`state`、`ui`、`episode-states`、`delta`。

## 3. 任务目标

把服务端 canonical run/review 状态和 episodes diagnostics 投影为一致、可恢复、可访问的页面状态。组件只能解释和展示权威状态，不新造第二套后端事实；尤其不能因为本地 loading、关闭面板或路由变化而改变 Gate。

## 4. 实现步骤

### 4.1 建立状态映射适配器

1. 从 canonical run/review/execution status、active attempt、completeness、conflict diagnostics 与 stale 标记派生唯一页面状态。
2. 规定优先级，避免同一时刻多个全页状态竞争；局部已到达内容仍可读时使用局部状态区而非清空页面。
3. 未知状态安全降级为“需要检查”，确认/继续保持锁定。

### 4.2 实现七个状态组件

1. `StoryWorkspaceEpisodeEmptyState`：无投影且无活动 run；突出简单描述和将生成的产物说明。
2. `StoryWorkspaceEpisodeInputSubmittingState`：run 创建中；输入/Deck 上下文暂时只读，提交按钮 loading、防重复。
3. `StoryWorkspaceEpisodeOutputValidatingState`：文件已到达但解析/一致性校验未完成；已完成区域可读，明确“不可审阅”。
4. `StoryWorkspaceEpisodeMetadataIncompleteState`：列出缺失 required artifact/字段及来源；提供退回 Agent / 再次生成，不提供确认。
5. `StoryWorkspaceEpisodeArtifactVersionConflictState`：并列身份、版本、数量、hash 或时长冲突来源；禁止自动选值。
6. `StoryWorkspaceEpisodeStaleReviewState`：旧内容只读，显示新 run/attempt/version 与“切换最新版本”。
7. `StoryWorkspaceEpisodeRegeneratingState`：新旧 attempt 并列，新版本进度与旧审计都可访问。

### 4.3 冻结恢复动作语义

1. “重试”沿用同一失败阶段/允许的原版本语义，不把它包装成新生成。
2. “再次生成”创建不可变新 run/attempt/version，并携带原始描述与补充意见。
3. “切换最新版本”只切换审阅上下文，不继承旧确认或未提交编辑。
4. 所有动作以服务端 available actions 为准；按钮可见性不能成为授权事实。

### 4.4 视觉与可访问性

1. 复用 UI v2 暖纸、既有语义 token、少面板与小面积强调；不新增孤立色值。
2. 每个状态提供标题、原因、影响、下一动作和可选技术详情，不只显示图标/颜色。
3. 状态切换通过 `aria-live`，按钮有可见 focus；动画遵循 reduced-motion。
4. 不引入视频预览、Canvas 或移动端专属状态。

## 5. 涉及文件路径

### 允许新增或修改

```text
frontend/src/components/story-workspace/episode/state/
frontend/src/components/story-workspace/episode/state/*.test.tsx
frontend/src/hooks/story-workspace/*episode-state*
```

### 禁止修改

- `docs/design/`、`docs/issue/`、`docs/stage/`、`docs/exec/` 与其他 task 合同。
- 后端 canonical 状态机、Gate 判定、通用状态基线的非增量行为。
- Canvas、视频、模型选择/计费、移动端或平板端能力。

## 6. 输入 / 输出说明

### 输入

`storyWorkspaceRunId`、attempt、canonical run/review/execution status、artifact arrival/validation、required completeness、conflict diagnostics、active artifact version 与 available actions。

### 输出

| 输出 | 内容 |
|---|---|
| 状态视图 | 七种 episodes 专属组件及原因/影响/动作 |
| 恢复事件 | retry、regenerate、switch-latest 的明确 payload |
| 可访问通知 | 状态、错误与恢复结果的 live region 文本 |

## 7. 依赖项

| 依赖 | 要求 |
|---|---|
| `SUO-201-FE-006` | 复用通用状态、错误与 loading 基线 |
| `SUO-241-FE-001` | 提供页面容器、Composer 与当前 run 上下文 |
| `SUO-241-BE-001/003` | 提供 completeness/conflict/Gate diagnostics；可用 fixture 并行 |

可与 `SUO-241-FE-002` 并行，最终由 shared tasks 验证状态链。

## 8. 测试策略

1. **映射表驱动测试**：每个 canonical 状态/diagnostic 组合只落到预期状态。
2. **组件测试**：七个组件的标题、原因、缺失/冲突来源和动作可见性。
3. **恢复语义测试**：retry 不建新版本，regenerate 建新 attempt，switch-latest 不继承旧确认。
4. **部分产出测试**：output-validating 保留已到达内容并锁定审阅。
5. **未知状态测试**：安全降级且确认/继续不可用。
6. **视觉/可访问性测试**：语义 token、文本+图标、focus、live region、reduced-motion。
7. **范围回归**：状态组件无 Canvas、视频或移动端分支。

## 9. 完成标志

- [ ] 七个指定状态组件和唯一状态映射已实现。
- [ ] UI 状态只投影 canonical facts，不另建持久状态。
- [ ] retry、regenerate、switch-latest 语义清晰且 payload 不混淆。
- [ ] conflict/incomplete/stale/unknown 均保持确认与继续锁定。
- [ ] 状态具原因、影响、动作、文本/图标/aria 表达。
- [ ] 组件和状态映射测试通过。
- [ ] 未引入 Canvas、视频、模型计费或移动端能力。

## 10. 风险提示

| 风险 | 处理 / 回滚 |
|---|---|
| 多状态并发导致 UI 抖动 | 冻结优先级与局部/全页边界，用表驱动映射测试 |
| UI 与后端状态枚举漂移 | 未知值 fail closed；通过共享类型/契约测试暴露差异 |
| retry 与 regenerate 文案混淆 | 每个动作明确是否创建新 attempt/version，并显示目标 run |
| 视觉状态仅靠颜色 | 强制文本、图标、aria 和 focus 验收 |
| 回滚丢失恢复路径 | 降级为基线错误/只读状态，服务端 Gate 继续锁定，不清理历史 |


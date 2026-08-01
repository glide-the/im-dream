# Task: Dream 页面 Episodes 工作空间骨架（Frontend）

> **Task ID**: `task_241_frontend_episode-workspace`  
> **关联 Issue**: `SUO-241-FE-001` — Dream 页面 Episodes 工作空间骨架  
> **Paperclip task**: [SUO-246](/SUO/issues/SUO-246)  
> **父需求**: [SUO-198](/SUO/issues/SUO-198)  
> **Domain / 优先级**: `frontend` / `P0`  
> **设计决策**: `DEC-017`, `DEC-020`, `DEC-025`  
> **生成依据**: `TASK-REQUIREMENT-FORMAT.md` 已填充提示词、设计稿 §5.1 / §5.2 / §7.1

## 1. 任务标题

在 canonical Dream 入口内实现 Episodes 工作空间页面骨架、简单描述入口、运行进度与三栏组合关系。

## 2. 关联 Issue

| Issue | 关系 | 本任务承接内容 |
|---|---|---|
| `SUO-241-FE-001` | 直接来源 | Episodes 页面、Prompt Composer、运行进度、路由与布局 |
| `SUO-230-FE-002` | 稳定基线 | Dream 页面、ReviewGate 与 240 / auto / 360 三栏 |
| `SUO-241-BE-001` | 数据合同 | `StoryWorkspaceEpisodeProjection` |
| `SUO-241-BE-002` | 数据合同 | run/attempt 与运行记录查询 |

标签：`layout`、`episode-workspace`、`dream-page`、`delta`。

## 3. 任务目标

将简单描述、Agent 运行状态、ReviewGate、分集列表/详情和右侧审阅区组合到同一个 Dream 工作空间。用户从参考 episodes 或简单描述进入时看到同一页面骨架和投影语义，不产生独立的“导入页”或第二套审阅流。

页面仅面向桌面端（≥1280px），沿用 240px / 自适应 / 360px 三栏；不新增第二层顶部栏，不实现复杂画布、视频能力或手工从零新建故事。

## 4. 实现步骤

### 4.1 接入 canonical 路由

1. 在 `/story-workspace/dream` 中组合 Episodes 工作区，提供 `/story-workspace/episodes` 列表、`/story-workspace/episodes/:storyWorkspaceEpisodeId` 详情和 `/review` 审阅深链。
2. 路由参数、query、组件和状态均使用 `storyWorkspace` / `story-workspace` 前缀。
3. 深链加载时恢复选中的 episode、active run/attempt/artifact version；找不到或无权限时进入规范错误/空态。

### 4.2 实现 `StoryWorkspacePromptComposer`

1. 输入题材、剧情或修改意图，并显示已选择的 Deck workflow/release/runtime 上下文摘要。
2. Deck 插件未选、Deck 运行配置不完整、runtime preflight 未通过或请求正在提交时禁用“交给 Agent”。
3. 提交只创建 run，不在客户端伪造 episode；成功后以服务端 `storyWorkspaceRunId` 进入运行态。
4. Composer 是创作意图入口，不提供“手动新建剧本”、模型选择、积分计费或视频生成控件。

### 4.3 组合三栏与中栏顺序

1. 左栏复用 `StoryWorkspaceSidebar`，保持 Dream 选中态及 240px 基线。
2. 中栏按“简单描述 → ReviewGate → 分集列表或详情”排列，自适应占满剩余宽度。
3. 右栏固定 360px，审阅当前 episode / artifact version；关闭右栏只影响可见性，不写 Gate 状态。
4. 页面级最多一条 Border Paper 虚线，以留白、字号和行分隔组织内容，不堆叠卡片。

### 4.4 展示运行进度

1. 显示当前 `storyWorkspaceRunId`、attempt、canonical status、当前步骤和已到达 artifact kinds。
2. queued/running、output-validating、pending-review、confirmed、continuing/failed 等均消费服务端 canonical 状态。
3. 刷新、深链、关闭右栏后重新拉取服务端状态，不依赖组件本地状态恢复授权事实。

### 4.5 接口与并行开发边界

1. 用 typed adapter 连接 run、projection 与 Gate API；后端未就绪时使用固定 fixture/mock，并标明与真实合同的替换点。
2. 列表、详情、审阅和状态子组件由后续 frontend tasks 实现；本任务只提供插槽、路由、选择上下文与组合状态。
3. loading/error/empty fallback 先复用基线组件，不复制 `SUO-241-FE-005` 的 episodes 专属状态实现。

## 5. 涉及文件路径

### 允许新增或修改

```text
frontend/src/pages/story-workspace/StoryWorkspaceEpisodeWorkspacePage.tsx
frontend/src/components/story-workspace/episode/StoryWorkspacePromptComposer.tsx
frontend/src/components/story-workspace/episode/StoryWorkspaceEpisodeRunProgress.tsx
frontend/src/router/story-workspace.tsx
frontend/src/hooks/story-workspace/*episode*
frontend/src/services/story-workspace/*episode*
frontend/src/pages/story-workspace/__tests__/*episode*
```

### 禁止修改

- `docs/design/`、`docs/issue/`、`docs/stage/`、`docs/exec/` 与其他 task 合同。
- 后端、Deck 插件内部 workflow、已有 Dashboard 统计语义。
- 复杂 Canvas/节点拖拽、视频预览/上传/生成/播放器、模型选择/计费。
- 移动端或平板端布局、用户手工从零创建故事。

## 6. 输入 / 输出说明

### 输入

| 输入 | 内容 |
|---|---|
| 路由 | episode ID、review 深链、可选 run/attempt 上下文 |
| Composer | 描述文本、Deck workflow/release/runtime snapshot 引用 |
| 服务端 | run progress、episode projection 摘要、Gate aggregate |

### 输出

| 输出 | 内容 |
|---|---|
| 页面上下文 | 当前 episode、run、attempt、artifact version、右栏开合状态 |
| 创建 run 请求 | 描述摘要 + 锁定的 Deck 上下文引用 |
| 子组件插槽 | ReviewGate、EpisodeList/Detail、EpisodeReviewPanel、状态区 |
| 可导航 URL | 列表、详情与 review 深链 |

## 7. 依赖项

| 依赖 | 类型 / 说明 |
|---|---|
| `SUO-230-FE-002` | 硬依赖：Dream canonical 页面与 ReviewGate 基线 |
| `SUO-241-BE-001` | 联调依赖：投影合同；可用冻结 fixture 并行 |
| `SUO-241-BE-002` | 联调依赖：run/attempt 查询；可用 typed mock 并行 |
| Deck runtime preflight 基线 | 提交前校验并锁定 `deck_runtime_snapshot_id` 与上下文脱敏摘要 |

本任务完成后解锁 `SUO-241-FE-002` 与 `SUO-241-FE-005`。

## 8. 测试策略

1. **路由测试**：列表、详情、review 深链及刷新恢复当前选择。
2. **Composer 测试**：有效提交、空输入、缺 Deck、Deck 运行配置不完整、重复提交与服务端失败。
3. **布局测试**：1280px 及常见更宽桌面视口下保持 240 / auto / 360；无第二层顶部栏。
4. **状态恢复测试**：关闭右栏、刷新、前进/后退不改变服务端 Gate 事实。
5. **可访问性测试**：输入 label、禁用原因、loading `aria-live`、可见 focus 与键盘导航。
6. **范围回归**：页面无 Canvas、拖拽、视频或手工创建入口。

## 9. 完成标志

- [ ] Episodes 工作区已接入 Dream canonical 页面与三条规范路由。
- [ ] Prompt Composer 能创建 run，且 preflight 不完整时不可提交。
- [ ] 页面显示 run ID、attempt、步骤和 artifact 到达进度。
- [ ] 中栏和右栏组合符合 240 / auto / 360；关闭右栏不改变 Gate。
- [ ] 刷新与深链从服务端恢复选择和 canonical 状态。
- [ ] 所有新增名称遵循 `story-workspace` 前缀。
- [ ] 桌面布局、路由、交互与可访问性测试通过。
- [ ] 未出现 Canvas、视频、模型计费或手工新建故事能力。

## 10. 风险提示

| 风险 | 处理 / 回滚 |
|---|---|
| 与 `StoryWorkspaceDreamPage` 基线重复布局 | 以组合/子区域扩展，不新建平行 Dream shell |
| 后端合同未就绪造成接口漂移 | 先冻结 typed fixture；联调前以 `SUO-241-BE-001/002` 合同替换并跑契约测试 |
| UI 本地状态误当 Gate 权威 | 每次确认/继续前由服务端重验；刷新重新读取 canonical 状态 |
| 窄桌面空间不足 | 本期最低 1280px；保持中栏最小宽度和可控溢出，不扩展到移动端 |
| 回滚破坏既有 Dream | Episodes 入口受可逆路由/能力开关保护；回滚仅移除增量组合，不改基线页面 |

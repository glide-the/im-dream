# Dream Surface Task 4 实施记录（审阅面板跳转按钮 + Chat guidance 过滤前置 + Dream 页 `?run=` 深链定位）

> 依据：`2026-08-03-dream-surface-execution-implementation-plan.md` Task 4 全节（Step 0–Step 6，含 2026-08-03 C9 兼容性修订与复核批注 R2）；设计语义以 design_004 §4（§4.1 可见条件、§4.2 六态文案、§4.3 深链、§4.4 异常态）为准
> 日期：2026-08-04

## 任务范围

1. **Step 0（前置，DEC-032）**：Chat 视图按 `metadata.kind === "story-workspace-guidance"` 过滤 guidance 消息，保证 Task 3 落库的指导行不出现在 Chat 气泡中。
2. **Step 1–4**：`StoryWorkspaceSurfaceLinkButton`（审阅面板侧，C9 修订后挂载点）——六态文案全部由服务端聚合 props 驱动，前端不推断；显隐条件与 supersede 降级按 §4.1/§4.4。
3. **Step 5（R2）**：Dream 页 `?run=` 深链定位——Dream 页局部 `URLSearchParams` 解析（Task 5 Step 0 统一收编至 router）；run 属于当前用户→设为初始选中 run；不存在/无权→提示并回退默认；只做初始定位不冻结选中。

## 测试设施现实（沿用 Task 2 先例）

无 vitest/@testing-library；采用 **Playwright test runner 的 Node 侧模式**（不取 `page` fixture、不起浏览器）跑合同测试。新增一处现实适配：Playwright 的 JSX 运行时（`__pw_type` 包装）与 `react-dom/server.renderToStaticMarkup` 不兼容，组件渲染冒烟降级为「直接调用函数组件断言 null/非 null 边界」，文案/href 语义全部由纯解析 seam（`resolveStoryWorkspaceSurfaceLink`）覆盖——与 Task 2「测 seam 不测渲染」的先例一致。

## TDD 过程摘要（Red → Green，三轮）

| 轮次 | 测试文件 | Red | Green |
|------|----------|-----|-------|
| Step 0 guidance 过滤 | `frontend/src/lib/__tests__/story-workspace-guidance.test.ts`（5 例：kind 常量、审计字段全量识别、畸形 metadata 拒绝、过滤保序、空表/原数组不变） | `Cannot find module '../story-workspace-guidance'`（No tests found） | ✅ 5 passed |
| Step 1–4 跳转按钮 | `frontend/src/components/story-workspace/__tests__/StoryWorkspaceSurfaceLinkButton.test.tsx`（14 例：六态文案×目标路由、episodeId 缺失退化、URL 编码、无 surface/无 runId/无聚合态隐藏、supersede 两种降级、组件 null 边界） | `Cannot find module '../StoryWorkspaceSurfaceLinkButton'`（No tests found） | ✅ 14 passed |
| Step 5 深链 | `frontend/src/hooks/story-workspace/__tests__/useRunDeepLink.test.ts`（5 例：query 解析/空白值、无参零请求、属主 run 解析、404/403/空 payload 降级） | `Cannot find module '../useRunDeepLink'`（No tests found） | ✅ 5 passed |

按钮轮中途一次真实环境修复：初版渲染冒烟用 `renderToStaticMarkup` 撞 Playwright JSX 运行时（见上节），改测 seam + null 边界后通过；随后 eslint `react-refresh/only-export-components` 拦截组件文件导出常量/函数，将纯 seam 拆至 `surfaceLink.ts`（组件文件只留 JSX 薄包装），测试相应改引。

## 测试运行输出

```
npx playwright test src/ --reporter=line
  35 passed (451ms)     # 11（Task 2 存量）+ 5 + 14 + 5
npx tsc -b              → exit 0
npx eslint <本 Task 全部改动文件>  → exit 0
（基线说明：npx eslint src/ 全量在 HEAD 上既有 69 errors/20 warnings，
  已用 git stash 验证与本次改动无关；本 Task 改动文件全部零告警。）
```

## 六态文案与服务端聚合 props 的对接说明（PLAN 降级处理）

**六态文案（design_004 §4.2 逐字）**：`SURFACE_LINK_LABELS`（`frontend/src/components/story-workspace/surfaceLink.ts`）——`pending_review`「前往 Dream 审阅」→ 审阅深链；`confirmed`「进入后续执行」/`continuing`「查看执行进度」/`completed`「查看执行结果」/`failed`「查看失败详情」→ 执行页深链；`rejected`「查看审阅记录」→ 审阅深链（只读语义由目标页承载）。

**聚合 props 合同（DEC-026）**：`StoryWorkspaceSurfaceLinkStage`（六态枚举）与 `StoryWorkspaceSurfaceLinkState`（`{stage, superseded?, latestRunId?}`）只归 `frontend/src/hooks/story-workspace/contracts.ts`。按钮 props：`{surfaces, runId, episodeId?, state}`。

**服务端聚合端点尚缺的降级**（关键偏差说明）：代码现实中 ①审阅资源（`StoryWorkspaceReviewResource`）不绑定 `workflow_run_id`；②不存在「提案 review 状态 + run 状态」的服务端聚合端点；③attempt/supersede 语义（`retryOfRunId` 关联）服务端合同已备（Task 3 记录）但提案侧无透出。按 PLAN「状态全部来自服务端聚合 props，前端不推断」与 §4.1 可见条件，前端处理为：

- 按钮组件**只做 props → 渲染的纯映射**；`state`（聚合态）为 `null/undefined` 时一律隐藏，绝不由前端从本地数据推断阶段；
- 两个挂载点只定义**可选注入缝**：`StoryWorkspaceReviewDetail` 新增可选 prop `surfaceLink: {runId, episodeId?, state}`（surfaces 经 `useWorkspaceSurfaces(sourceReceipt?.chat_thread_id)` 解析，且仅在 `surfaceLink.runId && surfaceLink.state` 齐备时才发起 receipt 请求）；`StoryWorkspaceStoryTable` 新增可选 `surfaceLinkForStory` 行级回调。当前无调用方传入 → 按钮默认隐藏，与「聚合端点就位前无入口」的安全缺省一致（DEC-028 同构）；端点/绑定就位后数据沿既有 props 链直接流入，组件零改动。

**显隐条件（§4.1，三者同时满足，否则 `resolveStoryWorkspaceSurfaceLink` 返回 undefined）**：①`surfaces` 含 `name="dream"`；②`runId` 非空；③聚合 `state` 存在。supersede 不隐藏而降级（§4.1 括号/§4.4）。

**supersede 降级（§4.1/§4.4）**：`superseded=true` 且 `latestRunId` 指向另一 run → 主链接「查看最新版本」跳最新 run 审阅深链 + 次链接「查看运行记录」跳本 run 执行页；无 `latestRunId`（或等于本 run）→ 仅「查看运行记录」单链接。

**深链目标（§4.2/§4.4）**：审阅深链 `/story-workspace/episodes/:episodeId/review?run=:runId`，episodeId 缺失退化为 `{entry_route}?run=:runId`（`entry_route` 取服务端透出值，当前恒为 `/story-workspace/dream`）；执行页深链 `/story-workspace/runs/:runId/execution`；path/query 段均 `encodeURIComponent`。

## Step 0 落点（Chat guidance 过滤）

- 新增 `frontend/src/lib/story-workspace-guidance.ts`：`STORY_WORKSPACE_GUIDANCE_KIND`、`isStoryWorkspaceGuidanceMetadata`、`filterStoryWorkspaceGuidanceMessages`（保序、不改原数组）。
- `ChatView.tsx` `fetchThreadMessages`（:353 附近，PLAN 指认落点）：历史消息加载后映射即过滤。
- `ChatPanel.tsx`：新增 `visibleMessages = useMemo(filter…)`，渲染（`ChatMessageList`）、分享导出快照（`messagesForExportRef`）、`shouldShowMessageSurface`、`pendingConfirmation` 推导、loading 指示器全部改消费 `visibleMessages`；`useChat` 原始列表仅保留在发送/滚动依赖等不改变渲染语义的用途。SSE 直播路径（`applyBackendEventToMessages`）若回显 guidance user turn 同样被渲染缝兜住。

## Step 5 落点（`?run=` 深链，R2）

- 新增 `frontend/src/hooks/story-workspace/useRunDeepLink.ts`：`parseRunDeepLinkParam`（局部 `URLSearchParams`，Task 5 Step 0 统一收编至 router）、`resolveRunDeepLink`（复用既有 actor 范围读 `getWorkflowRun`：成功=属主→`resolved`；404/403/异常/空 payload→`missing`）、`useRunDeepLink(enabled)`（每挂载仅解析一次——初始定位不冻结选中）。
- 接线落点为 **`StoryWorkspaceRouter`** 而非 `StoryWorkspaceDreamPage`（偏差 2，见下节）：enabled 门控 `activeRoute === 'dream'`；解析成功→经既有 `StoryWorkspaceLayout.workflowContext`（`WorkflowContextBar`，此前无调用方接线）展示选中 run 的 `status/deck 名版本/runId/summary`；`missing`→`role="status"` 可关闭提示「链接指向的运行 … 不存在或无权查看，已回退到默认视图」。无 `?run=` 时 hook 惰性，现状零变化。
- `replaceWithCanonicalPath` 用 `URL` 对象仅改 pathname，天然保留 `?run=`；导航 `pushState` 场景按 R2 留给 Task 5。

## 与 PLAN 的偏差（均按代码现实调整，语义不变）

1. **服务端聚合端点缺位 → props 注入缝 + 默认隐藏**：见「六态文案与服务端聚合 props 的对接说明」。PLAN 测试示例的 `renderReviewDetail({selection, surfaces})` 渲染形态在 Node 侧设施下不存在，六态/显隐/supersede 断言语义全部平移至 `resolveStoryWorkspaceSurfaceLink` seam 测试并保有超集（URL 编码、episodeId 缺失、latestRunId 自指、聚合态缺位隐藏）。
2. **Step 5 落点**：PLAN 写「Dream 页 `StoryWorkspaceDreamPage.tsx`（`?run=` 定位逻辑）」；代码现实 Dream 页为无状态 children 包装，无法承载定位状态/提示/选中 run 展示，落点改为渲染 Dream 页的 `StoryWorkspaceRouter`（PLAN Files 亦列其为相邻路由模块）。「替代默认最新 run」中的「默认最新 run 加载」在代码中不存在（`WorkflowContextBar` 此前无接线方），故深链语义实现为「有 `?run=` → 选中该 run 展示；无 → 维持现状默认」，不引入 PLAN 外的「默认最新 run」加载行为。
3. **组件文件拆分**：eslint `react-refresh/only-export-components` 要求组件文件不导出常量/函数，纯 seam（`SURFACE_LINK_LABELS`/深链构建器/`resolveStoryWorkspaceSurfaceLink`/类型）落于新文件 `frontend/src/components/story-workspace/surfaceLink.ts`，`StoryWorkspaceSurfaceLinkButton.tsx` 仅余 JSX 薄包装；测试文件路径与 PLAN 一致。
4. **渲染冒烟降级**：Playwright Node 侧 JSX 运行时与 `react-dom/server` 不兼容，组件渲染测试限于 null/非 null 边界（详见「测试设施现实」）。
5. **toast 形态**：代码库无统一 toast 组件（既有为 ad-hoc DOM toast），采用 `role="status"` 内联可关闭提示条（React 态、可测试），语义与 PLAN「toast 提示并回退默认」一致。
6. **样式**：新增 `.story-workspace-surface-link*` 与 `.story-workspace-deep-link-notice` 少量 CSS（归 `StoryWorkspaceLayout.css`，沿用既有 token），PLAN Files 未列样式文件。

## 给 Task 5 / 后续任务的接口说明

- **执行页路由生成**：`storyWorkspaceExecutionDeepLink(runId)` / `storyWorkspaceReviewDeepLink(runId, episodeId?, entryRoute?)`（`surfaceLink.ts`）即 §4.2 两类深链的唯一构建器；Task 5 路由参数化（C10）收编后请保持这两者的输出与 router 匹配规则一致。
- **query 解析收编**：`parseRunDeepLinkParam` 为 Task 4 R2 的局部实现；Task 5 Step 0 统一至 router 时直接替换 `useRunDeepLink` 内部调用点即可（seam 测试可平移）。
- **聚合 props 注入**：服务端「提案↔run 绑定 + 阶段聚合」就位后，向 `StoryWorkspaceReviewDetail.surfaceLink` / `StoryWorkspaceStoryTable.surfaceLinkForStory` 注入 `{runId, episodeId?, state}` 即可点亮两处按钮，组件与解析逻辑零改动。
- **guidance 反查**：Task 5 侧边栏按 `metadata.kind === "story-workspace-guidance"` 反查历史时复用 `isStoryWorkspaceGuidanceMetadata`（注意不要再用 `filterStoryWorkspaceGuidanceMessages` 反滤）。

## 变更文件清单（commit 范围）

- `frontend/src/lib/story-workspace-guidance.ts`（新增）
- `frontend/src/lib/__tests__/story-workspace-guidance.test.ts`（新增）
- `frontend/src/components/chat/ChatView.tsx`（历史加载过滤）
- `frontend/src/components/chat/ChatPanel.tsx`（渲染/导出缝过滤）
- `frontend/src/hooks/story-workspace/contracts.ts`（+`StoryWorkspaceSurfaceLinkStage`、`StoryWorkspaceSurfaceLinkState`，DEC-026）
- `frontend/src/hooks/story-workspace/useRunDeepLink.ts`（新增）
- `frontend/src/hooks/story-workspace/index.ts`（barrel：深链 hook + 新合同类型）
- `frontend/src/hooks/story-workspace/__tests__/useRunDeepLink.test.ts`（新增）
- `frontend/src/components/story-workspace/surfaceLink.ts`（新增，纯 seam）
- `frontend/src/components/story-workspace/StoryWorkspaceSurfaceLinkButton.tsx`（新增，组件薄包装）
- `frontend/src/components/story-workspace/__tests__/StoryWorkspaceSurfaceLinkButton.test.tsx`（新增）
- `frontend/src/components/story-workspace/index.ts`（barrel 导出）
- `frontend/src/components/story-workspace/layout/StoryWorkspaceReviewDetail.tsx`（提案详情区挂载点）
- `frontend/src/components/story-workspace/layout/StoryWorkspaceLayout.css`（按钮/提示条样式）
- `frontend/src/components/story-workspace/table/StoryWorkspaceStoryTable.tsx`（故事列表行操作列挂载点）
- `frontend/src/router/story-workspace.tsx`（深链接线 + workflowContext + 提示条）
- `docs/design/story-workspace/2026-08-04-dream-surface-task4-implementation-record.md`（本文件）

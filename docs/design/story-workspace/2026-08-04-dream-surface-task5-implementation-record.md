# Dream Surface Task 5 实施记录（独立执行页 + state router 参数化收编）

> 依据：`2026-08-03-dream-surface-execution-implementation-plan.md` Task 5 全节（Step 0 C10 前置 + Step 1–5）；设计语义以 design_004 §5（§5.1 DEC-030 布局、§5.2 只读数据层、§5.3 指导侧边栏、§5.4 五态、§5.5 Gate 重定向）为准
> 日期：2026-08-04

## 任务范围

1. **Step 0（前置 C10）**：state router 参数化——路由 union 扩展（`episode-review` / `run-execution`）、`:param` 分段匹配、`URLSearchParams` query 解析、`replaceWithCanonicalPath`/`pushState` 保留 query；**收编** Task 4 R2 的局部 `URLSearchParams` 解析（`parseRunDeepLinkParam` → router seam `parseStoryWorkspaceRunParam`/`readStoryWorkspaceRunParam`）；顺带处理 Task 4 评审两项遗留（见下）。
2. **Step 1–4**：独立执行页 `/story-workspace/runs/:storyWorkspaceRunId/execution`——五态 UI（§5.4）+ Gate 重定向（§5.5）+ DEC-030 布局（breadcrumb + 左只读数据层 Tabs[任务进度/资产/运行记录] + 右 360px `StoryWorkspaceGuidanceSidebar`）+ 指导侧边栏（预设动作 + 自由文本 + 幂等键 + `dispatched:false`「已记录待拾取」态 + 指导历史反查）。

## 测试设施现实（沿用 Task 2/4 先例）

Playwright test runner Node 侧模式（不取 `page` fixture、不起浏览器）。两处现实适配：

- **纯 seam 抽离**：路由匹配/状态解析/指导构造全部落于无 React/CSS 依赖的纯模块（`storyWorkspacePath.ts`、`executionState.ts`、`useStoryWorkspaceGuidance.ts` 的纯函数段），测试全覆盖；带 hook 的页面/侧边栏组件不测渲染（与 Task 4「测 seam 不测渲染」一致）。
- **Node 侧组件冒烟**：hook-free 叶子组件（`StoryWorkspaceExecutionProgressTable`/`StoryWorkspaceExecutionAssetPanel`）直接函数调用断言非 null（Task 4 null 边界先例）；带 hook 的 `StoryWorkspaceExecutionPage`/`StoryWorkspaceGuidanceSidebar` 不可直接调用（Invalid hook call），由 seam 测试承载其全部呈现决策。
- **新发现的环境约束（影响 seam 签名）**：`apiUrl()`（`lib/apiBase.ts`）在 Playwright Node 侧因 `import.meta.env` 未定义而抛错。沿用 Task 2 先例——fetch seam 一律接收**完整 endpoint 字符串参数**（`apiUrl()` 只在运行期边缘的 hook/组件层调用），seam 保持 Node 可测。

## TDD 过程摘要（Red → Green，三轮）

| 轮次 | 测试文件 | Red | Green |
|------|----------|-----|-------|
| Step 0 路由参数化 | `frontend/src/router/__tests__/storyWorkspacePath.test.ts`（9 例：静态路由零回归、run-execution/episode-review 参数匹配与解码、query 解析承载、部分/多余分段拒绝、pattern 字面段比较、canonical builder 与 Task 4 深链 builder 字节一致、`?run=` 统一 seam 平移） | `Cannot find module '../storyWorkspacePath'` | ✅ 9 passed |
| 五态 + 重定向 | `frontend/src/pages/story-workspace/__tests__/StoryWorkspaceExecutionPage.test.tsx`（7 例：六种未确认态 → not-confirmed、重定向目标含 run/episodeId 缺失降级、confirmed/continuing/completed/failed/cancelled 五态+取消终态、awaiting-guidance 投影推断三路径+非 continuing 不升级+无 projection 降级、PLAN 要求文案五连、guidable={continuing,failed}、叶子组件冒烟） | `Cannot find module '../../../components/story-workspace/executionState'` | ✅ 7 passed |
| 指导 seam | `frontend/src/hooks/story-workspace/__tests__/useStoryWorkspaceGuidance.test.ts`（11 例：free-text/retry-step payload 构造、自带幂等键、合同校验对齐拒绝、键唯一性与 ≤255、`dispatched:false`「已记录待拾取」/已发送/幂等去重三态文案、历史反查字段映射+畸形行跳过保序、POST transport 202/409 双错误码/网络异常） | `Cannot find module '../useStoryWorkspaceGuidance'` | ✅ 11 passed |
| 收编回归 | `useRunDeepLink.test.ts` 改写（parse 测试平移至 router 文件；resolve 改为直接收 runId 参数，3 例） | 签名变更后旧测试失败 | ✅ 3 passed |

中途一次真实环境修复：初版 fetch seam 内部直接 `apiUrl(path)`，Node 侧 `import.meta.env` 缺失抛 `TypeError`（2 例失败）；按 Task 2 先例改 seam 签名收完整 endpoint 后通过（见上节）。

## 测试运行输出

```
npx playwright test src/ --reporter=line
  59 passed (908ms)     # Task 2/4 存量 33 + 本 Task 26
npx tsc -b              → exit 0
npx eslint <本 Task 全部改动文件>  → exit 0（仅 CSS 文件 "ignored" 提示）
```

## Step 0 落点（C10 + Task 4 遗留处理）

**新增纯模块 `frontend/src/router/storyWorkspacePath.ts`**（无 React/CSS 依赖，Node 可测）：

- `StoryWorkspaceRoute` 扩展为 `'dream'|'stories'|'characters'|'scenes'|'episode-review'|'run-execution'`；`STORY_WORKSPACE_PATHS` 保持四静态路由（侧栏导航语义不变），参数化模板归 `STORY_WORKSPACE_ROUTE_PATTERNS`（`/story-workspace/episodes/:storyWorkspaceEpisodeId/review`、`/story-workspace/runs/:storyWorkspaceRunId/execution`）。
- `matchStoryWorkspaceRoutePattern`：前缀分段比较，`:param` 捕获单段并 URI 解码，段数不等/字面段不符 → null。
- `resolveStoryWorkspacePath(pathname, search?)`：返回 `{canonicalPath, route, params, query}`——query 恒为 `URLSearchParams`（C10-③）；静态路由行为与 C10 前完全一致（测试锁定零回归）。
- `storyWorkspaceExecutionPath`/`storyWorkspaceEpisodeReviewPath`：canonical builder，测试断言与 Task 4 `storyWorkspaceExecutionDeepLink` 字节一致（防两处发散）。
- `parseStoryWorkspaceRunParam`/`readStoryWorkspaceRunParam`：**收编** Task 4 R2 的局部 `?run=` 解析（语义逐字平移：空白/缺失 → null）。

**`story-workspace.tsx` 适配器**（唯一 choke point，保有全部 window/history 副作用）：

- `replaceWithCanonicalPath` 用 `URL` 对象仅改 pathname，天然保留 query（C10-④，Task 4 已具备，本 Task 注释锁定）；`handleNavigate`/`syncFromLocation` 改为 `resolveStoryWorkspacePath(pathname, search)` 且 pushState 目标 = `canonicalPath + search`（C10-⑤，深链 query 不再丢失）。
- 状态从 `activeRoute` 升级为完整 `activeMatch`（route + params + query）；`run-execution` 渲染 `StoryWorkspaceExecutionPage`（`key=runId` 切 run 重载），`episode-review` 渲染 Dream 工作区内容（审阅深链落点语义 = Dream 页 + `?run=` 初始定位）。
- DEC-030「AppHeader Dream 选中态」落点：执行页/episode-review 路由下侧栏 `currentPath` 恒为 `STORY_WORKSPACE_PATHS.dream`；执行页在 `StoryWorkspaceLayout` 内以 `reviewPanel=null` 渲染（不复用审阅右栏，满足「不嵌入 Dream 三栏」——右栏两种语义不混用）。
- **Task 4 遗留①（深链提示条切换路由不清除）**：`useRunDeepLink` 签名改为 `(enabled, runId)`，`enabled→false` 时清空 run 与 notice 并重置解析游标（回到 Dream 路由可重解析）；同时新增 `routeNotice` 通道承载 Gate 重定向提示（下述），两类提示条均可关闭。
- **Task 4 遗留②（按钮 `<a href>` 整页跳转）**：**适合换 router 导航，已换**。`StoryWorkspaceSurfaceLinkButtonProps` 新增可选 `onNavigate`；按钮拦截点击（meta/ctrl/shift/alt 修饰键保留原生新标签页语义），`StoryWorkspaceReviewDetail` 新增 `onSurfaceLinkNavigate` 透传，router 注入 `handleNavigate`。无 `onNavigate` 时保持纯 href 渐进增强（故事列表行挂载点 `surfaceLinkForStory` 目前无调用方传入——Task 4 记录的聚合端点缺位——该行保持 href 形态，数据就位后由调用方决定是否注入同一回调，组件零改动）。
- **收编落点**：router 以 `readStoryWorkspaceRunParam(activeMatch.query)` 喂 `useRunDeepLink`；hook 不再读 `window.location.search`。hooks barrel 移除 `parseRunDeepLinkParam` 导出（归 router seam）。

## 执行页落点（Step 1–4）

**合同（DEC-026，`frontend/src/hooks/story-workspace/contracts.ts`）**：`StoryWorkspaceGuidanceKind`、`StoryWorkspaceGuidanceCommandPayload`、`StoryWorkspaceGuidanceAccepted`、`StoryWorkspaceExecutionStep`/`StoryWorkspaceExecutionEvent`/`StoryWorkspaceExecutionProjection`（对齐 Task 3 后端合同）、`StoryWorkspaceExecutionPageState`、`StoryWorkspaceGuidanceHistoryEntry`。另在既有 API 客户端类型 `WorkflowRun`（`api/storyWorkspaceApi.ts`，非新业务合同）补 `source_voice_thread_id?: string | null`——后端 run read 自 SUO-198 起即透出该字段（`backend/services/workflow/run_service.py:933`），TS 类型此前漏收。

**状态 seam（`components/story-workspace/executionState.ts`）**：

- `resolveStoryWorkspaceExecutionState(run, projection?)`：页面可服务状态 = `{confirmed, continuing, completed, failed, cancelled}`；其余（preflight/queued/running/output_validating/pending_review/rejected）→ `not-confirmed`（§5.5）。`confirmed`（Gate 第四步刚过、执行未续行）渲染进度视图，归入 `continuing` 态。`awaiting-guidance` 投影推断：`continuing` +（`projection.phase==='awaiting-guidance'` 或任一步骤 `blocked:true`/`status:'blocked'`），非 continuing 永不升级（D13）。
- `cancelled` 处理（**设计缺口决策**）：§5.4 五态表未枚举 cancelled；它是 Gate 之后的终态，重定向审阅深链语义错误。决策为新增 `cancelled` 页面态（「已取消」终态提示，不重定向），已记录于此。
- `resolveStoryWorkspaceExecutionRedirect(runId, episodeId?)`：复用 Task 4 `storyWorkspaceReviewDeepLink` builder；**episodeId 缺口**——run read 无 episode 绑定（无提案↔run 聚合端点，同 Task 4 记录），执行页 `episodeId` 为可选注入缝，缺省降级为 `/story-workspace/dream?run=<id>`（§4.4 既定降级路径）。
- `STORY_WORKSPACE_EXECUTION_STATE_COPY`：五态+cancelled 徽章/横幅文案，含 PLAN 逐字要求（执行中/等待你的指导/执行完成/重试失败步骤/先完成审阅确认）。

**Gate 重定向（§5.5）**：页面 `state==='not-confirmed'` 时渲染空态+「请先完成审阅确认…正在跳转审阅」并 effect 触发 `onNavigate(审阅深链, notice)`；router `handleNavigate(path, notice?)` 第二参承载提示 → 落达页显示可关闭提示条（`routeNotice`），下次 location 同步清除。无 `onNavigate` 时退化 `window.location.assign`。

**页面与组件**：

- `StoryWorkspaceExecutionPage`：run 经既有 `getWorkflowRun` actor 范围读取（404/403 → 错误态，不重定向——「不存在/无权」与「未确认」是两种事实）；breadcrumb（Dream / Runs / `<runId>` / 执行）+ 状态徽章 + 横幅；左数据层 Tabs；右侧边栏；completed 态页脚「返回 Dream」深链。
- 数据层 Tabs（§5.2，只读，DEC-008，零写控件）：
  - **任务进度**（`StoryWorkspaceExecutionProgressTable`，hook-free）：步骤表（步骤/状态/耗时/失败原因/重试次数）；**projection 缺口降级**——run read 不返回步骤行（`read_run` 不填 `steps`）、无 projection 端点、SSE events 路由未注册，无投影时显示显式空态「暂无步骤数据…以 Chat 执行过程为准」+ run 级事实（current_step/failed_step/error_code）。
  - **资产**（`StoryWorkspaceExecutionAssetPanel`，hook-free）：`projection.assets_ref` 只读引用；无投影 → 空态 + 回 Dream 详情深链（router 导航）。无视频预览/上传/播放器、无可编辑图库（§5.1 取舍）。
  - **运行记录**：run 生命周期字段（创建/开始/完成）+ 指导历史条目合成的时间线（`transitions` 无 GET 端点，降级事实来源，页内只读拼接）。
- **指导侧边栏（`StoryWorkspaceGuidanceSidebar`，§5.3）**：
  - 预设动作：[重试失败步骤]（仅 `failed && failed_step` 可用，发 `retry-step` + `step_id=failed_step` + 输入框附言）与 [补充约束]（空输入框预填「补充约束：」并聚焦）；自由文本多行输入 + [发送指导]；`awaiting-guidance` 态自动聚焦输入框（主焦点，§5.4）。
  - 幂等键：`newStoryWorkspaceGuidanceIdempotencyKey()`（`swg_<uuid>`，≤255）；一次逻辑提交内复用 in-flight 键，重复点击走服务端 replay（202 `replayed:true`）路径；提交中禁用。
  - 提交结果呈现：`dispatched:true`→「指导已发送给执行 Agent」；**`dispatched:false`→「指导已记录，待执行 Agent 拾取（当前有进行中的回合）」（Task 3 评审遗留 R2，测试锁定逐字）**；`replayed:true`→幂等去重提示；409 双错误码（`WORKFLOW_RUN_NOT_GUIDABLE`/`IDEMPOTENCY_CONFLICT`）与 403 均有专属文案。
  - 指导历史（指令+状态+时间）：复用既有 `GET /api/claude-agent/threads/{thread_id}/messages`（threadId = run 的 `source_voice_thread_id`），`extractStoryWorkspaceGuidanceHistory` 按 `metadata.kind` 反查保留指导行（用 `isStoryWorkspaceGuidanceMetadata` 谓词，**不**用 Chat 视图的反滤函数——Task 4 交接说明）；审计字段（request_id/idempotency_key/command_kind/step_id/text_summary/created_at）齐全；任何失败降级空列表不破坏页面。页面级一次拉取，侧边栏与「运行记录」Tab 共享。
  - 客户端 guidable 门控（{continuing,failed}）只预禁用明显不可用情形；服务端保持权威（409 照常呈现）。

## 与 PLAN 的偏差（均按代码现实调整，语义不变）

1. **测试形态**：PLAN 示例的 `renderExecutionPage({run})` + `mockNavigate` 断言在 Node 侧设施下不存在；Gate 重定向/五态断言语义全部平移至 `resolveStoryWorkspaceExecutionState`/`resolveStoryWorkspaceExecutionRedirect` seam 测试（含超集：六未确认态枚举、cancelled、投影推断三路径、URL 编码）。组件渲染覆盖同 Task 4 降级为 hook-free 叶子直接调用冒烟。
2. **projection 数据缺口降级**（硬约束 2 允许并要求记录）：`StoryWorkspaceExecutionProjection` 无端点、run read 无 steps/transitions、SSE events 路由未注册。页面将 `projection` 设计为可选注入缝（默认 null），三处降级：进度表空态+run 级事实、资产空态+Dream 深链、运行记录改由 run 生命周期字段+指导历史合成；`awaiting-guidance` 在无投影时不出现（安全缺省）。端点就位后沿 props 注入即点亮，组件零改动。
3. **episodeId 缺口**：Gate 重定向的审阅深链无 episode 绑定可用，降级 §4.4 既定路径（Dream entry + `?run=`）；`episodeId` 留注入缝。
4. **cancelled 态**：§5.4 五态表外补第六态处理（见上「状态 seam」）。
5. **「AppHeader」落点**：代码库 story-workspace 视图无 AppHeader 组件（App.tsx 在该视图隐藏 TopNavBar），应用壳 = `StoryWorkspaceSidebar` 导航；DEC-030「AppHeader Dream 选中态」实现为执行页路由下侧栏恒选 Dream 项 + 页内 breadcrumb。
6. **fetch seam 签名**：`submitStoryWorkspaceGuidance(endpoint, …)`/`fetchStoryWorkspaceGuidanceHistory(endpoint, …)` 收完整 URL（`import.meta.env` Node 侧不可用，Task 2 先例）；`apiUrl()` 仅在 hook/组件运行期边缘调用。
7. **样式文件**：执行页 CSS 归入 `StoryWorkspaceLayout.css`（Task 4 先例，PLAN Files 未列样式文件）。
8. **测试文件路径**：`useRunDeepLink.test.ts` 中 parse 用例平移至 `src/router/__tests__/storyWorkspacePath.test.ts`（收编的自然结果）。

## 给 Task 6 e2e 的验收要点

1. **路由直开**：浏览器直开 `/story-workspace/runs/<run_id>/execution` → story-workspace 视图（此前落在 writing 视图）；直开 `/story-workspace/episodes/<ep>/review?run=<id>` → Dream 工作区 + run 定位。
2. **六态按钮链路**：审阅面板按钮点击为**无整页刷新**的 SPA 导航（修饰键点击仍可新标签打开）；confirmed/continuing/completed/failed 四态按钮 → 执行页渲染对应态。
3. **Gate 重定向**：pending_review/rejected 的 run 直开执行页 → 跳转审阅深链（无 episode 绑定时落 `/story-workspace/dream?run=<id>`）+ 可关闭提示「先完成审阅确认」+ run 定位（WorkflowContextBar）。
4. **指导闭环**：continuing/failed run 执行页 → 提交自由文本/重试失败步骤 → 202；线程忙时响应 `dispatched:false` → 侧边栏显示「已记录，待执行 Agent 拾取」；指导历史出现新条目（指令+状态+时间）；同幂等键重发 → replayed 提示；Chat 消息流无指导气泡（Task 4 Step 0 既有验收）。
5. **降级态**：无投影环境下进度/资产 Tab 显示空态文案而非报错；旧会话（无 surfaces）全链路无入口无报错。
6. **query 保留**：任何带 `?run=` 的深链经 canonical 化（尾斜杠/`/story-workspace` 根路径）与 SPA 导航后 query 不丢。

## 变更文件清单（commit 范围）

**新增**

- `frontend/src/router/storyWorkspacePath.ts`
- `frontend/src/router/__tests__/storyWorkspacePath.test.ts`
- `frontend/src/components/story-workspace/executionState.ts`
- `frontend/src/components/story-workspace/StoryWorkspaceExecutionProgressTable.tsx`
- `frontend/src/components/story-workspace/StoryWorkspaceExecutionAssetPanel.tsx`
- `frontend/src/components/story-workspace/StoryWorkspaceGuidanceSidebar.tsx`
- `frontend/src/hooks/story-workspace/useStoryWorkspaceGuidance.ts`
- `frontend/src/hooks/story-workspace/__tests__/useStoryWorkspaceGuidance.test.ts`
- `frontend/src/pages/story-workspace/StoryWorkspaceExecutionPage.tsx`
- `frontend/src/pages/story-workspace/__tests__/StoryWorkspaceExecutionPage.test.tsx`
- `docs/design/story-workspace/2026-08-04-dream-surface-task5-implementation-record.md`（本文件）

**修改**

- `frontend/src/router/story-workspace.tsx`（C10 适配器重写 + 两项 Task 4 遗留 + routeNotice）
- `frontend/src/hooks/story-workspace/contracts.ts`（Task 5 合同，DEC-026）
- `frontend/src/hooks/story-workspace/index.ts`（barrel）
- `frontend/src/hooks/story-workspace/useRunDeepLink.ts`（收编：router 喂 runId；路由切换清除）
- `frontend/src/hooks/story-workspace/__tests__/useRunDeepLink.test.ts`（签名跟进）
- `frontend/src/api/storyWorkspaceApi.ts`（`WorkflowRun.source_voice_thread_id` 补收）
- `frontend/src/components/story-workspace/surfaceLink.ts`（props +`onNavigate`）
- `frontend/src/components/story-workspace/StoryWorkspaceSurfaceLinkButton.tsx`（点击拦截 → router 导航）
- `frontend/src/components/story-workspace/index.ts`（barrel）
- `frontend/src/components/story-workspace/layout/StoryWorkspaceReviewDetail.tsx`（`onSurfaceLinkNavigate` 透传）
- `frontend/src/components/story-workspace/layout/StoryWorkspaceLayout.css`（执行页样式）
- `frontend/src/pages/story-workspace/index.ts`（barrel）

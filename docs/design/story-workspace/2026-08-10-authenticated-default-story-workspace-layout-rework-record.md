# 登录后默认进入 Story Workspace 布局实施记录

日期：2026-08-10

范围：登录根入口、Story Workspace canonical 路由、浏览器回归

状态：已实现并通过独立评审

## 1. 本轮 Optimized Prompt

在不引入第二套路由 owner、不改变既有 Story Workspace 深链、OAuth 回调与设备验证入口的前提下，将已登录用户访问根路径 `/` 时的默认布局从 `TopNavBar` 所属旧应用壳切换为 `StoryWorkspaceLayout`。根入口必须复用现有 Story Workspace 路径解析与 canonical 化机制，最终落到 `/story-workspace/dream`，由 `StoryWorkspaceRouter` 挂载 `StoryWorkspaceSidebar`。采用 TDD：先证明根路径当前不被 Story Workspace resolver 接管，再完成最小实现，覆盖刷新、未知路径与既有深链回归；最后使用真实 Chromium 和真实前端认证组件验证登录及刷新行为。保护其他工作线脏文件，不修改后端数据库，不执行归档。

## 2. Optional Enhancers

- 后续可补一条真实后端测试账号验收，但不得复用或写入生产数据。
- 后续可为 OAuth 成功回到 `/` 增加独立浏览器用例；本轮由 resolver 与 AuthContext 静态合同共同覆盖。

## 3. 执行计划与验收标准

计划：

1. 检查 git 状态和现有入口 owner。
2. 判定根入口应在 resolver、App 还是 AuthContext 中处理。
3. 先写失败测试，再做最小实现。
4. 执行聚焦测试、TypeScript、ESLint、构建和真实 Chromium 验收。
5. 独立评审、记录证据、仅提交本轮文件。

验收标准：

- 已登录用户访问 `/` 后进入 `/story-workspace/dream`。
- 页面挂载 `StoryWorkspaceLayout` 与 `StoryWorkspaceSidebar`，不显示旧 `TopNavBar`。
- 刷新后仍是同一 canonical 页面。
- 既有 Story Workspace 深链、未知路径、OAuth 片段消费和设备验证路由不被破坏。
- 不新增第二套路由状态 owner，不修改后端和数据库。

## 4. 问题判定

### 4.1 现状证据

- `App` 首次视图完全由 `resolveStoryWorkspacePath(window.location.pathname)` 决定：`frontend/src/App.tsx:171-175`。根路径原先解析为 `null`，所以回退到 `writing`。
- 旧 `TopNavBar` 仅在 `currentView !== 'story-workspace'` 时挂载：`frontend/src/App.tsx:1521-1524`。
- `story-workspace` 分支挂载 `StoryWorkspaceRouter`：`frontend/src/App.tsx:1526-1536`。
- Router 使用同一个 resolver 同步浏览器路径，并以 `replaceState` 规范化 alias：`frontend/src/router/story-workspace.tsx:265-307`。
- Router 的布局 owner 是 `StoryWorkspaceLayout`，左栏明确由 `StoryWorkspaceSidebar` 提供：`frontend/src/router/story-workspace.tsx:343-369`。
- 登录/注册界面在未认证时先于业务壳返回：`frontend/src/App.tsx:1382-1411`；因此登录成功后 React 重渲染会使用初始化时已判定的 Story Workspace 视图。

### 4.2 方案比较

1. 在登录回调里调用 `navigate`：会遗漏已有 token、OAuth 和直接刷新，形成第二入口 owner，不采用。
2. 在 `App` 中为 `/` 写特判：能够工作，但与现有 Story Workspace resolver 重复，不采用。
3. 将精确根路径 `/` 加入现有 resolver 的 Dream alias：登录、已有会话、刷新与 OAuth 根路径回跳共享同一 owner，采用。

### 4.3 最终决策

根路径 `/` 是 Dream 首页的入口 alias，canonical 路径唯一为 `/story-workspace/dream`。实现位于 `frontend/src/router/storyWorkspacePath.ts:132-143`。未知路径仍返回 `null`；`/oauth/device/verify` 不匹配该精确条件；既有 `/story-workspace/*` 深链不变。

## 5. TDD 与验证记录

### Red

先在 `frontend/src/router/__tests__/storyWorkspacePath.test.ts` 增加 `/` 应解析为 Dream 的断言。修改生产代码前，聚焦测试得到 1 个失败：resolver 实际返回 `null`。

### Green

- 根路径测试：1 passed。
- 完整 resolver 回归：`npx playwright test src/router/__tests__/storyWorkspacePath.test.ts --reporter=line --workers=1 --output=output/playwright/story-workspace-default-entry-2026-08-10/unit-results`，14 passed。
- TypeScript：`npx tsc -b`，通过。
- ESLint：覆盖 resolver、resolver 测试与 E2E 文件，通过。
- 前端构建：`npm run build`，通过。

### 真实 Chromium 验收

用例：`frontend/e2e/story-workspace-default-entry.spec.ts`。

步骤与结果：

1. 在根路径展示真实登录组件。
2. 通过页面级 deterministic API fixture 完成密码登录。
3. URL 规范化为 `/story-workspace/dream`。
4. `Story Workspace 导航` 可见，Dream 为当前项。
5. 旧 `TopNavBar` 的 `title="Writing"` 控件数量为 0。
6. 刷新后重复验证 3—5。
7. 控制台非白名单错误、page error、未知 API 均为 0。

命令：`npx playwright test e2e/story-workspace-default-entry.spec.ts --reporter=line --workers=1 --trace=on --output=output/playwright/story-workspace-default-entry-2026-08-10/browser-results`，最终复验 1 passed（4.4s）。

证据：

- 截图：`frontend/output/playwright/story-workspace-default-entry-2026-08-10/login-default-desktop.png`
- Trace：`frontend/output/playwright/story-workspace-default-entry-2026-08-10/browser-results/e2e-story-workspace-defaul-1ead3-nical-Story-Workspace-shell/trace.zip`

验收边界：真实 Chromium、真实 `AuthProvider`、登录表单、`App`、Router、Layout 与 Sidebar 均参与运行；认证及只读 API 响应使用页面 fixture。原因是并行后端工作线正在切换本地 PostgreSQL 启动合同，隔离数据库实例无法在本轮沙箱中建立。该边界不影响本次纯前端入口合同，但不宣称完成真实后端密码校验。

## 6. 独立评审

独立评审结论：P0 0、P1 0、P2 0，通过。

评审确认：

- 根 alias 复用唯一 resolver，没有第二 owner。
- `App` 初始化与 popstate 已复用该 resolver。
- OAuth token fragment 在工作区挂载前消费，error query/fragment 不被本次主动改写。
- 设备验证路由与未知路径不受精确 `/` 条件影响。
- Story Workspace 深链及 canonical/popstate 分支无回归。
- 补充评审提出的“刷新后缺少 Dream 当前项断言”及“8765 使用情况描述不准确”两项 P2 已修正，并完成 E2E 复验。

## 7. 工作区保护与运行资源

- 仅修改本轮 resolver、测试、E2E 和本记录；未回滚、覆盖或夹带并行后端、部署及其他文档工作线文件。
- 浏览器用例复用用户原有 5173 前端服务；全部 `/api/**` 由页面 fixture 响应，未调用、启动或关闭已有 8765 服务。
- 失败和成功用例的浏览器均由 Playwright fixture 自动关闭。
- 本轮尝试启动的隔离后端已退出；临时目录在交付前清理。
- 未执行归档操作。

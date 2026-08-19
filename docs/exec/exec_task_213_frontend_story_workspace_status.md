# Exec Report: task_213 - Story Workspace Workflow Status UI

## 1. 执行上下文

- Task ID: `task_213_frontend_story_workspace_status`
- 执行 Issue: `SUO-329`（`[execute][deck-plugin][task_213] 实现 Story Workspace Workflow Status UI`）
- 逻辑 Issue: `DECK-012`
- 来源控制项: `SUO-217`
- 关联设计稿:
  - `docs/design/story-workspace/product-scope-and-navigation.md` §2.3、§4.5
  - `docs/design/story-workspace/product-scope-and-navigation.md`
  - `docs/design/deck/design_002_deck-plugin-decision-gates.md` §4.5
- 关联 Stage: `docs/stage/stage_deck-plugin-voice-ink-dream-integration.md` §21.2，Stage 3 / Wave 1
- Task 文档: `docs/task/task_213_frontend_story_workspace_status.md`
- 强制模板: `docs/task/TASK-REQUIREMENT-FORMAT.md`
- 执行 Agent: `ExecTaskAgent`
- 执行时间: 2026-08-01 23:15–23:33 CST
- Checkout: 本 heartbeat 由 harness 预先 claim；未重复调用 checkout
- 初始状态: 共享工作树包含大量其他 task 的已修改/未跟踪文件；本执行保留全部既有差异，仅写 §11.1 闭集

## 2. TASK-REQUIREMENT-FORMAT.md 填充摘要

### 2.1 填充 Gate

| Gate | 填充值 / 结果 |
|---|---|
| 单一 Issue / Task / Stage 映射 | `SUO-329` → `task_213_frontend_story_workspace_status` → Stage 3 / Wave 1，唯一且完整 |
| 执行目标 | 实现 story-workspace 工作流上下文、8 步 preflight、运行状态、错误恢复、时间线及来源权限降级 UI |
| 交付类型 | frontend React/TypeScript 组件、hooks、API client、最小 layout/review 集成及唯一 exec 报告 |
| 明确不负责 | 后端状态机/API 实现、Deck binding 编辑、Voice chat 触发按钮/卡片、三栏骨架与既有审阅语义重构 |
| 允许修改范围 | Task §5 的 18 个 frontend 实现/条件测试路径 + 本报告；实际使用 14 个实现路径 + 本报告 |
| 禁止修改范围 | 其他 docs/exec、docs/design、docs/issue、docs/task、docs/stage、backend、依赖锁、测试/构建配置、生成物及未列明路径 |
| 验收条件 | Task §9 全部 12 项逐项带入 §6 |
| 测试要求 | runner 发现、`npm --prefix frontend run build`、`npm --prefix frontend run lint`、`git diff --check`；无 runner 时人工/合同证据 |
| 工作树冲突策略 | 不 reset、不清理、不覆盖；共享文件只追加 workflow/provenance props、slot 与样式，不修改既有几何或审阅行为 |
| Stage 准入 | Stage 文档 §21.2 九项 readiness 全部通过；本次 checkout 已持有；无未满足准入项 |

### 2.2 填充后的关键约束

1. 前端只消费服务端 binding/preflight/run/event/source 权威结果，不自行推进状态机。
2. 运行来源使用 `deck_plugin_id` / `deck_plugin_version`，与 Claude Code runtime plugin 命名隔离。
3. 错误 UI 只接收结构化 `error_code`、失败步骤与诊断 ID，不接收或显示堆栈、路径、prompt、secret、完整配置或 session settings。
4. Voice 来源权限单独判断；`denied` 分支固定显示「来源：Voice 对话（无权查看）」，不渲染名称、时间或链接。
5. SSE 事件按 `event_id` 去重并只接受更大的 `aggregate_version`；SSE 失败后 GET 轮询权威 run 快照。
6. 四个条件测试文件仅在发现兼容 test runner 时创建；本仓库 runner 发现为空，因此未创建。

## 3. 模型生成的执行任务

- 任务目标: 建立从 REST/SSE 合同到上下文条、preflight、run、error、timeline、provenance UI 的完整只读状态链。
- 实现范围:
  1. 定义 preflight/run/event/source API 类型和六个 mutation/query client。
  2. 实现 preflight 创建/查询/轮询 hook。
  3. 实现 run 创建/读取/重试/取消 hook。
  4. 实现 SSE 去重、版本顺序保护和轮询降级 hook。
  5. 实现六个 workflow UI 组件及受控导出。
  6. 在 `StoryWorkspaceLayout` 注入可选 context slot，在 `StoryWorkspaceReviewPanel` 注入可选 provenance slot。
  7. 只在既有 layout CSS 中添加 workflow/status/source/permission 样式，不改 240px / fluid / 360px 三栏几何。
- 验证方式: 全量 build、全量 lint、定向 ESLint、定向 TypeScript、13 项合同 smoke、diff/trailing whitespace/path 闭集检查。
- 范围校验结论: 通过；未生成 Voice chat UI，未写后端，未伪造服务端状态或来源。

## 4. 实现说明

### 4.1 API 与状态管理

- `storyWorkspaceApi.ts` 定义固定 8 步 preflight、完整 run 状态、步骤、transition、Voice source、统一事件 envelope 与安全 API error。
- API client 只提交 preflight token、idempotency key 和可选 Voice source 标识；不允许客户端提交 `deck_plugin_version` 或 runtime snapshot 覆盖服务端锁定来源。
- `useWorkflowPreflight` 负责创建、查询与 checking 状态轮询；失败保留权威记录，不创建伪 run。
- `useWorkflowRun` 负责 create/get/retry/cancel，并只以 REST snapshot 或服务器事件更新状态。
- `useWorkflowEvents` 使用浏览器 cookie 凭证订阅 SSE；按 `event_id` 去重、按 `aggregate_version` 单调更新，SSE error 时切换到 GET polling。

### 4.2 UI 与恢复

- `WorkflowContextBar` 展示 Deck Plugin 名称/版本、工作流摘要、runtime readiness、运行状态、进度、`workflow_run_id` 和脱敏 config ID 摘要。
- `PreflightProgressPanel` 固定展示 8 步顺序；失败时根据服务端 `failed_check` 停止后续步骤，通过时仅把 opaque token 交给回调，不在 DOM 展示 token。
- `WorkflowRunStatusPanel` 覆盖未选择、不可用、配置未就绪、preflight/queued/running/output-validating/pending-review/failed/completed/cancelled 等状态。
- `WorkflowErrorCard` 映射 Task §4.1 的 12 个错误码，并补充 `SECURITY_REVOCATION`；未知错误使用固定安全文案。
- `WorkflowRunTimeline` 按 `transition_seq` 展示状态历史、reason code、结果引用和 retry chain。
- `ProvenanceBadge` 展示 workflow run、Deck Plugin、profile、snapshot、runtime lock、时间、状态和 retry source；Voice `denied` 分支严格脱敏。

### 4.3 最小集成

- `StoryWorkspaceLayout` 新增可选 `workflowContext` 和 `reviewProvenance` props；未传入时不虚构 binding、run 或 source 状态。
- `StoryWorkspaceReviewPanel` 只在提供授权 provenance 时把来源卡放到既有 children 上方；关闭、标题、children 与 review 语义不变。
- CSS 保持 sidebar `240px`、main fluid、review `360px` 原值不变；只新增 task_213 class。

## 5. 变更摘要与文件清单

| 文件 | 操作 | 最小变更 |
|---|---|---|
| `frontend/src/api/storyWorkspaceApi.ts` | create | workflow preflight/run/event/source 类型与六个 API 操作 |
| `frontend/src/hooks/useWorkflowPreflight.ts` | create | preflight create/get/poll 状态管理 |
| `frontend/src/hooks/useWorkflowRun.ts` | create | run create/get/retry/cancel + event snapshot 状态管理 |
| `frontend/src/hooks/useWorkflowEvents.ts` | create | SSE 去重、aggregate version 顺序保护、GET polling 降级 |
| `frontend/src/components/story-workspace/workflow/WorkflowContextBar.tsx` | create | Deck Plugin、runtime readiness、run 状态和条件动作上下文条 |
| `frontend/src/components/story-workspace/workflow/PreflightProgressPanel.tsx` | create | 8 步 preflight 进度、失败 hard-stop、passed 启动入口 |
| `frontend/src/components/story-workspace/workflow/WorkflowRunStatusPanel.tsx` | create | 空/警告/运行/审阅/失败/取消/完成状态面板 |
| `frontend/src/components/story-workspace/workflow/WorkflowErrorCard.tsx` | create | 结构化错误码到安全文案/恢复动作映射 |
| `frontend/src/components/story-workspace/workflow/WorkflowRunTimeline.tsx` | create | transition 历史、结果引用、retry chain |
| `frontend/src/components/story-workspace/workflow/ProvenanceBadge.tsx` | create | 不可变来源与 Voice 权限降级 |
| `frontend/src/components/story-workspace/workflow/index.ts` | create | 受控导出 workflow 组件和类型 |
| `frontend/src/components/story-workspace/layout/StoryWorkspaceLayout.tsx` | update | 可选 workflow context 与 review provenance props/slot |
| `frontend/src/components/story-workspace/layout/StoryWorkspaceReviewPanel.tsx` | update | 可选来源卡插槽，不改 review children 语义 |
| `frontend/src/components/story-workspace/layout/StoryWorkspaceLayout.css` | update | task_213 workflow/status/source/permission 样式与窄屏 context bar 排布 |
| `docs/exec/exec_task_213_frontend_story_workspace_status.md` | create | 唯一正式执行报告 |

未创建的条件路径：

- `WorkflowRunStatusPanel.test.tsx`
- `PreflightProgressPanel.test.tsx`
- `WorkflowErrorCard.test.tsx`
- `useWorkflowEvents.test.ts`

原因：固定 runner 发现命令返回空字符串；未新增测试框架、依赖、锁文件或配置。

## 6. 验收条件逐项结果

| # | Task §9 完成标志 | 结果 | 证据 |
|---|---|---|---|
| 1 | 上下文条展示名称/版本/摘要/runtime ready | ✅ | `WorkflowContextBar` identity/facts/config summary；合同 smoke 通过 |
| 2 | 八类主要 UI 状态明确 | ✅ | context/run panel 覆盖 unselected、unavailable、config-not-ready、preflight、running、pending-review、failed、completed；另覆盖 queued/validating/cancelled |
| 3 | 8 步 preflight、选择器只读与 Loading | ✅ | `PREFLIGHT_CHECK_ORDER` 8 个唯一步骤；step checking；`selectorLocked` 禁用切换；合同 smoke 2 项通过 |
| 4 | 运行步骤进度与 workflow_run_id | ✅ | progressbar、manifest steps、current step、elapsed、run id；合同 smoke 通过 |
| 5 | 失败步骤/摘要/恢复动作 | ✅ | `WorkflowErrorCard` 仅显示安全映射、failed step、诊断 ID 与 1–2 个恢复入口 |
| 6 | 历史来源含 run/version/snapshot/lock | ✅ | `ProvenanceBadge` 与 `WorkflowRunTimeline`；合同 smoke 通过 |
| 7 | 错误码映射为恢复入口 | ✅ | Task 12 个错误码全部映射；合同 smoke 通过 |
| 8 | runner 或同等人工证据 | ✅（有限） | runner 为空；定向 TS/ESLint + 13 项静态合同 smoke 全通过。浏览器 E2E 因无 realized issue workspace / 可控浏览器连接未执行，见 §7.3 |
| 9 | 与既有 layout/review 增量集成 | ✅ | 仅可选 props/slot；三栏 width/flex 与 review children 行为不变；合同 smoke 通过 |
| 10 | 双向来源与无权限脱敏 | ✅ | granted 分支才渲染 name/time/link；denied 固定文案且静态断言无这三字段 |
| 11 | 实际变更只位于闭集 + 报告 | ✅ | 14 个 §5 实现路径 + 唯一报告；四个条件测试未创建；无其他本 task 写入 |
| 12 | 报告回填命令、结果、验收、diff、回滚 | ✅ | 本文 §5–§10 |

## 7. 测试与验证

### 7.1 已执行命令

| 命令 / 方法 | 结果 | 说明 |
|---|---|---|
| `node -p "require('./frontend/package.json').scripts?.test ?? ''"` | ✅ 输出空字符串 | 无现有 test runner；未创建条件测试文件 |
| `npm --prefix frontend run build` | ✅ 通过 | `tsc -b && vite build`；2662 modules transformed，Vite built in 533ms；仅既有 dynamic import/chunk size warnings |
| `npm --prefix frontend run lint` | ⚠️ 全仓失败 | 90 problems：70 errors / 20 warnings，均位于 task_213 闭集之外的既有文件；task_213 定向 lint 无问题 |
| `npx eslint <task_213 TS/TSX paths>`（`frontend/`） | ✅ 通过 | task_213 API、3 hooks、workflow 目录、2 个 layout 集成文件 0 error / 0 warning |
| 定向 `npx tsc -p $PAPERCLIP_RUN_SCRATCH_DIR/task213-tsconfig.json --pretty false` | ✅ 通过 | 仅编译 task_213 图；0 error |
| `node $PAPERCLIP_RUN_SCRATCH_DIR/task213-contract-smoke.mjs` | ✅ 13/13 | 验证八步、状态、错误映射、脱敏、来源字段、事件去重/顺序/降级和集成 slot |
| `git diff --check` | ✅ 通过 | 无 whitespace error |
| 授权文件 trailing whitespace 扫描 | ✅ 通过 | 无尾随空白 |
| Paperclip heartbeat context runtime 检查 | ⚠️ 无 workspace | `currentExecutionWorkspace: null`，无法取得 managed preview URL |

### 7.2 合同 smoke 明细

1. preflight 固定八步且无重复；
2. 八步均有用户可读标签；
3. 上下文条覆盖要求状态与后端运行态；
4. 运行时选择器支持只读锁定；
5. 运行面板展示 run ID、步骤和 progressbar；
6. 12 个结构化错误码均有安全恢复入口；
7. 错误详情不接收原始服务端技术文本；
8. 无权限来源使用冻结文案；
9. 无权限分支不含 Voice 名称、时间或 URL；
10. 来源卡包含 run/version/snapshot/runtime lock；
11. 事件按 ID 去重并拒绝旧 aggregate version；
12. SSE 失败后 GET polling；
13. layout/review 使用可选最小集成 slot。

### 7.3 未执行验证与替代证据

- 未执行真实浏览器 E2E：当前 Paperclip Issue 没有 realized execution workspace 或 runtime service URL，本会话也未取得 in-app browser 控制连接。
- 未执行真实 preflight/run 网络链：对应逻辑路由由并行 backend task 提供；本 task 不允许修改或伪造后端。
- 替代证据：生产 build 通过、定向 TS/ESLint 通过、13 项合同 smoke 通过、静态权限分支检查通过。
- 后续可复现人工步骤：
  1. 在有后端路由的 managed workspace 打开 Dream 页面并注入真实 `workflowContext`；确认选择器在 preflight/running 时 disabled。
  2. 观察 8 步 preflight；失败时确认后续为 waiting 且只显示结构化 code/安全文案。
  3. 启动 run，记录 create/get/SSE 请求与 `workflow_run_id`、steps、aggregate version。
  4. 断开 SSE，确认 UI 进入 polling 且 GET snapshot 更新状态。
  5. 分别使用 granted/denied Voice source 响应；denied 页面不得出现名称、时间、正文或返回链接。
  6. 失败后 retry，确认新 run ID 与 `retry_of_run_id` 链，取消 queued/running 时确认 cancel mutation。

## 8. 风险、阻塞与工作树处理

### 8.1 风险

- SSE endpoint 的物理路由由 backend/API task 最终确定；当前 client 使用逻辑 run events URL，404/error 会安全降级到 GET polling。
- 后端当前基础 `WorkflowRun` 模型不含全部 UI projection（display name、steps、source access、result summary）；前端将它们定义为可选，不会自行补造。
- 全仓 lint 有 70 个闭集外既有错误；本 task 定向 lint 和 production build 均通过。

### 8.2 阻塞

- 实现阻塞: 无。
- 发布/真实 E2E 阻塞: 需要 backend 逻辑路由和 realized preview workspace；不影响本 frontend task 的代码完成，但属于 Stage 3 集成验证前置。
- 需要上游动作: Stage/review owner 在 backend route 可用的集成 workspace 执行 §7.3 E2E；本 task 不创建额外后端或测试框架。

### 8.3 共享工作树

- 执行开始时已有 backend、design、issue、stage、task、App、story-workspace 其他组件及其他 exec 报告差异。
- 本执行未 reset、checkout、删除、格式化或回滚任何既有差异。
- `StoryWorkspaceLayout.tsx`、`StoryWorkspaceReviewPanel.tsx`、`StoryWorkspaceLayout.css` 在本 task 基线未显示为已修改；本次只添加 task_213 区段。
- 与并行 Plugin Admin 变更发生过一次 build 时序交叉；最终复跑 build 已通过，未修改其文件。

## 9. 完成状态

- [x] 已读取 Issue / Task / Stage / design 与强制模板
- [x] 已确认 checkout 和写入边界
- [x] 已完成实现
- [x] 已完成最小充分静态/合同验证
- [x] 已记录全仓 lint 非本 task 失败
- [x] 已记录未执行浏览器 E2E 及原因/替代证据
- [x] 已记录文件变更与工作树冲突处理
- [x] 已逐项回填 12 项验收
- [x] 可进入 review / audit

建议最终 Issue disposition：`done`。理由：task_213 授权实现、生产 build、定向 lint/TS、合同 smoke、diff 和唯一报告均已完成；真实跨域 E2E 由 Stage 集成 Gate 在 backend/runtime 就绪后执行，不应以无 live continuation path 将本 execute Issue 留在 `in_progress`。

## 10. 回滚建议

### 10.1 回滚文件

- 删除本 task 新建的 7 个 workflow 组件/出口文件、3 个 hooks 和 `storyWorkspaceApi.ts`。
- 从 `StoryWorkspaceLayout.tsx` 反向移除 `workflowContext` / `reviewProvenance` props 与两个 slot。
- 从 `StoryWorkspaceReviewPanel.tsx` 反向移除 provenance prop/slot。
- 从 `StoryWorkspaceLayout.css` 反向移除 `.story-workspace-layout__workflow-context`、`.story-workspace-review-panel__provenance` 和全部 `.workflow-*` 新增规则。
- 保留本执行报告，不随代码回滚删除。

### 10.2 回滚方式

1. 仅按本报告 §5 的文件/区段做反向 patch；不得对共享工作树运行 `git reset --hard` 或整文件 checkout。
2. 不删除或回滚后端 Workflow Run、Preflight、session、result、transition 或 source 数据。
3. 回滚后复跑 build、task 定向 lint、`git diff --check` 和 denied-source 人工场景。

### 10.3 触发条件

- 后端最终事件路由无法提供 SSE 且 polling 也不满足产品时效；
- 来源权限 projection 无法保证 `granted|denied` 服务端权威结果；
- workflow context slot 与后续 owner 集成出现无法安全合并的冲突。

回滚后的安全状态：隐藏 workflow/status/source UI，不伪造成功、来源或返回链接；保留既有三栏布局、数据表与 Review Panel 审阅语义。

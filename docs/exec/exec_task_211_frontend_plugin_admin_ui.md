# Exec Report: task_211 - 前端管理端插件目录与安装状态 UI

## 1. 执行上下文

- Task ID: `task_211_frontend_plugin_admin_ui`
- 执行 Issue: [SUO-327](/SUO/issues/SUO-327)
- 关联逻辑 Issue: `DECK-010`
- 来源控制项: [SUO-217](/SUO/issues/SUO-217)
- 关联设计稿: `docs/design/deck-plugin-voice-ink-dream-integration.md` §7.1、§12.1、§16.1、§16.2
- 关联 Task: `docs/task/task_211_frontend_plugin_admin_ui.md`
- 关联 Stage: `docs/stage/stage_deck-plugin-voice-ink-dream-integration.md` §21.2，Stage 3 / Wave 1
- 执行 Agent: `ExecTaskAgent` (`2a7a15fe-2ebb-4dc5-91a8-48ae2bcc5471`)
- 执行时间: 2026-08-01 23:15–23:29 CST
- Checkout: 本次 Paperclip harness 已预先领取 [SUO-327](/SUO/issues/SUO-327)，执行 Agent 未重复 checkout
- 初始状态: `in_progress` / `standard` / `high`

工作树基线存在大量其他 task 的未提交内容。与本 task 允许路径重叠的 `frontend/src/App.tsx` 在开始前已有 Story Workspace 路由接入差异；本次只新增一个受控 import 和 Settings 区块挂载，没有覆盖、重置或格式化该文件的其他差异。

## 2. TASK-REQUIREMENT-FORMAT.md 填充摘要

- 模板路径: `docs/task/TASK-REQUIREMENT-FORMAT.md`
- 输入 Issue: [SUO-327](/SUO/issues/SUO-327)，标题 `[execute][deck-plugin][task_211] 实现 Plugin Admin UI`
- 输入 Task: `task_211_frontend_plugin_admin_ui` / `DECK-010`
- Domain: `frontend`
- 执行目标: 在现有 Settings 中实现 Deck Plugin 管理目录、三维 readiness、详情、能力审批、生命周期 mutation 与安全错误/进度展示
- 明确不负责: Deck binding、Workflow Run/preflight、后端状态机、Paperclip Plugin worker 模型、Stage/Issue/Design/Task 改写、production readiness 宣称
- Stage 准入: Stage 2 Gate 已通过；`DECK-003` / `DECK-004` 前置满足；Stage 3 Wave 1 `ready_to_execute`；development/test + 单节点 persistent runtime 限域
- 并行约束: 与 task_212、task_213 可并行，但必须独立 checkout、独立报告、互不改写路径
- 模板填充 Gate: task、Issue、Stage、设计引用、闭集、禁止范围、11 项验收、测试和回滚要求均已读取并填充；无未决模板占位符

### 2.1 格式化后的写入闭集

允许修改：

1. `frontend/src/components/plugin-admin/PluginAdminPage.tsx`
2. `frontend/src/components/plugin-admin/PluginAdminList.tsx`
3. `frontend/src/components/plugin-admin/PluginAdminListItem.tsx`
4. `frontend/src/components/plugin-admin/PluginAdminDetail.tsx`
5. `frontend/src/components/plugin-admin/PluginStatusBadge.tsx`
6. `frontend/src/components/plugin-admin/PluginCapabilityDiff.tsx`
7. `frontend/src/components/plugin-admin/PluginErrorCard.tsx`
8. `frontend/src/components/plugin-admin/PluginOperationProgress.tsx`
9. `frontend/src/components/plugin-admin/index.ts`
10. `frontend/src/hooks/usePluginInstallations.ts`
11. `frontend/src/hooks/usePluginInstallationDetail.ts`
12. `frontend/src/hooks/usePluginOperation.ts`
13. `frontend/src/hooks/usePluginRuntimeReadiness.ts`
14. `frontend/src/api/deckPluginAdminApi.ts`
15. `frontend/src/App.tsx`（仅 Settings 增量入口/挂载）
16. `frontend/src/components/plugin-admin/PluginAdminPage.test.tsx`（仅现有 runner 可用时）
17. `frontend/src/components/plugin-admin/PluginAdminDetail.test.tsx`（仅现有 runner 可用时）
18. `frontend/src/hooks/usePluginOperation.test.ts`（仅现有 runner 可用时）
19. `docs/exec/exec_task_211_frontend_plugin_admin_ui.md`

禁止修改：除上述文件外的 `docs/exec/`、全部 `docs/design/`、`docs/issue/`、`docs/task/`、`docs/stage/`、`backend/`、依赖锁、测试/构建配置、生成物与未列明实现路径。三个条件测试路径因 test runner 发现结果为空而未创建。

### 2.2 格式化后的验收与验证合同

- 验收: 原 Task §9 的 11 项全部保留，逐项结果见 §6。
- 必跑命令: `node -p "require('./frontend/package.json').scripts?.test ?? ''"`、`npm --prefix frontend run build`、`npm --prefix frontend run lint`、`git diff --check`。
- 替代验证: 无 test runner 时使用浏览器/E2E 或人工证据；不得新增 runner 或伪报单测。
- 回滚: 仅删除本 task 新增文件，并从 `frontend/src/App.tsx` 移除本 task 的 import 和 Settings 挂载；不得回滚后端、历史审计或其他 task 差异；报告保留。

## 3. 模型生成的执行任务

- 任务目标: 建立独立于 Paperclip `PluginRecord.status` 的 Deck/runtime 插件管理模型和 Settings UI。
- 实现范围: 1 个 API adapter、4 个 hooks、8 个 UI 组件、1 个受控 export、1 个 App 增量挂载。
- 文件范围: 严格使用 §2.1 闭集；未创建条件测试文件。
- 实现步骤:
  1. 定义并归一化 Deck installation、Claude runtime lock、三维 readiness、兼容、健康、错误、权限和 operation 合同。
  2. 实现列表/detail/readiness 查询与服务端 operation mutation/polling hooks。
  3. 实现双分类目录、精确版本/来源/能力/健康/错误摘要、Configuration/Status 详情。
  4. 实现安装 manifest 能力确认、启停、升级、回滚、软卸载、reconcile、扩权批准/拒绝与安全进度/错误反馈。
  5. 在现有 Settings 视图增量挂载，执行最小充分验证。
- 关键安全决定:
  - 权限仅信任服务端 `permissions.can_manage` 等字段；缺失时默认只读。
  - compatibility、effective capabilities 与 runtime readiness 只展示服务端返回，不在浏览器自行计算或推进状态。
  - API 失败只显示不可用/错误，不使用假数据或伪造 mutation 成功。
  - 错误卡过滤多行、堆栈和本机绝对路径，只显示规范错误码与安全摘要。

## 4. 实现变更记录

| 文件 | 操作 | 说明 |
|---|---|---|
| `frontend/src/api/deckPluginAdminApi.ts` | create | Deck/runtime 独立类型、snake_case 响应归一化、权限 fail-closed、安装/启停/升级/回滚/卸载/reconcile/审批与 operation 查询 |
| `frontend/src/hooks/usePluginInstallations.ts` | create | 安装目录、runtime 依赖扁平列表、权限与刷新状态 |
| `frontend/src/hooks/usePluginInstallationDetail.ts` | create | 详情查询、取消与刷新 |
| `frontend/src/hooks/usePluginOperation.ts` | create | mutation 执行、1.5 秒 operation 轮询、终态刷新和错误 |
| `frontend/src/hooks/usePluginRuntimeReadiness.ts` | create | 服务端三维 readiness 查询，不进行客户端 run-ready 推导 |
| `frontend/src/components/plugin-admin/PluginAdminPage.tsx` | create | Settings 根页面、双分类、安装 manifest/能力确认、操作协调、响应式样式 |
| `frontend/src/components/plugin-admin/PluginAdminList.tsx` | create | loading/error/empty/list 状态 |
| `frontend/src/components/plugin-admin/PluginAdminListItem.tsx` | create | 名称、ID、精确版本、来源、三维状态、兼容、健康、能力、错误、最近运行和条件动作 |
| `frontend/src/components/plugin-admin/PluginAdminDetail.tsx` | create | Configuration/Status tabs、manifest/schema/runtime lock、effective capabilities、历史、最近 run、操作日志 |
| `frontend/src/components/plugin-admin/PluginStatusBadge.tsx` | create | Task §4.2 的 declared/materialized/loadable 状态文案映射 |
| `frontend/src/components/plugin-admin/PluginCapabilityDiff.tsx` | create | added/removed 展示与 upgrade_pending 明确批准/拒绝 |
| `frontend/src/components/plugin-admin/PluginErrorCard.tsx` | create | 规范错误码安全文案、阶段/operation/run 引用与恢复入口 |
| `frontend/src/components/plugin-admin/PluginOperationProgress.tsx` | create | queued/running/terminal 进度与失败反馈 |
| `frontend/src/components/plugin-admin/index.ts` | create | 受控组件导出 |
| `frontend/src/App.tsx` | update | 仅新增 `PluginAdminPage` import 与 Settings 内挂载；保留全部既有 Story Workspace 差异 |
| `docs/exec/exec_task_211_frontend_plugin_admin_ui.md` | create | 唯一正式执行报告 |

未创建 `PluginAdminPage.test.tsx`、`PluginAdminDetail.test.tsx`、`usePluginOperation.test.ts`：runner 发现命令输出为空，且 `frontend/package.json` 无 `test` script；按 Task 合同禁止新增测试框架或不可执行测试文件。

## 5. 测试与验证

| 检查 | 结果 | 证据 / 说明 |
|---|---|---|
| test runner 发现 | ✅ 执行；输出为空 | `node -p "require('./frontend/package.json').scripts?.test ?? ''"`，exit 0，stdout 空 |
| 生产构建 | ✅ 通过 | `npm --prefix frontend run build`，exit 0；TypeScript project build + Vite 2662 modules；仅既有 dynamic-import/chunk-size warning |
| 本 task 定向 lint | ✅ 通过 | 在 `frontend/` 执行 `node_modules/.bin/eslint`，覆盖新 API、4 hooks 与 `components/plugin-admin/`，exit 0，无输出 |
| 仓库要求 lint | ⚠️ 已执行但基线失败 | `npm --prefix frontend run lint`，exit 1，71 errors / 21 warnings；错误均位于既有文件（如 `voiceApi.ts`、`AnalysisView.tsx`、`EditorEngine.ts` 等）及 `App.tsx` 原有 `any`/hook warning；本 task 新文件定向 lint 为 0 问题 |
| diff whitespace | ✅ 通过 | `git diff --check`，exit 0，无输出 |
| 路径边界 | ✅ 通过 | 本 task 实际写入 15 个实现路径 + 1 个正式报告；未写 backend、依赖锁、配置或规划文档 |
| 浏览器/E2E | ⚠️ 未执行 | 当前运行没有可调用的应用内浏览器控制通道；仓库也尚无 `/api/deck-plugins/installations` 等 Plugin Admin router，无法获得真实 mutation/SSE/轮询闭环；未伪造截图、后端状态或成功结果 |

### 5.1 人工/静态验证证据

在无法启动真实浏览器/API 闭环的条件下，逐项检查源码与构建产物入口：

1. `PluginStatusBadge.tsx` 覆盖 Ready、Loaded、Materializing、Declared not materialized、Load failed、Disabled、Not installed。
2. `PluginAdminListItem.tsx` 对 `ready` / `disabled` / `availableVersion` / rollback versions / readiness failure / system plugin 条件展示合法动作；非管理员隐藏动作并显示只读提示。
3. `PluginAdminDetail.tsx` 包含 Configuration / Status tab、manifest/schema/workflow/runtime lock、capability diff、错误、history、recent runs、operation logs。
4. `PluginAdminPage.tsx` 的安装流程必须先通过精确 SemVer 校验，读取 manifest preview，显示 `manifest_requested` capability 并勾选确认后才可安装。
5. `usePluginOperation.ts` 只在服务端返回终态 `ready/completed/error/failed` 后结束轮询并刷新；没有本地成功 fallback。
6. `deckPluginAdminApi.ts` 不 import Paperclip Plugin 类型，Deck 字段使用 `deckPluginId/deckPluginVersion`，runtime 字段使用 `claudeCodePluginId/resolvedVersion/artifactDigest`。

### 5.2 可复现浏览器验证步骤（待后端 router/浏览器通道可用）

1. 使用管理员身份打开 Settings，确认「Deck 工作流插件」区存在并可切换到「ClaudeAgent 运行时插件」。
2. 对服务端 fixture 逐个提供七类三维状态，检查 badge 文案与条件按钮。
3. 打开详情，切换 Configuration / Status，核对 manifest、schema、runtime lock、effective capabilities、错误、历史和 run 列表。
4. 使用非管理员响应，确认 Install 和所有 lifecycle 按钮不可见，页面仍可只读。
5. 执行安装：输入受控来源与精确版本 → 加载 manifest → 确认 capability → 提交 → 观察 operation 终态。
6. 执行 Enable / Disable / Upgrade / Rollback / Uninstall / Reconcile，核对请求路径、请求体、进度与失败恢复。
7. 对 `upgrade_pending` 返回 `capability_diff.added`，确认批准/拒绝入口；验证旧 ready 版本未被前端改写。

## 6. 验收条件逐项结果

| # | Task §9 完成标志 | 结果 | 证据 |
|---|---|---|---|
| 1 | 管理端插件列表页面实现 | ✅ | `PluginAdminPage` + `PluginAdminList`，由 Settings 挂载 |
| 2 | 名称、来源、精确版本、三维状态、能力、兼容、健康、错误摘要 | ✅ | `PluginAdminListItem` + `PluginStatusBadge` |
| 3 | Configuration / Status tab | ✅ | `PluginAdminDetail` |
| 4 | 区分 Deck 工作流插件 / ClaudeAgent 运行时插件 | ✅ | 显式类型与双分类 tab；无笼统跨域 ID |
| 5 | 能力扩张升级显式审批 | ✅ | `upgrade_pending` + capability diff + approve/reject mutation |
| 6 | 健康与 `last_error` 可观察 | ✅ | list 摘要、detail error card、规范错误码与恢复动作 |
| 7 | 管理动作要求管理员权限 | ✅ | 只信任服务端 permissions，缺失 fail-closed；非管理员隐藏动作 |
| 8 | runner 自动化测试或同等人工证据 | ✅（无 runner 分支） | runner 输出为空；未创建测试文件；§5.1 静态/人工证据 + §5.2 可复现步骤；真实浏览器闭环未验证并已披露 |
| 9 | 不直接复用 Paperclip `PluginRecord.status` | ✅ | 独立 Deck installation/runtime 三维枚举与 normalizer |
| 10 | 变更只位于 18 路径 + 唯一报告 | ✅ | 实际使用其中 15 个实现路径；3 个条件测试路径未创建；报告路径唯一 |
| 11 | 回填命令、结果、验收、diff、回滚 | ✅ | 本报告 §5、§6、§8 |

## 7. 风险与阻塞

- 风险: Plugin Admin 前端按 Task §5 逻辑 API 编写，但当前工作树未发现对应管理 router；真实响应 shape 与 operation status endpoint 落地时可能需要在本 API adapter 内做小范围对齐。
- 风险: 当前运行只证明 production build 与静态交互合同，未获得真实浏览器截图、网络请求/响应或权限降级录屏。
- 风险: 仓库级 ESLint 基线已有 71 个错误；本 task 没有授权修复这些文件。新文件定向 lint 为 0 问题。
- 阻塞: 无阻塞本 frontend task 完成的第一类问题；后端 router 与浏览器/E2E 证据属于后续集成/Stage Gate 复核输入，owner 为对应 backend execute task / StagePlanner。
- 需要上游澄清: 后端最终 operation 查询端点与 uninstall/upgrade approval 的精确路由若不同，应由后端合同 owner 给出正式变更，再仅调整 `deckPluginAdminApi.ts`；不得由前端伪造。

## 8. 完成状态

- [x] 已完成实现
- [x] 已完成最小充分静态测试
- [x] 已记录变更
- [x] 已逐项映射验收条件
- [x] 可进入 review / audit

建议 Paperclip Issue 最终状态：`done`。理由：本 Issue 的 frontend 实现与允许范围内验证已完成，没有仍需在本 Issue 内执行的授权工作；未验证的真实 API/browser 闭环已作为 Stage/集成风险披露，不以伪造成功替代。

## 9. 回滚建议

- 回滚文件: 删除本次新建的 `frontend/src/components/plugin-admin/` 九个文件、4 个 `usePlugin*` hooks 与 `frontend/src/api/deckPluginAdminApi.ts`。
- App 回滚: 只从 `frontend/src/App.tsx` 移除 `PluginAdminPage` import 与 Settings 内 `Deck Plugin Admin` section；不得回滚该文件既有 Story Workspace 路由差异。
- 报告保留: `docs/exec/exec_task_211_frontend_plugin_admin_ui.md` 作为执行证据，不随代码回滚删除。
- 注意事项: 不触碰后端 installation/release、审计记录、历史 run、依赖锁或其他 Settings 功能。
- 回滚验证: 再执行 `npm --prefix frontend run build`、本 task 定向 lint 和 `git diff --check`，确认 Settings 其余功能与共享差异仍保留。

## 10. 执行完成报告

task_211 已在唯一 checkout 与严格十九路径闭集内完成。交付实现了 Deck/runtime 类型隔离、服务端权限与状态权威、目录/详情/三维状态、能力扩张审批、生命周期动作、进度、安全错误和 Settings 增量入口；无 test runner 时没有新增测试框架或伪报单测。生产构建、定向 lint、diff whitespace 和路径审计通过；仓库 lint 基线失败与真实 browser/API 未验证项已如实记录。可交由 StagePlanner / reviewer 进行 Stage 3 Gate 的 API 合同与真实浏览器集成复核。

<!-- [Input] Implementable design review, Stage 4 visual specification and authorized existing public-read boundaries. -->
<!-- [Output] Minimum source/test implementation receipt, exact commands, passed focused/final type evidence and preserved failures. -->
<!-- [Pos] Chat activity implementation handoff; technical execution and real-business acceptance are separate. -->
<!-- [Sync] 2026-10-07: retain local logs as explicit local paths and version the read-only document validation harness for clean PR checkouts. -->
<!-- [Sync] 2026-10-07: record 22 unique checks, final six-browser diagnostics, type/lint/doc pass and preserved clock/route/offset fixture failures. -->

# 活动视图实施回执 · 2026-10-07

## 状态与执行依据

[独立设计评审](priority-activity-design-review-20261007.md)结论为可实施，D1 已闭合；[Stage 4](../design/claude-agent/priority-activity-workflow-20261007/workspace/4_ui_design.md)先保存本轮优化提示词和现有主题视觉规格，再编写功能代码。最小实现已写入，6项纯模型与6项生产组件focused技术检查全部通过，相关原合同10项通过，共22个unique检查，不累计重复运行数；changed-files ESLint为0错误0警告。初轮与最终全仓类型检查通过，中间复核的并行Notion文件 `number`→`Timeout` 错误保留在历史回执，本次未改该无关文件。确定时钟的最终6项browser与诊断附件已经完成；本回执不代表真实业务测试、模型验收或发布通过。

## 实际变更

| 文件或模块 | 已写入行为 |
| --- | --- |
| `ChatView.tsx`、`Icons.tsx` | 新建旁始终可见的活动视图铃铛；原 `threadSidebarOpen` 管理一个活动／历史栏；更多历史指向同一栏，与文件、子智能体、任务会话和任务详情双向互斥。 |
| `ActivitySidebar.tsx/.css` | 20rem 桌面侧栏、原 `useMobile` 的全宽抽屉、固定标题与唯一 body 滚动；四项可连续勾选菜单，搜索／菜单／抽屉分层焦点与 Escape，窄屏背景隔离。 |
| `activitySidebarModel.ts` | 集中五分钟及技术调度 policy，复用 `timezone.ts`；task_id 合并、inclusive recency、来源实体去重、真实任务运行／Dream 阶段分层，失败旧状态退出当前运行层。 |
| `useActivitySidebarData.ts` | 三个来源独立的 loading/error/最近成功集合与请求序号；近期 Chat 公开分页直到旧记录或空响应，原始批次数量推进；扫描途中失败保留行；关闭、隐藏、卸载停止新增计时与读取，跨日任务范围和晚到响应受保护。 |
| `chatHistoryApi.ts`、`scheduledTaskApi.ts` | 可选 `AbortSignal` 仅取消活动读取；原 DTO、路由、动作和调用者保持兼容。原 Dream landing hook 未修改。 |
| 原历史／删除／导航 | 历史失败及分页失败可重试，不伪装为空／全部显示；历史 raw offset 独立于展示去重。删除成功同步近期、历史及搜索；已消费 ID 删除减少 offset，旧批次提交扣除已成功删除 ID，普通重复 ID仍按原始条数消费。保留原删除当前 Thread 行为。 |
| `i18n.ts`、目录清单、双语 README、现行文档 | 同步活动入口、来源、真实状态、显示和恢复文案及当前实现映射，保留旧文档原文。 |

普通 Chat 点击仍用 `handleSelectThread`，普通 Dream 点击仍用 `openDreamRun`，修饰键使用原 canonical href；任务行打开原 `ScheduledTaskDetailSidebar`。只有存在定义时生成快照，孤立触发传 `taskId` 与空快照。活动打开、刷新、筛选和导航不自动创建、发送或控制业务；原用户主动删除继续使用原公开删除接口。

## 技术测试入口

- `frontend/app/_dream/components/chat/__tests__/ActivitySidebarModel.test.ts`：五分钟边界、未来／无效时间、跨日连续窗口、已有 timezone 解析、Chat 批次停止证据、ID 合并与排序、真实任务／Dream 状态和失败旧状态、显示投影不修改原数组。
- `frontend/app/_dream/components/chat/__tests__/ActivitySidebar.browser.test.ts`：实际挂载生产 `ChatView`／`ActivitySidebar`，本机 Chrome、自有随机 Vite 端口和单测缓存；覆盖完整近期多页、四选项、搜索／导航、孤立任务、来源与历史失败恢复、删除后的 raw offset 和延迟旧历史响应、390px焦点与滚动、跨午夜及关闭／隐藏旧响应，检查自动活动没有控制写请求。

浏览器夹具仅在 `__tests__`；使用公开生产 DTO 和真实组件，不另写 parser/reducer/入口。Dream Project、Episode、私有发布、Hook 和数据库不在范围；共享 Thread 只用于现有导航，正文与草稿保持原能力。截图命名为 `output/playwright/priority-activity-desktop.png`、`priority-activity-mobile.png` 和 `priority-activity-menu.png`，输出位于测试cwd的 `frontend/output/playwright/`；它们是模拟公开接口的技术证据，不能作为当前普通用户服务或真实业务验收截图。

## 确切验证命令

从仓库的 `frontend` 目录执行：

```sh
corepack pnpm exec playwright test app/_dream/components/chat/__tests__/ActivitySidebarModel.test.ts app/_dream/components/chat/__tests__/ActivitySidebar.browser.test.ts --reporter=line --workers=1 --output=../output/playwright/priority-activity-final-verified-tests
corepack pnpm exec playwright test app/_dream/components/chat/__tests__/ScheduledTaskMarker.test.ts app/_dream/components/chat/__tests__/ThreadSessionHydration.test.ts --reporter=line --workers=1 --output=../output/playwright/priority-activity-related-tests
corepack pnpm exec tsc --noEmit --incremental false
corepack pnpm exec eslint app/_dream/components/chat/ChatView.tsx app/_dream/components/chat/Icons.tsx app/_dream/components/chat/ActivitySidebar.tsx app/_dream/components/chat/activitySidebarModel.ts app/_dream/components/chat/useActivitySidebarData.ts app/_dream/components/chat/__tests__/ActivitySidebarModel.test.ts app/_dream/components/chat/__tests__/ActivitySidebar.browser.test.ts app/_dream/api/chatHistoryApi.ts app/_dream/api/scheduledTaskApi.ts app/_dream/i18n.ts
```

从仓库根目录执行现行文档检查：`python3 docs/design/claude-agent/priority-activity-workflow-20261007/workspace/validate_documents.py`（原执行脚本位于本地 `output/playwright/priority-activity-doc-check.py`）。该明确命名的只读harness检查Markdown清单、本地引用、README活动条目、现行状态及正式稿四幅Mermaid语法；包括本次Chat Sidebar／Dashboard迁移指引与完整旧稿。脚本仅创建并关闭自有Chrome文档DOM来parse/render四图，不访问业务页面、数据库或业务API。

仅复用本机 Chrome，不下载 Chromium revision。runner／浏览器启动失败属于前置失败，不据此认定界面或 API 有缺陷。测试只关闭自身 Vite server 并删除自身 cacheDir；不启动或停止既有 5173／8765 服务、数据库或正常用户进程。当前 Next 开发服务正在使用 `.next`，本次不直接运行会改写该目录的生产构建。专用验证执行者负责上述机械检查；无发布、提交、合并或重启授权动作。

日志、模拟接口截图和诊断 JSON 保留在本轮本地输出目录，不纳入 Git；下表保存实际命令、退出码、关键结果与失败历史。

## 当前实际证据

| 命令 | 退出码 | 关键结果与限制 |
| --- | --- | --- |
| `node --input-type=module` 内联 TypeScript `transpileModule` 语法检查 | 0 | 首次6文件、冻结后10个本轮源／测试文件均无语法错误，最终 `syntax_files=10 errors=0`；仅语法，不代表类型或功能通过。 |
| 首轮 focused Playwright（11项，由专用runner执行） | 1 | 原始日志（本地 `output/playwright/priority-activity-tests.log`）：6项纯模型通过，5项浏览器均未完成生产组件挂载；这是harness前置失败，不能判为页面/API缺陷。 |
| 修后bell单用例及组合11项回归 | 单用例0，组合1 | 挂载单例日志（本地 `output/playwright/priority-activity-mount-rerun2.log`）通过；组合日志（本地 `output/playwright/priority-activity-final-tests.log`）10项通过，历史offset19失败注入的前提被此前真实滚动自动分页改变。 |
| 拆分后12项回归 | 1 | 原始日志（本地 `output/playwright/priority-activity-accepted-tests.log`）：11项通过，历史首批合法省略offset0参数，夹具错误要求固定序列化字符串；改为URL参数语义核对，没有改API。 |
| 历史单用例、最终完整focused（上方命令） | 0、0 | 历史日志（本地 `output/playwright/priority-activity-history-rerun.log`）：1项通过；最终日志（本地 `output/playwright/priority-activity-final-verified-tests.log`）：12项通过（14.9s），含延迟旧历史响应后删除及继续加载不漏lookahead。 |
| 首次追加诊断的6项browser回归 | 1 | 原始日志（本地 `output/playwright/priority-activity-final-diagnostics-tests.log`）：5项通过，延迟跨日用例未得到今日行。原fixture在23:59:58安装clock后，慢挂载仍推进Date，不能保证首次明确10/07；两个跨日fixture改为挂载期setFixedTime、跨日前setSystemTime再runFor，并断言10/07和10/08公开日期读取。只修夹具前置条件，没有改生产状态机。body式附件未被line reporter存盘，已改安全JSON写自有outputPath后path attach；不能补造过去首日诊断证据。 |
| 首轮 `corepack pnpm exec tsc --noEmit --incremental false` | 0 | 原始日志（本地 `output/playwright/priority-activity-tsc.log`）无诊断。 |
| 中间全仓同一类型复核 | 2 | 复核日志（本地 `output/playwright/priority-activity-actual-final-type.log`）：`ConnectorNotionDetailPage.tsx(485,26)` TS2322，`number`不兼容`Timeout`；并行Notion改动不在本次范围，没有由本任务修改。 |
| 最终 `corepack pnpm exec tsc --noEmit --incremental false` | 0 | 最终日志（本地 `output/playwright/priority-activity-final-diagnostic-type.log`）无诊断，runner退出0；保留先前并行修改错误，不覆盖失败证据。 |
| 确定时钟的跨日单例及最终6项browser | 0、0 | 跨日单例1项通过；最终browser日志（本地 `output/playwright/priority-activity-complete-browser.log`）：6项全部通过（15.4s）。两个跨日fixture在mount时 `setFixedTime(NOW)` 仅固定Date，定时器仍工作；跨日前 `setSystemTime(NOW)` 解除fixedDate后再 `runFor(3000)`，明确公开日期由10/07进入10/08。没有重复运行model/related来累计检查数量。 |
| 最后browser测试文件ESLint | 0 | runner在确定时钟与path附件修改后检查 `ActivitySidebar.browser.test.ts`，0错误0警告。 |
| `python3 output/playwright/priority-activity-doc-check.py` | 0 | 当轮文档日志（本地 `output/playwright/priority-activity-doc-check.log`）：15个指定Markdown、79个本地引用、20项inventory、README活动条目一致、四幅Mermaid均parse并render SVG、0错误；包括本次迁移指引与旧稿。回执追加后由root再核对最终文档及diff，不把该结构检查称为真实业务验收。 |
| 原 `ScheduledTaskMarker.test.ts`＋`ThreadSessionHydration.test.ts` focused回归 | 0（runner回执） | 原始日志（本地 `output/playwright/priority-activity-related-tests.log`）：10项通过；没有浏览器或模型调用。 |
| 首轮 changed-files ESLint | 0 | 原始日志（本地 `output/playwright/priority-activity-eslint.log`）：0错误、7条本轮hooks依赖警告，按实际回调、日期输入和cleanup映射修正。 |
| 源码＋测试10文件ESLint及拆分后测试复核 | 0、0 | 修后日志（本地 `output/playwright/priority-activity-eslint-final.log`）、拆分复核（本地 `output/playwright/priority-activity-accepted-eslint.log`）：均0错误0警告。 |
| `python3 -` 内联 Markdown 清单／本地引用／围栏／空白／README活动条目检查 | 0 | `markdown_files=5 local_links=29 inventory_files=8 readme_activity_parity=1 formal_mermaid_blocks=4 errors=0`；只验证文档结构与路径，未重新解析Mermaid。 |
| `git diff --check --` 本轮源码／目录／现行文档／双语README范围 | 0 | 无输出；未跟踪新文档的空白由上方检查覆盖。不是功能验证。 |
| `node --input-type=module` 提取当前正式稿首幅图并执行 `mermaid.parse` | 0 | `normal_sequence=PASS type=sequence dream_read=storyWorkspaceFetchDreamRuns display_owner=ChatViewContent model_direct_view_calls=0`；只解析当前受影响正常时序，未重复其余图或浏览器。 |

首轮harness根因是 `page.route('**/api/**')` 同时匹配 Vite 的 `/app/_dream/api/*.ts` 源码，未知path被fixture返回JSON，阻断模块加载。当前夹具先检查 `url.pathname.startsWith('/api/')`，其他请求 `route.continue()`，并在挂载前记录console／pageerror／requestfailed、失败时输出安全fixture正文；保留原始失败日志。来源反馈重试与历史分页已拆为独立可见操作场景，原生产滚动、分页和API序列化没有为夹具改变。最后在每个browser用例的 `harness.close` 附加 `priority-activity-safe-diagnostics` JSON，记录consoleErrors、requestFailures、pageErrors和fixture读写路径；只有pageErrors和允许的写请求被测试断言，不能从断言不存在推导console／requestFailures为零。

root已检查桌面截图（本地 `frontend/output/playwright/priority-activity-desktop.png`）和390px截图（本地 `frontend/output/playwright/priority-activity-mobile.png`）：当前纸面主题、20rem右栏、窄屏全宽抽屉、固定标题与行结构符合视觉规格。显示菜单截图（本地 `frontend/output/playwright/priority-activity-menu.png`）在四项勾选断言后生成。截图和JSON只作为模拟公开接口技术证据，不能替代正常用户服务或真实业务验收。

最终安全JSON位于 `output/playwright/priority-activity-complete-browser/*/priority-activity-safe-diagnostics.json`，root已读取：bell用例的consoleErrors、requestFailures、pageErrors均空；来源失败用例有3个预期503，历史失败用例有1个预期503及2个用户显式DELETE；关闭／跨日取消诊断为预期ERR_ABORTED，全部pageErrors为空。只按夹具的来源故障和读取取消分类，不宣称所有用例console/requestfailure为零。root也已检查菜单截图，其四项显示布局符合视觉规格。

## 限制与发布状态

今日任务接口不包含昨日开始仍运行的触发或未来一次性定义；Chat updated_at 可能来自消息以外的更新且没有全局 running；Dream 阶段不代表实时 Runtime 观察，recent 集合继续使用服务端范围。公开 offset 读取无原子快照，期间更新由下次正常刷新重新扫描。本次没有新增后台聚合、通知／已读状态、任务控制、共享 schema、Runtime 或发送协议。

当前分支为 `develop`，用户和其他 Agent 的未提交文件已经保留。本轮仍是未提交工作，没有PR、Git提交、发布、重启或正常数据库写入。涉及 Chat 源码的发布仍需遵守 `Agent.md` 的完整发送链路门禁；本次技术界面验证不得替代用户正常 Dream/Admin/Gateway/PostgreSQL 的真实模型验收。

最终只读收口：`python3 output/playwright/priority-activity-doc-check.py` 退出0，检查15份Markdown、83处本地引用、20项目录清单、双语README活动条目；正式稿4幅Mermaid均解析并渲染SVG成功。`git diff --check` 退出0、无输出。原始日志分别为 `output/playwright/priority-activity-doc-check-final.log` 与 `output/playwright/priority-activity-diff-check-final.log`。这些结果属于文档与工作区检查。

## 后续提交授权 · 2026-10-07

用户在技术验证完成后授权提交、创建 PR、合并到仓库默认主分支 `develop` 并切回该分支。该授权不包含部署；原发布门禁保持。提交仅纳入活动视图，不包含原有未推送登录偏好提交或并行 Calendar／Notion 改动。参考截图含对话片段，保留本地且由精确 `.gitignore` 排除；布局规则、正文骨架、业务图及优化提示词纳入版本管理。PR 的独立工作区验证与合并结果在后续回执记录。

<!-- [Input] Current calendar PRD/design/review, develop baseline and user's Search-scope decision. -->
<!-- [Output] Implementation impact assessment, completed technical journey matrix, command receipts and acceptance limits. -->
<!-- [Pos] Calendar implementation evidence; technical validation is not real-account acceptance. -->
<!-- [Sync] 2026-10-06: close the accepted Search-scope implementation with final source hashes, 39 browser journeys, 37 backend cases, build, contrast, documentation and cleanup receipts. -->

# 日历栏目实施与验证记录

本实施聊天为 `01a10c81-1077-7bf1-8973-fee93a49936e`。原生 Codex 目标是：完成日历右侧互斥页签及已明确资源范围的 Notion 今日文档功能，保留既有业务，通过完整业务旅程自动化验证，并提交可复核代码、文档和测试回执。目标没有 token 预算；最终状态以原生目标工具回执为准。本稿提供代码与技术验证证据。

## 1. 基线、授权与影响评估

- 基线：`develop`，`dc5c7723f28bc75efe55f7573182fe857782dbdf`。起始未提交内容仅为父聊天列出的根合同、PRD、交互稿、评审及历史材料；均保留。
- 用户直接答复接受“Search 可发现范围，继续实现”。严格授权全集不再是本次验收范围；Search 的索引遗漏、延迟和扫描变化仍须明确呈现。官方依据：[Search limitations](https://developers.notion.com/reference/search-optimizations-and-limitations)。
- 本任务负责 CalendarPopup、其样式与本地文案、必要 App 设置导航、共享 Notion 字形、今日 API/helper/panel、Notion facade/operations 和允许目录内的测试；只对有关目录合同与现行设计做增量同步。
- 呈现变化：右栏三项互斥；保留同日输入、滚动、LIST/RESULT 与任务卡状态。隐藏内容使用 hidden/inert，暂停新查询/轮询，更多菜单关闭；共享 Modal 仅补过滤隐藏焦点目标。
- 状态所有者：CalendarPopup 保存日期、任务与安排输入；ScheduledTaskCard 保持编辑/revision/历史 owner；ScheduledTaskResult 保留精确 final_message_id；新 Notion 局部面板保存当前 actor/connector/date/timeZone/generation 的只读响应。
- 数据与权限：现有 router → actor facade → Admin connector 归属、user-preferences.get → effective_home → ntn 0.15.1。只读 Search 原始元数据；不调用 select/sync/body，不改变 Agent 已选正文权限，不新增 schema 或 Admin capability。
- 现有缺口：创建时间、扫描完整性、错误分类、服务端 API 日期与安全 URL 投影。今日路径单独补充，不改变既有同步/正文读路径。
- 不涉及 Project/Episode/canonical Artifact、Run-private .dream、after-turn Hook、Gateway、模型、账本或资源策略；这些在本次技术场景全部为不在范围。任务 Chat 仅验证原导航与未发送输入；不发 Agent turn。
- 根 `CLAUDE.md` 在当前 checkout 不存在，已读取根 AGENTS.md、Agent.md 与适用 Cursor 合同；不读取真实 thread workspace 来替代仓库规则。

## 2. 旅程与验证边界

| 旅程 | 验证内容 | 数据与入口 |
| --- | --- | --- |
| 日历 | 默认日期/栏目、手动键盘激活、tooltip、唯一面板、切换保留、日期、关闭重开、明暗与窄屏 | 生产 Next/UI，拦截公开 API 的真实 DTO |
| 定时任务 | 安排与未发送 Chat 草稿、编辑/失败/revision 冲突、立即运行、记录/历史分页、精确结果/Thread、暂停/恢复、删除/撤销 | 复用 scheduled-task-calendar spec，fixture 写入仅在内存 |
| 日记 | 日期/列表/当前标记/打开/返回/原删除确认 | 公开 sessions 接口 fixture |
| Notion 正常 | 今天门禁、连接、归属/时区、分页、去重/分组/计数、直接外链、刷新、切栏 | 公开今日 GET + 原连接 DTO；后端注入假 Provider |
| Notion 异常 | 未连接/pending/失效/拒绝/两类空/partial/缺字段/重复/cursor/429/网络/5xx/旧结果/URL/午夜 | 前端浏览器和后端合同故障注入 |
| 并发与时间 | A→B→A、登出/关闭迟到、区间起止、DST、双命中、partial 0、无 select/sync/body/写入 | clock、控制 promise、真实生产函数/DTO |

隔离技术 lane：只启动本轮命名的 Next 进程和可用端口 55173；无 backend、数据库、真实账户或模型。Chrome 已通过一次启动检查，不下载浏览器。Luna 执行有界测试并提供退出码；主任务负责实现与修复。清理只关闭自建 Next/Chrome，保留可复核 output 回执。

## 3. 结果与验收边界

实现与本轮自动化技术验证完成。最后源码的完整浏览器旅程为 **39 passed / 0 failed / 0 skipped**：身份组件2项、Calendar/Notion28项、原定时任务9项；保留39份 trace。后端四文件为 **37 passed**。tsc、完整 ESLint、production build、定向色彩、文字缩放、Markdown/引用、Mermaid与diff检查均通过，具体命令和证据见§6。

Notion验收采用用户已接受的 Search 可发现今日页面；保留遗漏提示、刷新及 partial 状态。没有执行真实 Notion账户、正常本机服务、数据库或模型验收；正常部署仍须显式配置支持的 `INK_NOTION_TODAY_API_VERSION`。这不是浏览器39项中的跳过项，也不将 fixture 回执称为真实业务结果。首次前置检查仍保留在 `output/playwright/calendar-tabs-20261005/preflight-receipt.md`；复用本机Chrome，没有下载浏览器。

## 4. 实际实现与错误合同

- `CalendarPopup` 使用本地 active/focus 状态、稳定 tab/panel 关联及 hidden/inert；保留原任务卡、结果、编辑/历史 Modal 和日记 callbacks。隐藏任务停止新读取/轮询；共享 Modal 仅将不可见焦点目标排除。tooltip 按当前矩形向视口内夹取位置，scroll/resize 重算。
- `CalendarNotionPanel` 用 actor/date/timeZone/today 与 request generation 校验响应；同日隐藏保留已读或正在读取的结果。连接事件、日期/身份变化和关闭取消旧请求，快速日期 A→B→A 会开启新扫描；网络/5xx/429 仅在同上下文保留上次响应。
- `notionTodayApi` 校验字段、半开时间区间、唯一 ID、分组标记及计数一致性。显示只读 metadata；URL 由 `today.safe_url` 的服务器配置检查，直接新标签打开，无打开前正文/权限预检。
- `routers/notion.py:today_pages` 使用原认证依赖、actor facade、Admin connector 归属与偏好 DTO，再从 `effective_home` 读取凭证。`today.read_today` 顺序 Search 分页、去重并处理不前进 cursor、截断/缺字段与扫描变化；返回前 facade 再读 connector 状态/更新时间和凭证文件 inode/mtime_ns/size，变化拒绝旧结果。
- `INK_NOTION_TODAY_API_VERSION` 为必需合法日期，没有默认值；`ntn@0.15.1` 的今日子进程显式 `--notion-version`。`INK_NOTION_ALLOWED_URL_HOSTS` 由服务器配置，默认精确主机在 `.env.example`。测试注入日期，只验证协议与 subprocess 参数，未验证正常服务配置或真实 Notion API 兼容性。

| 来源 | 安全错误/状态 | 页面处理 |
| --- | --- | --- |
| Dream 会话 | `INVALID_ACCESS_TOKEN` 或本机认证边界 401 | 清除清单，提示登录；正常 App 登出回原登录 gate |
| Admin owner | connector 不可见 404 / `ADMIN_PERMISSION_DENIED` 403 | 清除列表，反馈连接/归属变化；不泄漏其他 actor |
| Admin capability/设置 | `ADMIN_CAPABILITY_UNAVAILABLE`、`ADMIN_DATA_UNAVAILABLE`、`ADMIN_UNAVAILABLE` 等 503 | 设置读取失败与刷新；只有同上下文才保留旧列表 |
| Notion 授权/读取 | `NOTION_AUTH_EXPIRED` 401 / `NOTION_PERMISSION_DENIED` 403 / `NOTION_RESOURCE_UNAVAILABLE` 404 | 清除旧列表，反馈重新连接/分享权限/不可见，不推断删除 |
| Notion 限流/上游 | `NOTION_RATE_LIMITED` 429 / `NOTION_UPSTREAM_UNAVAILABLE` 502 | Retry-After 后刷新；已有候选可返回 partial，无候选明确失败 |
| 日期/版本/上下文 | `NOTION_DATE_CONTEXT_CHANGED` 409、`NOTION_TIMEZONE_UNAVAILABLE` 503、`NOTION_API_VERSION_UNCONFIGURED` 503、`NOTION_CONTEXT_CHANGED` 409 | 日期矫正或明确失败；上下文变化拒绝旧列表 |

## 5. 首次失败与修复记录

| 检查 | 首次结果与分类 | 修复及复测 |
| --- | --- | --- |
| tsc | TS2345，visibleTabs tuple union 的 indexOf 参数收窄；实现类型缺口 | 改显式 tab union 数组；后续 tsc exit 0 |
| backend pytest 在根目录 | conftest 无法导入 `tests.legacy_persistence`，exit 4；harness 启动问题 | 从 backend 工作目录并显式 PYTHONPATH 执行；不改业务模块 |
| backend 四文件 | 31 passed / 4 failed；缺标题显示 ID 是今日投影缺陷；偏好 operation 未登记/foreign 非 UUID 为 fixture 缺口 | extract_title 增 optional fallback 保留旧默认，今日采用未命名；fake 登记真实偏好 operation，foreign 用合法未拥有 UUID；37 passed、exit 0 |
| E2E 首次 | 9 passed / 3 failed / 25 did not run，exit 1 | Vite fixture 的宽泛 API mock 拦截真实 TS 模块，造成 MIME JSON 空页：改精确 `/api/` 前缀；Calendar 重开复用既有键盘入口避免 Writing 叠层拦截；新 spec 改独立模式确保各状态执行 |
| 新旅程对照 | 快速日期 A→B→A 取消后旧 request key 可能阻止重新读；实现并发缺口 | key cleanup 清 request 标记/列表，generation 与 Abort 共同拒绝旧响应；新增 held 日期乱序测试 |
| 文档检查首次 | README.zh 中文头被检查器误报英文头缺失；checker 不兼容原文件约定 | checker 接受输入/输出/定位/同步头，不增加重复英文头；历史回执保留首次分类并补正 |
| 38-case 全量复测 | 35 passed / 3 failed；auth 投影未加载生产 CSRF、logout mock 不满足真实 DTO；tooltip 混合 hover/focus 时焦点提示可能消失 | auth fixture 使用生产 BrowserSession 读取；logout 返回 `{success:true}`；tooltip 保持当前键盘焦点提示，定向 auth 两项与视觉项通过 |
| 5-case 定向复测 | 3 passed / 2 failed；Settings 被误当为带“更多”的工作区；登录按钮名称和 `/auth/options` 未按现有协议模拟 | 使用原“返回应用”→工作区→写作入口；模拟实际 options DTO 并断言 Login enabled；等待39-case 全量复测，不更改生产导航/登录 |
| 39-case 复测中断 | 日志已开始35/39但进程随聊天中断停止，未取得终态；至少有 `/auth/options` ERR_ABORTED 诊断和1440px初始页面语法错两项失败 | Login visible/enabled 已通过；仅该旅程启用 GET options 生命周期取消分类，其余诊断仍失败。共享 helper 追加 pageerror stack，定向 trace 定位语法错；本轮不得报告39项完成 |
| 中断后的定向 trace | logout、1440px与390px滚动三项通过，exit 0；此前页面语法错未复现，原运行未采集堆栈，不能据此判断根因 | 保留未复现记录和三份 trace；复用仓库既有可选 react-grab 开发工具脚本 fixture，消除该无关外部依赖。页面错误仍按完整堆栈失败；随后重新冻结并执行39项全集 |
| 完整39项与色彩复核 | auth 2/2、tabs 28/28、scheduled 9/9 全通过，exit 0；另行采样确认 light desktop 未选图标背景透明、focus 外描边位于遮罩上 | 测量通过只表示样式收集完成，不表示对比度通过。页签改用既有不透明主题底色及内侧 focus；原 visual case 增明暗1440/390实际比值与截图，等待修正后全量回归和构建 |
| 页签色彩修正后的全集 | 39 passed、0 failed、0 skipped；37 backend tests、静态检查、构建、125%文字缩放和文档检查退出码均为0，详见 `final-adjusted-validation-receipt-20261005.md` | 最终截图再次发现 Notion 刷新/外链使用浅蓝操作色；只在 Calendar 内改用既有 primary 色，将可见操作文字加入4.5:1实际比值断言，最后源码的全集与构建待复测 |

本节保留各阶段首次失败、修复和中断事实；最终结果由§6的最后源码回执取代阶段等待状态，历史原始日志不删除。

后续独立执行的新页签 spec 首轮为 23 passed / 3 failed（并发日期修复前的运行版本）。正常“回到今天”未重新读属于上述旧 request key 缺陷；完整登出路径的用户菜单同样被既有 Writing 层拦截，改用原键盘交互；390px 长列表切栏前必须滚回非粘附导航，导致保存的滚动被覆盖，这是呈现缺口。窄屏导航已改当前栏目区域顶部 sticky，保留单一滚动 owner，待完整复测。

上述修复均已进入最终39项全集复测，结果为全通过。最后的操作文字颜色修正也已进入新的39项全集与构建，并在四种主题/宽度下测到刷新、标题外链、打开外链三项实际文字，不以只测加载按钮代替外链验证。

## 6. 最后源码、实际命令与证据

独立 Luna runner 未修改生产或测试源码。最后一轮原始回执为[操作文字修正后的最终回执](../../output/playwright/calendar-tabs-20261005/final-action-contrast-validation-receipt-20261005.md)；[前一轮回执](../../output/playwright/calendar-tabs-20261005/final-adjusted-validation-receipt-20261005.md)保留后端37项与125%布局测量。最终文档收口只修改本稿、PRD、正式设计和目录索引，不改变以下功能源码。

| 验证 | 通过 / 失败 / 跳过 | 退出码与关键输出 | 证据 |
| --- | --- | --- | --- |
| 完整浏览器生产页面/组件旅程 | 39 / 0 / 0 | 0；`39 passed (1.2m)`；39 trace | [原始日志](../../output/playwright/calendar-tabs-20261005/latest-action-39.log)、[HTML报告](../../output/playwright/calendar-tabs-20261005/latest-action-39-report/index.html) |
| 后端公开router/facade/driver合同 | 37 / 0 / 0 | 0；`37 passed in 1.10s` | [pytest日志](../../output/playwright/calendar-tabs-20261005/adjusted-backend-pytest.log) |
| 明暗1440/390色彩定向 | 1 / 0 / 0 | 0；`1 passed (4.4s)`；操作文字最低light 8.021247182950265、dark 12.655299079446777 | [visual日志](../../output/playwright/calendar-tabs-20261005/latest-action-visual.log)、[明色桌面JSON](../../output/playwright/calendar-tabs-20261005/latest-action-contrast-light-1440.json)、[暗色窄屏JSON](../../output/playwright/calendar-tabs-20261005/latest-action-contrast-dark-390.json) |
| 125%文字缩放390×844组件测量 | 1 / 0 / 0 | 0；root20px、doc/body宽390，无水平溢出，页签/tooltip/关闭/月历入口可达 | [原始JSON](../../output/playwright/calendar-tabs-20261005/calendar-font-scale-125-measurements.json)；仅此组件与比例，不声明200%或全站认证 |
| TypeScript / ESLint | 通过 / 0 / 0 | 均0 | [tsc](../../output/playwright/calendar-tabs-20261005/latest-action-tsc.log)、[eslint](../../output/playwright/calendar-tabs-20261005/latest-action-eslint.log) |
| production build | 通过 / 0 / 0 | 0；Next16.1.6编译、TypeScript成功，静态页3/3 | [build日志](../../output/playwright/calendar-tabs-20261005/latest-action-production-build.log) |
| Markdown/目录/引用/头部/历史 | 通过 / 0 / 0 | 0；源码阶段50份changed Markdown、203本地引用、5/5 HEAD历史快照一致；收口后再检查现行清单和所有新增引用 | [源码阶段文档日志](../../output/playwright/calendar-tabs-20261005/latest-action-doc-check.log)、[最终收口文档日志](../../output/playwright/calendar-tabs-20261005/final-doc-closure-20261006.log) |
| 正式设计Mermaid三图 | 3 / 0 / 0 | 0；Mermaid11.17.2语法解析并Chrome渲染正常/异常/状态图 | [图示日志](../../output/playwright/calendar-tabs-20261005/mermaid-render-ui-final-20261005.log)；本轮只修正文与色彩表，图示未变 |
| 真实Notion账户/正常服务/模型 | 未执行 | 在本轮隔离技术范围之外，不计入39项 | 不能据此声明上游兼容性或真实业务验收 |

实际命令（工作目录均在本仓库，完整外壳和所有参数以原始回执为准）：

```bash
# frontend
corepack pnpm exec tsc --noEmit --incremental false
corepack pnpm exec eslint app/_dream/components/CalendarPopup.tsx app/_dream/components/CalendarNotionPanel.tsx app/_dream/components/NotionMark.tsx app/_dream/components/chat/Modal.tsx app/_dream/api/notionTodayApi.ts app/_dream/api/resourceConnectorApi.ts app/_dream/components/dashboard/ConnectorNotionDetailPage.tsx e2e/calendar-right-panel-tabs.spec.ts e2e/scheduled-task-calendar.spec.ts e2e/calendar-auth-context.spec.ts e2e/fixtures/calendarHarness.ts
E2E_WEB_BASE=http://127.0.0.1:55173 PLAYWRIGHT_HTML_OUTPUT_DIR=../output/playwright/calendar-tabs-20261005/latest-action-39-report corepack pnpm exec playwright test e2e/calendar-auth-context.spec.ts e2e/calendar-right-panel-tabs.spec.ts e2e/scheduled-task-calendar.spec.ts --trace=on --reporter=html --workers=1 --output=../output/playwright/calendar-tabs-20261005/latest-action-39-results
NODE_ENV=production corepack pnpm run build
# backend
PYTHONPATH=/Users/dmeck/project/ink-dream-memory/backend .venv/bin/python -m pytest tests/test_notion_today.py tests/test_notion_operations.py tests/test_notion_connector_router_flow.py tests/test_admin_notion_connector_data.py -q
# repository root
python3 output/playwright/calendar-tabs-20261005/doc_checker_all_20261005.py /Users/dmeck/project/ink-dream-memory
git diff --check
```

URL userinfo修复后的 `today.py` SHA256为 `1e5bd511794ec886d45112cd6a1535029dce1ac5bb51868c3066b0dd181f850f`，对应测试为 `916b6133f30da27b712ede20f5c99bbc62fbcacceb1c0ccf5928b2354da158d9`。最后CSS为 `aac14692f5ac59921310f8b98ba72dab31f1471b896f5ef9f1c6b3d30cf83ced`，visual spec为 `57f954314c766c4d7957049029d573408fcff4939b54ac2402f86eab2077128c`。

## 7. 文档、清理与Git交付

- 现行PRD位于 `docs/prd/calendar/`，正文含桌面和窄屏骨架；正式设计正文含正常、异常恢复与状态三图。R01–R14矩阵关联真实模块/接口/测试。两份README、受影响目录合同与文件头已同步。
- 原2026-10-04设计阶段、实施前完整PRD/UI、任务/日记/连接器旧稿与所有阶段失败证据均保留。旧路径有现行指引；不删除仍有业务责任的文档或程序。
- 只结束本轮命名的Next/Chrome进程。55173最终零监听；原 `frontend/.next` 已恢复，测试构建保存于output；没有残留backup或 `tsconfig.tsbuildinfo`。未启动或修改真实backend、数据库、账户、凭证、账本、模型及用户服务。
- Git仍为 `develop` / `dc5c7723f28bc75efe55f7573182fe857782dbdf`，无提交、无PR；保留用户原有未提交内容，本轮代码与文档留在共享工作区供复核。未擅自修改正常 `.env` 或部署服务。
- 后续正常配置/真实账户验收须使用实际支持的API日期和用户指定账户；不能用隔离fixture结果替代，也不重新要求确认已接受的Search范围。

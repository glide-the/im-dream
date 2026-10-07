<!-- [Input] 用户长等待、历史日期查询及快照优先要求；Git 和源码调查。 -->
<!-- [Output] 本轮影响、设计评审、失败修复和验证回执。 -->
<!-- [Pos] exec 过程证据；PRD/正式设计仍为现行规范。 -->
<!-- [Sync] 2026-10-06: 建立影响边界；实现与验证待执行。 -->
<!-- [Sync] 2026-10-06: 追加重启后旧数据库索引排查、公开同步恢复及数据库完整旅程回归。 -->
# Notion 日历快照优先修复

## 影响评估

- Git develop，基线 dc5c7723f28bc75efe55f7573182fe857782dbdf。已有广泛日历实现和文档未提交改动，全部保留，不回退或格式化无关文件。
- 本轮文件所有权：backend/notion 的 today、factory、operations、sync；notion router；CalendarNotionPanel、notionTodayApi、i18n；对应测试、README 镜像、现行 PRD/设计、文件头与目录清单。共享 Admin DTO/schema、Chat/任务状态机、Agent body hook 不变。
- 已复用 SnapshotStore/current index、当前选择过滤、actor facade/credential Provider、现有 API transport、图标、Tokens 和 Playwright harness。问题是当前日历绕过快照运行 Search，轻量索引未保留创建时间、独立页面同步使用旧选择元数据。
- 呈现调整：日期文档标题、同步时间、校验状态；数据调整：现有 JSON index 增加原始 created_time/last_edited_time；接口增加快照/校验参数及版本检查。无数据库合同迁移。
- 定时任务、精确结果、编辑/历史 Modal、日记删除、Thread/Chat 草稿导航保持；新读取不 select/sync/body/write。仅连接器同步会刷新索引元数据。
- Project/Episode/canonicalArtifact、Run .dream、after-turn Hook、Gateway/模型均不在范围。最终 UI consumer Calendar 变更；现有任务日记 API/持久化保持。
- 回归：日历全旅程、任务/日记已有全旅程；快照/历史/今天两阶段、字段缺失、权限/限流/网络、版本/日期/凭证并发、隐藏/关闭/登出、午夜、DST 和无写入副作用。
- 使用 backend tests fake Admin/OAuth + 临时 actor 目录；浏览器用 production Next、隔离具名端口、已安装 Chrome 和 e2e fixtures。仅清理本轮资源，不停止用户服务。技术验证不是正常真实账户验收。
- 能力边界：范围为当前连接器已索引且仍选中的资源；新页面和未记录变化依赖连接器同步，旧索引缺创建时间需同步。历史只展示创建，不能完整还原历史编辑。严格全集仍无完整枚举能力，但已不作为用户最新资源范围。

## 设计门禁

[现行 PRD](../prd/calendar/calendar-right-panel-tabs-prd.md)与[正式设计](../design/claude-agent/calendar-right-panel-tabs-ui-design.md)已按最新要求更新，旧全文单独保存。[独立评审](./notion-calendar-snapshot-design-review-20261006.md)结论可实施，已闭合上下文分类和同步元数据 API 日期两项门禁；其后才编写实现。现已完成生产代码和回归用例，实际验证正在执行。

## 验证回执

Luna 已执行首轮：tsc/build exit 0；eslint exit 0（初次 today 依赖 warning 随后修正）。后端首轮 exit 4：不存在的 test_notion_sync_policy.py；去掉该路径后 exit 2：fixture 导入前置失败，均没有执行断言。浏览器 43 项：29 通过/14 失败，exit 1。

分类及修复：一个实现缺陷，A→B→A 时 verifiedRef 保留旧标记导致再次 pending 没有启动校验，已在日期/身份清理与 connector invalidate 同步重置。其余失败是 harness 使用旧 /notion/today 诊断规则，不能识别具名 /notion/documents 故障注入/取消，以及登录/连接文案未更新。测试仅在允许的 e2e/tests 目录修正；后端 fixture 使用既有测试目录导入方式，未修改生产 OAuth。首次原始输出保存在 output/notion-calendar-snapshot-20261006/，复测待执行。

收尾审查：服务端 URL 策略原默认遗漏官方 page.url 的 app.notion.com，已加入精确默认主机（仍保留配置覆盖、安全校验）；API 不可表示的次日边界（9999-12-31）明确 400。追加后端回归验证，前端逻辑未随该收尾变化。

## 最终技术验证（2026-10-06）

执行人为 `luna_test_runner`，使用本机已安装 Chrome，无数据库迁移、外部 Notion/模型调用或正常业务记录写入。

| 检查 | 实际命令（相对对应工作目录） | 退出码与结果 |
| --- | --- | --- |
| backend 合同 | `PYTHONPATH=/Users/dmeck/project/ink-dream-memory/backend .venv/bin/python -m pytest tests/test_notion_today.py tests/test_notion_operations.py tests/test_notion_connector_router_flow.py tests/test_admin_notion_connector_data.py tests/test_notion_snapshot_contract.py tests/test_notion_snapshot_store.py tests/test_notion_sync_scheduler.py -q` | 0；55 passed, 6 subtests passed，1.73s |
| frontend TypeScript | `corepack pnpm exec tsc --noEmit --incremental false` | 0 |
| frontend ESLint | `corepack pnpm exec eslint app/_dream/components/CalendarNotionPanel.tsx app/_dream/api/notionTodayApi.ts app/_dream/i18n.ts` | 0；无 errors/warnings |
| frontend production build | `NODE_ENV=production corepack pnpm run build` | 0；编译、类型和页面生成通过 |
| frontend 完整旅程 | `E2E_WEB_BASE=http://127.0.0.1:55173 corepack pnpm exec playwright test e2e/calendar-auth-context.spec.ts e2e/calendar-right-panel-tabs.spec.ts e2e/scheduled-task-calendar.spec.ts --trace on --reporter=html --workers=1 --output /Users/dmeck/project/ink-dream-memory/output/notion-calendar-snapshot-20261006/playwright-test-results-second` | 0；43 passed，1.1m |
| Mermaid | `node output/playwright/calendar-tabs-20261005/mermaid_render_ui_20261005.cjs` | 0；现行正文 3/3 parse/render，无失败 |
| 文档 | `python3 output/playwright/calendar-tabs-20261005/doc_checker_all_20261005.py /Users/dmeck/project/ink-dream-memory` | 0；第二轮 255 links、0 missing/header failures；桌面/窄屏/层级均通过，既有历史 SHA 5/5 一致 |
| diff | `git diff --check` | 0，无输出 |

日志位于根 `output/notion-calendar-snapshot-20261006/`：`backend-final.*`、`tsc-second.*`、`eslint-second.*`、`build-second.*`、`e2e-second.*`、`mermaid-second.*`、`doc-validation-second.*`、`diff-check-second.*`。首轮全部保留，没有覆盖；HTML report 与 traces 保留。正文最终更新后再执行文档/diff 检查，最终日志使用 final 后缀。

## 旅程矩阵与实际范围

| 旅程 | 结论 |
| --- | --- |
| 日历打开、默认日期/栏目、切栏、换日、关闭重开、输入/结果/滚动保留 | 通过 |
| tab/tabpanel、手动键盘、焦点陷阱、hover/focus tooltip、明暗/窄屏及对比度 | 通过 |
| 安排未发送 Chat 草稿、列表、编辑成功/失败/revision冲突、立即运行、历史分页、精确结果、执行 Thread、暂停/恢复、删除/撤销 | 通过；原任务生产入口/DTO和既有 harness，未复制状态机 |
| 日记选择/列表/打开/返回、当前标记及原删除确认 | 通过 |
| 连接/授权/归属 → 快照筛选计数 → 今天更新项只读校验 → 外链/刷新/切走返回 | 通过；隔离 metadata Provider，非真实账户验收 |
| 历史日期、DST 23/25h、起点包含/终点排除、双标识只计一次、规范身份去重、缺标题/时间、partial 已知0 | 通过 |
| 未连接/授权未完成/失效、权限拒绝/删除、无索引候选/无日期命中、metadata mismatch、超时/网络/上游异常/429及 Retry-After | 通过 |
| 慢校验期间快照可用、隐藏阶段不发新校验、快照/凭证/归属变化、A→B→A、登出/关闭迟到响应、跨午夜 | 通过 |
| 重复查看/刷新不 Search/select/sync/body、不产生配置或业务写入 | 通过；资源同步由原显式同步路径独立负责 |
| 正常真实账户/Notion服务链路 | 未执行；本轮技术自动化不能称为真实业务验收 |

## 文档与隔离资源

现行 PRD 正文含桌面/窄屏骨架；正式设计正文含正常、异常、状态三图。连接器当前稿和任务/日记导航补充同步；4 份 pre-snapshot 全文历史新增且不覆盖前次历史。`overview.md` 为历史基线，本轮曾尝试补充但已完全撤回新增内容，最终保持原文；现行规则归当前连接器/日历正文。

自建 Next 55173 已停止，无 listener；临时测试 actor 目录由 fixture 清理，未创建数据库或外部资源。测试清理首轮误删了 4 个 tracked frontend/test-results 基线文件，已恢复并逐个与 HEAD blob hash 核对一致（初始工作区这些文件无修改状态）；具体名单及 hash 见 `tracked-test-results-final.keyoutput.log`。该失误保留为 harness 证据。

生产构建使用现有 frontend/.next，未采集 pre-build hash/备份，因此不能声明已恢复原 .next。保留标准构建产物，不删除未知用户生成物。既有 5173（PID 9971）和 8765（PID 9739）进程均未停止/重启；不把进程存在当成业务验收。

## 当前服务与完成边界

主 Agent 只读检查：正常 8765 的 `/openapi.json` HTTP 200，**未加载 `/api/connectors/{connector_id}/notion/documents`**；正常 5173 `/story-workspace/writing` HTTP 200。当前后端仍为旧进程，源代码修复尚未在正常服务生效。须按正常配置重启 Dream 后端，再刷新页面；旧索引缺创建时间时需要在连接器设置显式同步一次。不得用隔离服务代替正常链路。

代码和隔离自动化已通过；正常服务切换及用户实际连接的验证仍待完成，不宣称整体功能已在用户运行服务验收。Git develop / dc5c7723f28bc75efe55f7573182fe857782dbdf；本轮没有 commit、push 或 PR，保留原有全部未提交工作。实施任务仍为 `01a10c81-1077-7bf1-8973-fee93a49936e`，其此前 Search 范围技术完成状态不能代替此次快照范围的正常服务验收。

## 数据库页面为空的后续排查（2026-10-06）

优化后的执行提示词：核对“选择数据库 → 同步索引 → 日历显示数据库内页面”完整链路；保留当前数据库行的资源范围和日期筛选，修复具体缺口，不恢复日历 Search 或正文同步。交付数据库选择公开入口回归、正常服务的实际结果和同步恢复证据。

影响评估：基线仍为 develop / dc5c772，保留现有全部 dirty 文件。本阶段拥有 `backend/tests/test_notion_today.py` 的数据库完整旅程补充与本回执、相关现行文档说明。数据库选择、同步策略、Admin DTO、私有 actor 快照和 Calendar 是链路参与者；数据库行已由 `build_canonical_snapshot` 加入 `index` 和 `database_pages`，无需扩大已选权限。任务、日记、Chat、Project/Episode/Run-private `.dream`、Hook 与 PostgreSQL 业务投影均不涉及。Calendar 仅消费索引，不承担同步写入；现有显式同步入口负责更新 actor 快照及正常 Admin 记录。

只读证据：用户重启后，正常 8765 OpenAPI 已包含 documents 入口。用户所指连接器的私有当前快照包含 7 个数据库、319 个页面，319 行都只有 page_id/title/url/last_edited，没有 created_time/last_edited_time；快照 fetched_at 为 2026-10-06T06:21:55Z，早于当前后端启动时间（本机 14:24:16）。重启不会重建持久化快照，旧轻量索引不能按创建日期推算。实际页面标题、正文和凭证不写入回执。

验证矩阵：公开数据库选择执行实际 snapshot builder（仅注入远程 operations）→ 分页与原始时间 → 持久化 → Calendar 当日及历史读取 → 重复刷新不查询数据库/body/选择；删除选择后范围过滤。隔离 fixture 的 actor 根仅清理自身。正常本机检查使用用户当前连接器和已登录会话，至多执行既有显式同步，不修改选择或策略，不停止服务，不清理真实同步记录。

### 实际原因和恢复

本次是旧持久化索引的数据缺口，数据库枚举和当前生产投影已符合目标，无需制造新的生产实现分支。主 Agent 在现有 Chrome 的独立标签，使用正常 localhost:5173/8765 服务及用户当前会话，从“资源链接 → Notion → 管理已挂载来源 → 立即同步”执行一次公开同步。原用户 Chat 标签未导航或中断；数据库选择、同步频率和授权未修改。

同步成功后，正常 Settings 显示 7 个来源、最近成功 14:29；私有 current.json 的 fetched_at=2026-10-06T06:29:31Z，snapshot_version=snap-20261006T062931Z-5cc3f06c。仍有 319 个唯一页面，319 行均有上游 created_time 与 last_edited_time，pages 保持空。日历今天显示 2 个页面（当日创建 1、今天编辑 1），切到 10 月 5 日显示创建 2 个页面，无历史编辑组；历史刷新后返回今天结果一致。实际标题和正文不写入文字回执。

Chrome CDP 仅观察该标签的公开 API，保存 URL/方法/状态/耗时，不保存请求头、Cookie、凭证或响应正文：

| 操作 | 公开请求 | 状态 | 请求到响应头耗时 |
| --- | --- | --- | --- |
| 历史刷新 | `GET /api/connectors/{id}/notion/documents?date_key=2026-10-05` | 200 | 108 ms |
| 返回今天快照 | `GET /api/connectors/{id}/notion/documents?date_key=2026-10-06` | 200 | 142 ms |
| 今天更新项校验 | 上述 GET 加 `validate_remote=true&snapshot_version=...` | 200 | 2229 ms；快照先显示 |

正常服务证据在 `output/notion-database-calendar-20261006/normal-api-history.json`、`normal-api-today.json`、`normal-calendar-today.jpg`、`normal-calendar-history.jpg`。这是用户所指连接器的正常服务恢复检查，不扩充为完整真实模型/任务/日记业务验收。保留真实同步产生的正常 Admin 记录及快照，未清理用户数据。主 Agent 的只读统计脚本首次因多余右括号 exit 1，修正后 exit 0；没有业务请求或数据写入。

### 数据库链路技术回执

执行人为 Luna；测试通过 CLI transport 依赖注入，调用公开 router、严格 Admin DTO、实际 builder 与 SnapshotStore，不复制生产状态机。旧 connector harness 的整体 builder mock 在新增类中显式解除，消除此前只凭预置快照验证数据库链路的覆盖缺口。

| 命令（backend 工作目录，PYTHONPATH 为仓库 backend 绝对路径） | 退出码 | 结果 |
| --- | --- | --- |
| `.venv/bin/python -m pytest tests/test_notion_today.py::DatabaseSelectionCalendarJourney -q` | 0 | 2 passed，1.16s |
| `.venv/bin/python -m pytest tests/test_notion_today.py tests/test_notion_operations.py tests/test_notion_connector_router_flow.py tests/test_admin_notion_connector_data.py tests/test_notion_snapshot_contract.py tests/test_notion_snapshot_store.py tests/test_notion_sync_scheduler.py -q` | 0 | 57 passed，6 subtests passed，1.68s |
| `python3 output/playwright/calendar-tabs-20261005/doc_checker_all_20261005.py /Users/dmeck/project/ink-dream-memory`（根目录） | 0 | 255 links、0 missing/inventory/header failures；历史 SHA 5/5；骨架通过 |
| `git diff --check`（根目录） | 0 | 无输出 |

回执目录 `output/notion-database-calendar-20261006/` 内的 database-journey、backend-regression、doc-check、diff-check 各保存 command/log/exit/keyoutput。新增用例覆盖数据库分页、原始时间、双分组、历史创建、只读刷新、取消选择与旧索引公开同步恢复，未失败或跳过。本阶段未改 frontend 业务代码或生产状态机，不重复此前已经通过的 43 项浏览器旅程与构建；上方原始回执保留。现行 PRD、正式设计、README 双语及目录合同补充数据库页面范围与重启后显式同步恢复。最终文档/README/Mermaid 复核另存 final 后缀。

本阶段无自建进程、端口或数据库；临时 actor fixture 清理完成。正常服务保持运行，独立 Chrome 标签保留在日历今天列表供复核。Git 仍为 develop / dc5c772，无新增 commit、push 或 PR，未覆盖无关改动。本次“数据库页面为空”的具体问题已恢复并有接口、UI 与完整数据库链路回执；此前整个项目的目标状态不以本次局部检查代替。

最终文档检查 exit 0（39 新文件、255 引用、清单/文件头/路径 0 失败、历史 SHA 5/5）；README 双语检查 exit 0（15 标题、6 代码块、命令块及 22 链接一致，数据库恢复说明两种语言均 4/4）。正式设计当前 3 个 Mermaid 图没有改动，复用既有 3/3 渲染回执，最终图数量检查 exit 0；无需重复起浏览器。README 检查脚本首次正则转义错误、Mermaid 检查脚本首次正则组号错误属于 harness 失败，修复检查脚本后分别 exit 0；首次日志保留 readme-parity-final-harness-failure、mermaid-final-harness-failure 后缀，没有修改生产或设计图。最终 diff exit 0，55173 无残留 listener。以上补充后再检查文档与 diff，收尾回执使用 close 后缀。

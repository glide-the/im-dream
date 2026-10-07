<!-- [Input] UI v2.pdf 第5页、现行 calendar PRD、正常页面和共享工作区基线。 -->
<!-- [Output] Calendar 右侧无边框视觉调整的影响、设计门禁及追加式测试回执。 -->
<!-- [Pos] 本轮执行证据；完成状态必须以实际实现与验证回执为准。 -->
<!-- [Sync] 2026-10-06: 实施前记录影响和阶段1产物，后续设计/评审/实现/验证尚未完成。 -->
<!-- [Sync] 2026-10-06: 四阶段与正式稿规格已交付；保存正式稿完整历史，独立评审/实现/验证仍待执行。 -->
<!-- [Sync] 2026-10-06: 独立评审可实施，右侧 CSS 与隔离 E2E 视觉源码完成；Luna 实际验证待执行。 -->
<!-- [Sync] 2026-10-06: 追加删除标签换行修复、真实首帧焦点实验及48/48技术回归；最终文档检查与隔离清理待回执。 -->
<!-- [Sync] 2026-10-06: §10.1 收口回执已完成文档检查、48/48 provider-free 技术回归和自建资源清理；当前 UI 实现与隔离验证完成，真实业务验收仍未执行。 -->
# Calendar 右侧无边框视觉调整：影响与执行记录

## 1. 当前结论与依据

用户定位 `CalendarPopup.tsx` 的 `calendar-popup__workspace` 并要求简约留白、无边框。[UI v2.pdf](../prd/Ink%20%26%20Memory%20UI%20Design%20v2.pdf) 第5页 §5.4 定义少面板、多留白，以字号字重替代边框/阴影、静止条目无卡片。此区域采用用户明确无边框要求，不追加 PDF 一般页面级虚线。阶段1记录时后续设计尚未完成；现阶段四份设计、[独立评审](./calendar-borderless-ui-design-review-20261006.md)及右侧 CSS/测试源码已完成；Luna 完整三份浏览器旅程 48/48、最新 TypeScript/ESLint 和既有冻结生产源码 build 均有 exit 0 回执。§10.1 已记录最终 Markdown/引用/header、README parity、Mermaid、diff 检查及自建资源清理。本轮 UI 实现及 provider-free 隔离自动化技术验证完成，没有执行真实账户或真实模型验收。

## 2. 实施前影响评估

| 项目 | 当前事实与本轮边界 |
| --- | --- |
| Git 基线 | `develop`，HEAD `dc5c7723f28bc75efe55f7573182fe857782dbdf`；仓库存在广泛未提交任务/日记/Notion 改动，本轮保留，不回退或格式化无关文件。 |
| 文件所有权 | 阶段1/4 Agent：本 exec、现行 PRD/正式稿与完整历史、workflow 阶段文件及相关目录；阶段2/3 Agent：相应结构/层级文件。后续同一实施 worker 持有 `CalendarPopup.css` 右侧视觉、必要文件头/组件目录及 E2E 视觉断言，主 Agent 审阅/接收；Luna 执行确定性验证。测试差异仅允许 frontend/e2e 或具名脚本。 |
| 现有页面和组件 | 复用 CalendarPopup、CalendarNotionPanel、图标组件、既有 tooltip、Modal、菜单和所有 DOM；section 的大圆角、装饰 border、双层 shadow，页签未选实底、日记卡片是当前视觉差距。左月历不扩大、不重绘。 |
| 状态 owner | CalendarPopup activeTab/focusedTab/tooltip、selectedDate、安排输入、任务 LIST/RESULT/历史编辑 owner 均保留；Notion 的 actor/date/connector/snapshot/request guard 与缓存 owner 不变。 |
| 视觉调整 / 业务缺口 | 只调整呈现：右侧平坦 paper 底、无装饰外框/阴影、无未选页签实底、文字层级与间距。没有新增字段、接口、错误分类或持久化需求。focus outline、输入/菜单功能识别边界不被误删。 |
| 接口、权限和数据 | 不改公开 API、Admin 归属、Notion 授权、资源范围、时区、数据库行枚举、快照先显/今天更新项校验及任何文案；不改变正文读取权限，不 select/sync/body/write。 |
| 既有旅程风险 | CSS 作用域误伤左月历/原 Modal；日记选中态可读性；task RESULT 和长内容滚动；隐藏面板、tooltip 溢出/焦点；窄屏 header 操作布局。任务运行/安排/编辑/历史/删除撤销、日记打开/删除、Chat/Thread 导航应保留。 |
| 测试数据、隔离资源 | 复用当前 Calendar 公开入口和 `frontend/e2e/fixtures/calendarHarness.ts` 真实 DTO 的 DI harness；新场景覆盖三个栏目和长内容。使用已安装 Chrome；具名端口、输出目录由 runner 记录。只清理本轮自建资源，不停用户服务；真实账号截图不冒充完整真实业务验收。 |
| 不涉及模块 | Project、Episode、Run、Hook、Agent runtime、数据库 schema、Admin 合同、API、连接器同步/策略、Chat 业务不变。无跨项目依赖任务。 |
| 当前门禁 | 阶段1/2/3/4及正式稿同步已交付，独立评审可实施；CSS 与 E2E 已完成，48/48 旅程及必要静态/build 通过；§10.1 已完成最新文档检查和自建资源清理。没有资源全集/API 能力变更，原快照范围保持。 |

## 3. 正文与历史保留

- [现行 PRD](../prd/calendar/calendar-right-panel-tabs-prd.md)正文已加入桌面/窄屏无边框骨架、normal/hover/selected/focus 规则和视觉验收矩阵；原任务、日记、Notion 合同保留。
- [调整前完整 PRD](../prd/calendar/calendar-right-panel-tabs-prd-pre-borderless-20261006-history.md)按字节拷贝，SHA256 `01d756792acbc4e8e680a6bcec89f7be75c4c04a1142a3e1f8ca4262d79606b8`；其它历史原文不修改。
- [阶段1 PRD 草案](../design/claude-agent/calendar-borderless-ui-workflow-20261006/workspace/1_prd_draft.md)是过程证据，不能代替 PRD 骨架或正式稿正常/异常/状态图。
- [正式交互设计稿](../design/claude-agent/calendar-right-panel-tabs-ui-design.md)正文已同步视觉规格，原业务图保留并与 PRD 一致。

## 4. 必要回归矩阵（执行前）

| 旅程/状态 | 范围 | 执行状态 |
| --- | --- | --- |
| 打开 → 默认 → 三页签 → 换日 → 关闭重开 | 唯一面板、原日期、草稿、LIST/RESULT、同日滚动 | 待执行 |
| 任务 LIST/RESULT / 原编辑历史操作 | 行层级、安排输入、操作按钮、长结果滚动、原 Modal/focus owner | 待执行 |
| 日记列表 → 打开 → 返回 / 当前与删除 | 透明行、当前文字/active、原入口与撤销 | 待执行 |
| Notion 快照 → 校验 → 组别 → 外链/刷新 | 原文案/数据不变，组距/长标题/状态与正文滚动 | 待执行 |
| 键盘 / tooltip / hover / selected | 手动激活、可见 focus、不裁切、未选透明、无静态卡片阴影 | 待执行 |
| 主题与视口 | 浅/深色，390 / 430 / 1024 / 1440px，长内容与操作不溢出 | 待执行 |
| 静态与文档 | TypeScript、相关 ESLint、必要 build、Markdown 清单/引用、Mermaid、diff check | 待执行 |

## 5. 实际命令与回执

设计输入和代码搜索已执行；四阶段设计未运行测试、未写生产代码、未启动自建进程。后续由 `luna_test_runner` 追加实际命令、退出码、首次失败、修复、复测和隔离清理，不以计划代替回执。

## 6. 顺序设计交接（2026-10-06）

阶段2交付[结构草图](../design/claude-agent/calendar-borderless-ui-workflow-20261006/workspace/2_structure_sketch.md)，阶段3交付[层级映射](../design/claude-agent/calendar-borderless-ui-workflow-20261006/workspace/3_hierarchy_layout.md)，阶段4交付[现有 CSS 视觉规格](../design/claude-agent/calendar-borderless-ui-workflow-20261006/workspace/4_ui_design.md)。阶段4所有权为这些过程文件、相关目录清单、现行 PRD/正式稿的必要同步和本节追加；生产 CSS 与 E2E 留待独立评审后交给实施 worker。

正式交互稿 §4.1–4.4 直接交付 selector/Token/间距、主题、原断点/滚动与验收；PRD 和阶段1修正 1024px 已堆叠、窄屏原外层滚动。workspace 保持透明，tabs/当前 section 是连续 opaque paper，alpha hover/active 按该纸底合成；普通 header/行/RESULT 装饰线取消，功能控件、焦点、tooltip/menu、独立 Modal 保留。

正式视觉修改前完整稿保存为[pre-borderless 历史](../design/claude-agent/calendar-right-panel-tabs-ui-design-pre-borderless-20261006-history.md)，SHA256 `f0ede490ab078175a215c2cabd03467ef765b82315ebd28d76ecf78f0640c4a8`。原三幅 Mermaid 的合并原文 SHA256 为 `b0c2bff6ebdb30cee301920ab6d0ed7eaff19e2d6ac226678bd529941ffcb359`，仅作为历史保存记录，语法与渲染仍待验证。其它历史文件未修改。

待主任务进行独立评审后实施并提交实际技术回执。本阶段 CSS 片段仅在 Markdown 中，未修改生产代码；没有把设计文档交付称为实现或业务验收。

## 7. 实施源码交接（2026-10-06，待验证）

Optimized Prompt：按可实施的现行 PRD/正式稿修改现有右侧 CSS 定义，保留全部业务/API/数据/文案/状态 owner；修正隔离 E2E 视觉差距，复用实际公开入口与 DTO，冻结生产源码交给 Luna 执行必要验证。交付项：scoped CSS、必要文件头/目录/README 镜像、完整旅程保留和实际合成视觉断言源码。

`CalendarPopup.css` 改为 workspace gap=0、tabs/current section 连续 opaque paper；未选 tab 透明、selected active；标题/普通任务日记撤销行/RESULT 的装饰线框与静态阴影取消，水平对齐和组/行留白按正式稿落实。原两级 media 仅为左月历保留圆角/阴影，不再给右侧加回卡片。原左月历、独立 editor/history Modal、功能按钮/输入/tooltip/menu 样式和所有滚动 owner 不变；`CalendarPopup.tsx` 只增加文件头说明，没有行为修改。

原三份完整 E2E 旅程保留。`scheduled-task-calendar.spec.ts` 区分左月历原 border/shadow 与右侧 0，并检查 RESULT 纯分隔线为无。`calendar-right-panel-tabs.spec.ts` 扩展24个三栏目/四宽度/浅深主题组合的 normal/hover/selected/focus、长标题、当前日记标记、对齐/视口/操作触达；增加长快照滚动与系统媒体 Token 场景，原同日 scroll 回归覆盖四宽度。`calendarHarness.ts` 仅提供真实 DTO 长标题与实际 canvas alpha 合成：先找到 opaque ancestor，再按真实背景层绘制；遇到未测图像/filter/opacity 或无 opaque ancestor 报错。selected 文字 4.5、未选图标/focus 3、tooltip/Notion 元数据动作文字 4.5 阈值保持，未用降低阈值或测试实底掩盖失败。

README 英中同段一句呈现事实与相关目录/文件头已同步。本阶段未执行测试/构建、未启动或清理进程；生产 CSS/TSX 已冻结供 Luna 在具名独立副本构建，实际命令/退出码与失败修复另行追加。截图、文档检查或未执行的断言源码均不称为完整真实业务验收。


## 8. 失败、修复与证据（追加，不覆盖前述阶段）

Optimized Prompt：根据实际截图和失败回执修复最小布局缺陷；以真实公开入口和 DTO 记录焦点时序，证明并补齐 harness 就绪前置，保留生产业务及键盘优先合同；由 Luna 重跑受影响完整旅程、静态检查和最终文档/清理，按实际退出码收口。

### 8.1 日记删除标签换行：实际呈现缺陷

首次截图 `output/calendar-borderless-ui-20261006/visual-report/data/5de95029999703ffbd24de1cc6b7c63680c4726a.png` 的 diary/light/1440 normal 中，“删除”被长标题挤成两行。原因是既有 flex 行中删除按钮可以收缩。只在 `.calendar-popup__diary-delete` 添加 `flex: 0 0 auto` 和 `white-space: nowrap`，保留原字号、42px 最小命中区、危险 hover、文案与点击行为；标题 min-width/ellipsis 保持。未修改 TSX 行为、API 或状态 owner。

实际文本单行断言以 `Range.selectNodeContents(button).getClientRects()` 的 top 差值不超过 1px 为准，覆盖日记完整旅程及24视觉组合内全部8个日记主题/宽度场景。复测 scoped3 中日记与24视觉场景通过；主任务复核修复后 diary/light/1440 与390截图确认单行和右侧连续无边框纸底。保留修复前后截图清单：`visual-evidence-before/manifest.json`、`visual-evidence-after/manifest.json`，均位于本轮输出目录。

### 8.2 tooltip 首次失败与测试焦点就绪修正

删除样式修复后的 scoped3 命令 exit 1：2 passed、1 failed。原 Calendar 旅程在 `notion.hover()` 后期望日记 tooltip，收到 Notion（当时源码124行）；保存 `scoped-tests-final.command.log`、`scoped-tests-final.exit.log`、`scoped-tests-final.log` 及 `scoped-results/.../error-context.md`。该首次失败没有焦点事件/trace，不能唯一归因。随后带事件诊断的单用例通过，仅证明那次运行中日记保持焦点，不能用重试通过代替原因分析。

源码事实：既有 `Modal.tsx` 通过原 `requestAnimationFrame` 将 Calendar 的 `monthPrevRef` 聚焦；旧 `openCalendar` 只等待 dialog visible，尚未等待该初始焦点。生产 tab `onBlur` 清空焦点 owner、鼠标 hover 使用实际键盘 owner 的规则未改。

具名受控用例 `controlled initial Modal frame proves calendar focus readiness before tab interactions` 仅在测试 beforeOpen hook 暂存原 RAF callback，公开打开 → tasks/ArrowRight → 放行原 RAF；`finally` 恢复 RAF/cancelRAF 并清理本实验队列。实际 `calendar-initial-frame-focus-evidence.json` 记录 releasedCallbacks=1：651ms 放行前 active/tooltip=日记；657ms 日记 focusout 的 relatedTarget=“← 上个月”，原 monthPrev 聚焦；800ms hover Notion 时 active=monthPrev、tooltip=Notion；995ms ready 后再次 tasks/ArrowRight/hover，active/tooltip=日记。该证据证明可复现的初始焦点前置竞态，不把无事件的首次随机失败写成唯一已证实根因。

共用 `openCalendar` 现在默认等待既有“← 上个月”实际 `toBeFocused()`，没有主动覆盖生产初始焦点、sleep、force click 或改 Modal。原完整旅程保留手动激活、任务仍选中、日记焦点和 tooltip 优先全部断言。变化只位于允许的 `frontend/e2e`；新增一个机制验证用例，因此完整三份 spec 由47变48。受控实验与原 Calendar 旅程实际 2/2 通过，随后完整48/48通过。

### 8.3 已修复的验证前置问题

早期隔离 Next 启动参数将 `--hostname` 误作目录，exit 1；改用 runner 的具名 Next 启动方式后运行。另一次 E2E 回执使用相对输出路径导致命令未启动（`e2e-final-harness-failure`），改用绝对输出目录；视觉汇总脚本把长列表数组当 metrics 对象，修正读取后汇总通过。它们是 runner/回执脚本前置问题，不作为页面或接口缺陷。首次日志均保留，正常用户服务未被停止。

## 9. 实际技术回执与完整旅程状态

执行者为 `luna_test_runner`，运行使用已安装 Chrome、公开 Next 页面入口和生产形状 DTO 拦截。E2E 工作目录为 `/Users/dmeck/project/ink-dream-memory/frontend`；冻结生产构建在具名隔离副本，不使用用户 `.next`。回执根目录为 `/Users/dmeck/project/ink-dream-memory/output/calendar-borderless-ui-20261006`。以下日志、命令、退出码均由实际运行生成；最后焦点修正仅改测试，未重建不变的生产源码。

| 实际命令 | 退出码与关键结果 | 回执文件（位于输出根目录） |
| --- | --- | --- |
| `corepack pnpm run build`（cwd=`output/calendar-borderless-ui-20261006/frontend-build`，焦点实验前的冻结生产构建） | 0；Next 16.1.6 compiled successfully，TypeScript、页面生成及 traces 完成 | `diagnostics-build.command.log`、`.exit.log`、`.keyoutput.log` |
| `corepack pnpm exec tsc --noEmit --incremental false` | 0；无类型错误 | `controlled-tsc.command.log`、`.exit.log`、`.log` |
| `corepack pnpm exec eslint app/_dream/components/CalendarPopup.tsx app/_dream/components/CalendarNotionPanel.tsx app/_dream/api/notionTodayApi.ts e2e/calendar-right-panel-tabs.spec.ts e2e/scheduled-task-calendar.spec.ts e2e/calendar-auth-context.spec.ts e2e/fixtures/calendarHarness.ts` | 0；无相关 lint 错误 | `controlled-eslint.command.log`、`.exit.log`、`.log` |
| `E2E_WEB_BASE=http://127.0.0.1:55174 PLAYWRIGHT_HTML_OUTPUT_DIR=/Users/dmeck/project/ink-dream-memory/output/calendar-borderless-ui-20261006/controlled-focus-report corepack pnpm exec playwright test e2e/calendar-right-panel-tabs.spec.ts --grep="controlled initial Modal frame\|calendar journey preserves input" --workers=1 --trace=on --reporter=line,html --output=/Users/dmeck/project/ink-dream-memory/output/calendar-borderless-ui-20261006/controlled-focus-results` | 0；2 passed（6.1s），真实事件附件与 trace 保留 | `controlled-focus.command.log`、`.exit.log`、`.keyoutput.log`、`calendar-initial-frame-focus-evidence.json` |
| `E2E_WEB_BASE=http://127.0.0.1:55174 corepack pnpm exec playwright test e2e/calendar-right-panel-tabs.spec.ts e2e/scheduled-task-calendar.spec.ts e2e/calendar-auth-context.spec.ts --workers=1 --reporter=line --output=/Users/dmeck/project/ink-dream-memory/output/calendar-borderless-ui-20261006/full-regression-controlled-results` | 0；48 passed（55.3s），0 failed、0 skipped | `full-regression-controlled.command.log`、`.exit.log`、`.keyoutput.log`、`.log` |

| 完整旅程/验证 | 最终执行结果与边界 |
| --- | --- |
| Calendar 打开、默认、三页签、日期、关闭重开 | 通过；唯一面板、安排草稿、LIST/RESULT、精确读取、焦点与手动激活均保留；受控首帧机制单独验证 |
| 任务完整生命周期与 Chat | 通过；安排入口的未发送草稿、编辑成功/失败/冲突、立即运行/幂等、状态未知、历史分页、精确结果与 Thread 导航、暂停/恢复、删除/撤销及 DST 反馈 |
| 日记打开、返回、当前标记与删除 | 通过；原删除确认保留，长标题操作标签真实单行 |
| Notion 正常、异常与并发 | 通过；快照先显、历史创建、今天更新项校验、外链/刷新、慢校验不阻塞打开、连接/授权/归属错误、partial、Retry-After、网络错误、A→B→A、隐藏/关闭/登出迟到响应及跨午夜；重复操作不产生 select/sync/body 写入 |
| 视觉与原滚动 owner | 通过；三栏目×390/430/1024/1440×浅/深色共24组合 normal/hover/selected/focus，长标题/长列表、系统主题、对齐、操作触达、视口不溢出；实际 opaque ancestor 上合成 alpha Tokens，不降低原对比阈值 |
| 静态与生产构建 | 通过；上述实际 exit 0；最后只有测试/文档变化，未重复不变生产 build |
| 最新文档/历史/Mermaid/diff 检查 | 通过；§10.1 的最终动态 Markdown、README parity、Mermaid 和 `git diff --check` 回执均为 exit 0 |
| 自建资源清理 | 已完成；55174 无 listener，隔离副本/`.next`/依赖链接已删除；用户5173/8765保持运行 |

## 10. 历史、资源和交付状态

PRD 完整历史 SHA256=`01d756792acbc4e8e680a6bcec89f7be75c4c04a1142a3e1f8ca4262d79606b8`；正式稿完整历史 SHA256=`f0ede490ab078175a215c2cabd03467ef765b82315ebd28d76ecf78f0640c4a8`。原3个 Mermaid 块与 pre-borderless 历史逐块相等，§10.1 已记录最新机械检查通过。§6 原合并 hash 是当时记录，最终检查以逐块原文及各历史文件 byte hash 为准，避免用不同拼接分隔方式伪造一致。

代码、正式正文、过程证据、首次失败、修复前后截图、真实命令和测试回执保留；没有新增共享 schema/Admin 任务、接口或资源范围。Notion 仍为现行连接器选中快照范围（数据库范围包括其 page），没有声称完整上游授权全集。当前 `develop`/HEAD 与§2一致，保持用户和其他 Agent 的广泛未提交改动；本轮未创建 commit/PR，最终 Git 状态由主任务复核。

本轮技术旅程、必要静态/build、文档检查和自建资源清理均已通过，当前 UI 实现及 provider-free 隔离自动化技术验证完成；首次 tooltip 失败仍无法唯一归因，真实账户/真实模型验收不在本轮执行范围。

### 10.1 最终收口回执（2026-10-06）

本节在实施 worker 冻结正文后由 `luna_test_runner` 追加，记录最终独立验证与清理，不改变前述历史失败分类。

- 受控初始焦点实验：`controlled-focus.command.log`，exit `0`，2 passed；`calendar-initial-frame-focus-evidence.json` 记录 `releasedCallbacks=1`，并保留首帧、`monthPrev`、Notion hover 与键盘恢复事件。完整三份 E2E：`full-regression-controlled.command.log`，exit `0`，48 passed（55.3s）。
- 静态检查：`controlled-tsc.command.log` 和 `controlled-eslint.command.log` 均 exit `0`。本轮只改测试/fixture 就绪前置，生产 CSS/TSX 未重建。
- Markdown 动态检查：`doc-check-close-pre.command.log` exit `0`；46 个 tracked status entries、53 个 untracked leaf files、70 个 changed Markdown files；53 个新文件 inventory failures=`0`，70 个文件头 failures=`0`，318 个链接 non-pending missing=`0`，历史快照 `5/5`，whitespace=`0`。
- README 英中结构 parity：`readme-parity-close-pre.command.log` exit `0`；两侧标题 `15/15`、代码块 `6/6`、链接 `23/23`，API 日期和数据库同步标记一致。
- 正式稿 Mermaid：`mermaid-close-pre.command.log` exit `0`；3 个图全部 parsed/rendered，`render_failures=0`，Chrome headless/mermaid 11.17.2。追加本节没有改变图块；两份 pre-borderless 历史 SHA 与原始 3 图保留记录继续有效。
- `git diff --check`：`diff-close-pre.command.log` exit `0`。
- 清理：停止本轮自建 Next `127.0.0.1:55174`（PID 23759，命令为 `next-server (v16.1.6)`），删除本轮 `frontend-build`、其 `.next` 与 `node_modules` symlink；保留全部 output 回执、HTML、trace、JSON 与截图。清理后 55174 无 listener；用户既有 `127.0.0.1:5173`（PID 9971）和 `127.0.0.1:8765`（PID 81085）仍在监听，未停止或修改。
- 追加本节后的最终复查：`doc-check-close-final.command.log`、`readme-parity-close-final.command.log`、`diff-close-final.command.log` 均 exit `0`；README parity 仍为标题 `15/15`、代码块 `6/6`、链接 `23/23`，动态清单仍为 318 个链接无缺失、70 个文件头无失败、历史快照 `5/5`。一次 README shell 引号错误的未执行命令保留在 `readme-parity-close-final-harness-failure.*`，不属于文档失败。

以上回执覆盖第4节矩阵中的 Calendar、任务、日记、Notion、键盘/tooltip、主题/视口、静态与文档验证项。结论范围为本地 provider-free 隔离技术验证；首次无焦点事件的 tooltip 失败仍保留为无法唯一归因的历史事实，不写成已证明的产品根因；本轮不构成真实账户或真实模型业务验收。

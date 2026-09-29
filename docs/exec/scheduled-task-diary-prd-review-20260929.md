<!-- [Input] 用户标注图、Ink & Memory UI Design v2.1、现行 Calendar PRD/骨架/UI/系统设计、生产 CalendarPopup 与浏览器旅程。 -->
<!-- [Output] CalendarPopup 悬浮纸张视觉纠错的独立评审、范围裁决、追踪矩阵与验证回执。 -->
<!-- [Pos] 定时任务日记日期弹窗的现行设计与实施门禁；上一版分卡评审原文保存在 docs/exec/history。 -->
<!-- [Sync] 2026-09-29: 三张悬浮纸面、宽屏独立卡栈滚动和完整 Chrome 业务回归均已通过；上一版评审完整归档。 -->

# CalendarPopup 悬浮纸张视觉纠错独立评审（2026-09-29）

## 文档导航

- [现行 PRD](../prd/claude-agent/scheduled-task-diary-page-prd.md)
- [现行页面骨架](../prd/claude-agent/scheduled-task-diary-page-structure-sketch.md)
- [现行 UI 设计与原型](../design/claude-agent/scheduled-task-diary-page-ui-design.md)
- [定时任务系统交互与执行设计](../design/claude-agent/scheduled-task-loop-interaction-design.md)
- [上一版独立分卡评审与真实业务回执（历史）](./history/scheduled-task-diary-prd-review-v2-20260929.md)

## 1. 评审结论

**结论：可直接实施并验证完成。**

上一版已经把 `Scheduled tasks` 与 `Diary` 分成独立卡片，但仍保留可见的大型 Modal 纸面、重复的 `Calendar`/日期摘要，以及计划、下次执行、最近结果等嵌套事实框，因此未满足用户标注图的悬浮层级。现行设计已经完成以下收敛：

1. 共享 `Modal` 只负责 portal、dialog、焦点循环、Escape、关闭后焦点恢复和尺寸边界；Calendar 作用域中的 surface 透明且没有包围边框、圆角或阴影。
2. 月历、Scheduled tasks、Diary 是透明画布上的三张同级 Paper Cream 纸面，使用完整圆角与响应式暖棕阴影；右侧卡栈没有共享白底。
3. 可见 `Calendar` 标题与独立日期摘要被移除。dialog 标题仍以 1px 裁切方式供 `aria-labelledby` 使用；日期进入任务、日记业务标题。
4. 任务 facts、recent、edit/history 展开区取消卡中卡底色、圆角和阴影，以文字、留白和必要单线分组。
5. Task、Thread、Run、Tool、revision、manual request key、状态机、任务/日记 API 和数据库 schema 均不改变。

上一版 PRD、骨架、UI 和评审已完整保存在各自 `history/` 目录；它们只说明当时基线，不再作为现行实现规范。

## 2. 目标符合性与范围裁决

| 评审项 | 证据和判断 | 裁决 |
| --- | --- | --- |
| 是否解决用户指出的“线框大弹窗” | 现行 PRD §3、骨架 §2/§4 和 UI §5/§10 均定义透明 dialog 画布；生产 CSS 移除 outer surface | 符合 |
| 是否形成分开的悬浮卡 | 月历、任务、日记三个生产 surface 共用 Paper Cream、圆角和双层阴影；右栏父级透明 | 符合 |
| 是否删除无关信息层 | JSX 删除独立日期摘要；可见标题隐藏；计数改为普通次级文字；任务事实框扁平化 | 符合 |
| 是否保留业务交互 | 只调整现有组件 JSX、i18n、CSS 和浏览器断言；没有改 API、DTO、状态或持久化 | 符合 |
| 是否复用现有模块 | 继续使用共享 `Modal`、`CalendarPopup`、`ScheduledTaskCard`、原 API 与 Chat 导航 | 符合 |
| 是否引入未来假设 | 原型中误写的每周计划已改回每日；没有新建入口、筛选器、工作流或新状态 | 符合 |
| 是否增加无价值动效 | 现行设计明确不新增纸面入场、错峰、持续浮动或整体 hover 动画 | 符合 |
| 是否覆盖响应式和阴影裁切 | 1024px 以下单列；宽/中/手机分别匹配阴影安全区；宽屏右栈滚动不移动月历；短视口日期可达 | 符合，Chrome 回归通过 |
| 是否存在数据库 capability 影响 | 本轮无 schema、migration、runtime DDL 或 capability 变化 | 无影响 |

## 3. 需求—设计—实现—测试追踪矩阵

| 需求 | PRD/设计 | 实现 | 本轮测试 | 状态 |
| --- | --- | --- | --- | --- |
| 透明外层 dialog | PRD §3.1；UI §5/§10 | `.calendar-popup-modal` 透明、border 0、shadow none；标题视觉隐藏 | computed style 与隐藏标题裁切断言 | 通过 |
| 三张独立悬浮纸面 | PRD §3.2；骨架宽/窄屏；UI §3/§4 | `.calendar-popup__calendar` 与两个 `.calendar-popup__section` 共用纸色/圆角/阴影 | 要求正好三张非透明、有边界、有阴影的纸面 | 通过 |
| 关闭按钮不覆盖内容 | 骨架 D1；UI §4/§6 | 宽屏按钮位于纸面外侧安全区；单列时内容顶部预留 68px | 关闭按钮和三张纸面矩形不相交 | 通过 |
| 去掉重复日期摘要 | PRD §3.3；UI §10.1 | 删除 `.calendar-popup__date-summary`；日期进入两个业务 heading | 摘要不存在；中文标题为“今天的定时任务/日记” | 通过 |
| 计数是次级文字 | PRD B2/C2；UI §6.2 | `1 项` / `1 篇`，无圆形底 | 有数据与空任务日期断言 | 通过 |
| 任务详情扁平 | PRD §5.1；UI §6.3/§10 | task/fact/recent/展开区移除嵌套纸面 | task border/background/shadow 与 fact background 断言 | 通过 |
| 任务错误不阻断日记 | PRD §5.5；系统设计时序一失败分支 | 任务卡局部 error/retry；日记按钮仍可操作 | 持续错误、恢复重试和日记 enabled 旅程 | 通过 |
| 编辑、暂停、恢复和 revision | 系统设计时序三 | 既有 `ScheduledTaskCard`/API 不变 | desired 保留、CAS 重试、暂停/恢复 | 通过 |
| 手动运行与重复控制 | 系统设计时序二/三/四 | 既有 manual request key 和状态刷新不变 | 确定失败新 key、未知响应复用原 key、终态刷新 | 通过 |
| 历史、删除撤销和 Thread | PRD §5；系统设计时序三 | 既有 cursor、undo、Chat 导航不变 | 20+1 历史、删除/撤销、精确目标 Thread | 通过 |
| 滚动与断点 | 骨架 §4；UI §4 | 宽屏右侧卡栈独立滚动且月历固定；短视口月历内部可达；单列 `.calendar-popup` 统一滚动；1024/1025 同步切换 | overflow、390/1024/1025、1440×480 几何与最后日期可见 | 通过 |
| DST 失败反馈 | 系统设计配置规则 | 既有 desired 草稿和稳定错误文案不变 | 重复/缺失当地时间与恢复保存 | 通过 |

## 4. 影响范围与测试边界

| 项目 | 本轮范围 |
| --- | --- |
| 生产模块 | `frontend/app/_dream/components/CalendarPopup.tsx`、`CalendarPopup.css`、`frontend/app/_dream/i18n.ts` |
| 既有旅程 | 查看任务、任务错误重试、日记、编辑冲突、暂停/恢复、立即运行、历史、删除撤销、Thread 导航、DST |
| 数据库与后台 | 无代码和 schema 改动；确定性回归不连接数据库、不调用模型 |
| 浏览器资源 | 复用本机 Chrome。55173 因现有 5173 dev 进程持有 `.next/dev/lock` 无法另启同项目实例，按 harness 规则复用正常 5173 服务 |
| 清理 | 未停止或修改用户已有 5173/8765 服务；55173 最终无监听；Playwright 生成物由本轮恢复/清理 |

## 5. 既有真实业务闭环的适用范围

本轮是视觉和信息层级纠错，没有改变调度业务链。上一版评审已经记录两条正常账户、正常 PostgreSQL、真实模型的公开入口回执：修复后手动运行得到 `SCHEDULE-E2E-PASS-20260929-1438`；电脑重启后通过正常 Chat Tool 创建的一次性任务在 15:38 自动领取、完成并在持久目标 Thread 返回 `AUTO-SCHEDULE-E2E-PASS-20260929-1538`。任务、失败历史、目标 Thread 和刷新后持久化证据均保留在[历史评审](./history/scheduled-task-diary-prd-review-v2-20260929.md)。

这些回执证明既有 Chat Tool → Admin → worker → TaskSession/Thread → Claude turn → final → Calendar 历史业务链。它们不替代本轮视觉回归；本轮也不为纯 UI 变化再制造真实任务或日记数据。

## 6. 本轮验证回执

| 命令 | 退出码/关键输出 | 覆盖 |
| --- | --- | --- |
| `git diff --check` | 0；无输出 | patch 空白和冲突标记 |
| `cd frontend && corepack pnpm exec eslint app/_dream/components/CalendarPopup.tsx app/_dream/i18n.ts e2e/scheduled-task-calendar.spec.ts` | 0 | 生产 JSX/i18n 与浏览器旅程静态规则 |
| `cd frontend && corepack pnpm exec tsc --noEmit --incremental false` | 0 | TypeScript 合同 |
| `cd frontend && corepack pnpm build` | 0 | Next production build |
| `cd frontend && E2E_WEB_BASE=http://127.0.0.1:5173 corepack pnpm exec playwright test e2e/scheduled-task-calendar.spec.ts --grep 'mobile exhausted' --reporter=line --workers=1` | 0；`1 passed (3.8s)` | 390×844 底部阴影安全区聚焦复验 |
| `cd frontend && E2E_WEB_BASE=http://127.0.0.1:5173 corepack pnpm exec playwright test e2e/scheduled-task-calendar.spec.ts --reporter=line --workers=1` | 0；`8 passed (27.7s)`；console/pageerror/unexpected request 均为 0 | 三张悬浮纸面、宽屏右栈独立滚动、1440×480 月历可达、390/1024/1025 响应式，以及完整任务业务旅程 |

## 7. 最终裁决门禁

以下门禁均已满足：

- 独立评审没有未关闭的阻塞或 P1 问题。
- focused lint、TypeScript、production build 全部退出码 0。
- provider-free Chrome 完整旅程全部通过，且 application console、page error 和意外请求为 0。
- 390、1024、1025、1440 宽度均无文档或主滚动边界横向溢出；关闭按钮不覆盖纸面；三张纸的阴影样式存在且匹配各断点安全区。
- 本轮现行 Markdown 相对链接全部存在，`git diff --check` 退出码 0。

独立静态复核最终裁决为“可直接实施”；本轮无未关闭 P0/P1。

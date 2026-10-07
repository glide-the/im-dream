<!-- [Input] ../inputs/target_image.png、../inputs/topic.txt、UI v2.pdf 第5页与正常 Calendar 截图。 -->
<!-- [Output] 无边框右侧栏目的视觉分析和阶段1 PRD 草案，供结构阶段输入。 -->
<!-- [Pos] 顺序设计阶段1过程证据；现行产品合同位于 docs/prd/calendar。 -->
<!-- [Sync] 2026-10-06: 分析轻纸面无卡片规则，限定右侧呈现变更及现有业务保留。 -->
<!-- [Sync] 2026-10-06: 后续结构核对补正1024原堆叠/窄屏外层滚动及连续opaque paper承载；视觉规格已交正式稿，待评审实施。 -->
# 阶段1：Calendar 右侧无边框 PRD 草案

## 背景与问题

输入图是用户指定 PDF 第5页 §5.4 的规则页，并非 Calendar 页面。规则要求少面板、多留白：普通内容无需卡片，字号/字重区分层级，静止条目无阴影、外框或深底。正常页面截图显示右侧当前栏目仍是大圆角浅色卡片，顶部存在横向分割线；未选页签有圆形实底。用户明确此区域无边框，因此不把 PDF 通用页面级虚线外框套入 Calendar。

## 目标与边界

将 `calendar-popup__workspace` 的右侧 tasks/diary/Notion 改为平坦浅纸内容区，以留白和文字层级分区。左月历保持现状，编辑/历史 Modal 保持原功能、外观、状态 owner 和焦点。既有任务、日记、Notion 的数据、状态、文案、API、配置和权限完全沿用当前代码与现行 PRD。此次仅布局和视觉修正。

## 页面模块结构（自上而下、自左向右）

| 区域 | 当前外观 / 问题 | 目标布局 | 功能和 owner |
| --- | --- | --- | --- |
| 透明 Calendar 画布、关闭按钮 | 现有浮层 | 保留 | CalendarPopup 原关闭 / 日期初始值 |
| 左月历 | 原浅纸面、日期格及选中标记 | 保留尺寸、位置和窄屏转换 | 当前日期选择 / 原日记标记 |
| 右侧页签 | 选中胶囊、未选实底圆形 | 选中浅底圆角图标+名称，未选透明图标 | CalendarPopup activeTab / 手动键盘激活 |
| 当前栏目标题和原操作 | 大圆角卡片头、底部分隔线 | 主标题字重与留白分区，取消横线；操作原位置 | 原计数、刷新、入口和 aria-live |
| 当前栏目正文 | paper 底外框和双层阴影 | 平坦 paper 底，无外框、阴影或大圆角轮廓 | 原唯一 tabpanel / 原断点滚动 owner |
| 任务正文 | 行、事实、动作；有分隔线 | 行间留白，主副文字；取消装饰条目线框 | 原 LIST/RESULT、安排输入、结果、菜单 |
| 日记正文 | 条目卡片和当前态描边 | 透明行，标题/摘要/当前文字，轻 active 底可选 | 原日记打开、返回、当前标记、删除 |
| Notion 正文 | 创建/编辑组、时间和外链 | 保留组别/状态/文案，以组距和行距分层 | CalendarNotionPanel 原快照和远程校验 |
| 原功能浮层与输入控件 | tooltip、菜单、输入、Modal | 不按普通内容面板处理；保留功能识别和焦点 | 原 Portal owner、focus trap、输入提交 |

## 概念与交互规则

- 无边框指右侧栏目和普通内容的装饰边界；禁止用新的虚线框、条目外框、header 横线或悬浮卡片替代旧框。
- 默认静止态：workspace 透明；tabs 与当前栏目以连续 opaque paper 承载，workspace gap=0，由内部 padding 分区；普通行透明，无静态阴影或大圆角卡片轮廓。
- hover：现有 hover Token 轻背景，布局不位移、不加装饰边框，可不使用阴影。
- selected：页签保留浅底圆角图标和名称；当前日记使用现有当前标记和轻 active 背景，无选中描边。
- focus-visible：保留现有 `--color-border-focus` outline，滚动时不裁切；outline 是键盘焦点信息，不能被统一 border/outline 清零。
- 输入、主动作、危险动作、菜单与 tooltip 保留识别、禁用、焦点、定位和原行为。Notion 图标本身的描线不属于栏目装饰边框。
- 未选页签保持 accessible name、鼠标及键盘 tooltip。tablist/tab/tabpanel、aria-selected、方向键/Home/End 移焦点与 Enter/Space 手动激活不改变。
- 同日切栏保留各面板滚动、安排草稿、任务 LIST/RESULT 和已读结果；换日和重开仍按现行 PRD。
- 隐藏面板仍 hidden+inert，不触发新增查询、轮询或可见 Portal。

## 页面骨架与响应式

现行 PRD 正文已经直接包含完整桌面和窄屏骨架。本过程产物只提取结构供阶段2使用：

```text
桌面：原左月历 | 透明页签（选中浅底）
               | 标题 / 状态 / 原操作
               | 留白
               | 唯一平坦浅纸内容区，正文独立滚动
               | 分组标题、透明内容行及原操作

窄屏：原左月历
      透明页签（选中浅底）
      标题 / 状态 / 原操作
      唯一平坦浅纸正文，行换行和内容滚动
```

1440px 沿用左右结构与当前 section 独立滚动。原 <=64rem 断点在 1024px 已堆叠，Calendar 外层整体滚动、tabs sticky；390/430px 继续原 <=40rem 规则。不横向溢出，不放大月历或隐藏操作；RESULT 与原 Modal 内层滚动保持。明暗主题均复用既有 Tokens；透明 tab 置于 opaque paper，hover/active alpha 必须按实际纸底合成后实测对比。

## 技术建议

复用 `CalendarPopup.tsx`、`CalendarNotionPanel.tsx` 和现有 CSS 选择器，不新增布局组件、字体、图标库、Provider 或状态。实现主要修改 `CalendarPopup.css` 的右侧作用域：section、heading、tabs、日记/撤销行和条目留白。避免宽泛 `.calendar-popup__*` 规则误改左月历和原编辑/历史 Modal。复用 `--color-bg-paper`、`--color-bg-hover`、`--color-bg-active`、`--color-text-primary`、`--color-text-secondary`、`--color-border-focus`。字号与间距交阶段2/4按现有样式精化，不能增加业务阈值。

## 验收与阶段2输入

需要覆盖三个栏目、长内容、scroll 保留、键盘焦点与 tooltip、hover/selected、浅深主题和 390/430/1024/1440px。检查右侧外框与静态阴影为无、未选页签透明、字号/字重层级和可读性、左月历/原 Modal 未回归。任务和日记原完整旅程、Notion 快照优先与旧响应保护仍使用已有生产入口和 harness。

阶段2读取本文件、原规则图和现行 PRD，产出布局分区、具体响应式留白/文字层级；阶段3继续沿用业务 owner，阶段4同步正式设计稿正常/异常/状态图，再独立评审。本阶段仅完成设计文档，未写生产代码、未运行功能测试。

- [现行 PRD](../../../../prd/calendar/calendar-right-panel-tabs-prd.md)
- [影响及验证记录](../../../../exec/calendar-borderless-ui-20261006.md)
- [正式设计稿](../../calendar-right-panel-tabs-ui-design.md)

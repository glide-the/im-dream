<!-- [Input] 1_prd_draft.md、2_structure_sketch.md、PDF 第5页规则图与当前 CalendarPopup/CalendarNotionPanel DOM/CSS。 -->
<!-- [Output] 右侧栏目视觉层级、逻辑树、交互状态及供正式设计阶段落实的 CSS 映射。 -->
<!-- [Pos] 顺序设计阶段3过程证据；正式 PRD/交互正文与生产实现由主任务维护。 -->
<!-- [Sync] 2026-10-06: 明确连续 opaque paper、现有状态与滚动 owner；不新增业务模块或测试分支。 -->
# 阶段3：Calendar 右侧层级映射

## 背景与边界

综合[阶段1](./1_prd_draft.md)、[阶段2](./2_structure_sketch.md)及[原规则图](../inputs/target_image.png)。以真实 DOM/CSS 为准，只细化右侧视觉；所有文案、状态 owner、API、条件渲染、Modal、菜单与焦点逻辑保持原实现。以下线条用于标识范围，不是界面边框。

## 精化结构与逻辑树

```text
┌ A1 原 Calendar 画布 ────────────────────────────────────────┐
│                                                   A2 关闭 │
│ ┌ D1 原左月历 ───────────┐  ┌ B1 页签浅纸平面 ───────────┐ │
│ │ 原导航/日期格/标记     │  │ [选中图标+名称] 图标 图标   │ │
│ │                       │  │ B2 当前栏目标题    原操作   │ │
│ │                       │  │    计数/次级状态（原位置）  │ │
│ │                       │  │                            │ │
│ │                       │  │ B3 唯一栏目正文            │ │
│ │                       │  │ C1 输入或状态/恢复/组标题  │ │
│ │                       │  │                            │ │
│ │                       │  │ C2 标题                    │ │
│ │                       │  │    时间/摘要/标记 原操作   │ │
│ └───────────────────────┘  └────────────────────────────┘ │
│ B4 原 tooltip/菜单/编辑与历史 Modal 覆盖层                 │
└───────────────────────────────────────────────────────────┘
```

```text
A1 CalendarPopup / 原 Modal：日期与 activeTab owner
├── A2 原关闭入口
├── D1 原月历：保持全部视觉与布局
├── 原 calendar-popup__workspace（透明布局容器）
│   ├── B1 原 tablist：选择栏目；opaque paper 承载透明 tab
│   └── 原 workspace-scroll
│       └── B3 唯一可见 tabpanel（其余 hidden + inert）
│           ├── B2 原 heading：主标题 + 原计数/状态/操作
│           └── 原 card-body
│               ├── tasks：CalendarPopup / ScheduledTaskCard/Result 原 owner
│               │   ├── C1 安排输入、loading/error/恢复（原条件）
│               │   └── C2 原任务列表或 RESULT（互斥，原条件）
│               ├── diary：CalendarPopup 原日期条目与当前条目 owner
│               │   ├── C1 原空状态
│               │   └── C2 时间/当前标记/标题 + 原删除入口
│               └── Notion：CalendarNotionPanel 原请求/上下文 owner
│                   ├── C1 连接/读取/校验/partial/恢复 + 实际计数/同步时间
│                   └── C2 原创建/编辑组：标题、上游时间与外链
└── B4 原 tooltip/菜单与编辑/历史 Modal：保留各自 Portal/焦点 owner
```

此树表示功能归属，三个栏目分支按原条件互斥；不引入新的容器组件或状态。B4 的 Modal 沿用现有 Portal，不表示将其移动到 workspace DOM 内。

## 三栏目层级与现有 selector

| 层级 | 现有内容及 selector | 阶段4可实现规则 |
| --- | --- | --- |
| 导航 B1 | `__tabs [role='tab']`、`__tab-wrap` | 选中图标+名称；未选图标透明。沿用 .82rem/700、2.75rem 最小命中区及原 accessible name。 |
| 栏目 B2 | `__section-heading h3`、`__card-header-meta/count/status`、原 refresh | 主标题沿用 1.1rem 与原标题字体，primary 色；计数/状态沿用 .78rem secondary 色。原刷新/注意事项按钮保持位置及禁用逻辑，不另建徽章卡片。 |
| leading C1 | `__arrange`、`__loading/empty/hint/alert`、Notion 原 status/设置按钮 | 保持原呈现顺序、完整文案、role/aria-live/busy 与恢复入口。以留白和原状态色区分；不将状态再包入独立卡片。安排输入保留功能边界与提交按钮，不按普通内容去掉控件识别。 |
| 任务 C2 | `__task`、`__task-open strong/small`、`__task-state`、`__undo-row` | 最终现有 CSS 的标题 .94rem、副文字 .77rem 沿用；原状态图标与行内 edit/more 位置保持。透明行，任务/撤销行无装饰外框和阴影；任务状态图标自身描线是功能标记，保留。 |
| 任务 RESULT C2 | `__task-result`、其 header/scroll/footer | 原返回、任务标题、时间、准确结果和 Thread 按钮保留，内层 scroll 不改。取消普通内容 header/footer 分割线，改为原间距或留白；按钮功能边界保留。 |
| 日记 C2 | `__diary`、`__diary-open`、`__diary--current`、`__diary-delete` | 时间 .75rem secondary 色、标题原字体/字重、既有当前文字标记保留。透明普通行；current 用轻 active 底，不用成功色整行描边。原删除入口及危险 hover 不变。 |
| Notion 分组 C1 | `__notion-group h4` | 分组标题沿用 .94rem primary 色及原实际组计数；创建/编辑组条件不变。组间 1.5rem，以留白分层，无组卡片。 |
| Notion 页面 C2 | `__notion-group li`、`__notion-title`、`__notion-meta`、外链 | 图标/title/时间/外链原顺序，元数据 .77rem secondary 色。标题可换行；保留创建/编辑双标识与原 URL 失败反馈，页面行不新增 border/shadow。 |
| 浮层 B4 | tooltip、more-menu、task editor/history Modal | 维持原外观、焦点陷阱、菜单定位与危险项；普通面板的去边框 selector 不匹配这些区域。 |

## 状态呈现

| 目标 | normal | hover / selected | focus |
| --- | --- | --- | --- |
| B1 tabs | 未选 background transparent、无 border/shadow | hover 为现有 hover Token；selected 为 active Token 浅底圆角，无描边/阴影 | 保留 focus Token 的 inset -3px outline，手动激活与 tooltip 不变 |
| B2/B3 平面 | 同一 opaque `--color-bg-paper`；border/radius/shadow=0，无 heading 横线 | 不给整面 hover 填充或浮动效果 | 当前面板/内部控件的原键盘行为不变 |
| C2 内容行 | 透明，无静态阴影/外框/横向分割线 | 使用现有轻 hover 反馈，无位移；日记 current 轻 active 底与原当前标记 | 保留按钮与行焦点，不能用统一 outline:0 清除 |
| C1 读取/校验 | 原 status 文案与 live/busy、实际已知计数保持 | 原刷新/恢复禁用或可用状态保持；不显示伪进度 | 设置/刷新/恢复入口维持可见 focus |
| C1 错误/partial | 原错误/部分结果及允许展示的旧行保持；无新包裹卡片 | 不通过背景或 hover 暗示错误已恢复 | danger 状态色、原 role 与恢复入口保持，焦点不因排版丢失 |

## 正式稿同步与验证边界

- workspace 保持透明；B1 tabs 与 B2/B3 当前 section 为连续 opaque paper，workspace gap=0，靠 tabs/heading 的内距形成留白。桌面三处水平内距 1.5rem，<=40rem 同为 1rem；tabs 上/下 .75/.5rem、heading 与 body 上 1rem 沿用阶段2建议。没有纸面上的新增边框或大圆角。
- 原 <=64rem 断点整体 `.calendar-popup` 滚动，当前 section 高度 auto/overflow visible，tabs sticky；1024px 已堆叠。1440px 原当前 section 独立滚动，tabs 在其外；任务 RESULT 与 Modal 内层滚动保持。这些需写入正式稿，不只链接阶段文件。
- active/hover Token 是 alpha 值，对比验证须与实际 opaque paper 合成后测量；不能用透明色的 RGB 直接计算比值。浅/深/系统主题、normal/hover/selected/focus 均以后续实际浏览器证据为准。
- 原三个 E2E specs 的业务旅程继续保留。视觉断言只对右侧作用域要求 border/shadow=0，左月历的原 border/shadow 与原 Modal 不应被误判。两个 media 断点对 section 的旧圆角/阴影覆盖也要核验。
- 本阶段只写层级过程文件和清单，不写生产代码，不执行测试，不声明视觉或业务验收通过。
